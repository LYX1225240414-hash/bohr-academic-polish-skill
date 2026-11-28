#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
edit_lint.py — 学术润色的「最小编辑 + 语义守恒 + 可追溯」核验器
（academic-polish-faithful Skill 执行内核）

解决的问题：润色最容易出事的地方不是"改得不够漂亮"，而是
  限定词被删掉（may → is）、强度词被吞掉（significantly）、数字/单位/引用编号被顺手改、
  整句被重写成另一种主张、以及改了一堆却没写进修改清单。
这些都能机械核对。

子命令：
  split    句级切分原文与改文，输出带 location 的句子表
  terms    抽候选术语 + 检出全篇缩写大小写/连字符漂移 + 缩写首次出现未给全称
  lint     句级对齐后做保真、语域、硬错误、过度改写、修改清单覆盖五类检查
  report   只读 lint 产出的 json，生成人读 md

用法：
  python3 edit_lint.py split --text orig.txt --out /app/work
  python3 edit_lint.py terms --text polished.md --out /app/work
  python3 edit_lint.py lint  --source orig.txt --revised polished.md \\
                             --glossary glossary.json --changes changes.json --out /app/output
"""

import argparse
import json
import re
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

# ---------- 切句 ----------

ABBREV = ("et al", "e.g", "i.e", "Fig", "Figs", "Tab", "Ref", "Refs", "Eq", "Eqs",
          "vs", "cf", "approx", "resp", "Suppl", "Sec", "No", "Dr", "Prof", "St")
SENT_END = re.compile(r"(?<=[.!?。！？；;])\s+")


def cjk_ratio(s):
    if not s:
        return 0.0
    n = sum(1 for ch in s if "\u4e00" <= ch <= "\u9fff")
    return n / len(s)


def same_script(a, b):
    """两段文本是否同为主中文或同为主拉丁：跨语言比较时相似度/术语包含判断都无意义"""
    return (cjk_ratio(a) > 0.2) == (cjk_ratio(b) > 0.2)


def split_sentences(text):
    """按句末标点切句；保护缩写、保护 $...$ 与 \\cite{} 等标记内部"""
    # 把不可切分的片段先占位
    guards = {}

    def stash(m):
        key = f"\x00{len(guards)}\x00"
        guards[key] = m.group(0)
        return key

    t = re.sub(r"\$[^$]*\$|\\\([^)]*\\\)|\\\[[^\]]*\\\]|\\cite[a-z]*\{[^}]*\}|\[\d{1,3}(?:\s*[,\-–]\s*\d{1,3})*\]",
               stash, text)

    raw = [p.strip() for p in SENT_END.split(t) if p.strip()]
    # 累积到"末尾不是缩写、且长度够"才切句。判断对象是当前累积段，不是新片段。
    out, buf = [], ""
    for seg in raw:
        buf = (buf + " " + seg).strip() if buf else seg
        tail = buf.rstrip(" .!?。！？；;")
        words = tail.split()
        last1 = re.sub(r"^[^\w]+", "", words[-1]).rstrip(".") if words else ""
        last2 = re.sub(r"^[^\w]+", "", " ".join(words[-2:])).rstrip(".") if len(words) >= 2 else ""
        if last1 in ABBREV or last2 in ABBREV or len(seg) <= 2:
            continue
        out.append(buf)
        buf = ""
    if buf:
        out.append(buf)

    for i, s in enumerate(out):
        for k, v in guards.items():
            s = s.replace(k, v)
        out[i] = s
    return out


def paragraphs_of(text):
    return [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]


def numbered_sentences(text):
    """返回 [(location, sentence)]，location 形如 sec1/p2/s3"""
    res = []
    for pi, para in enumerate(paragraphs_of(text), 1):
        for si, sent in enumerate(split_sentences(para), 1):
            res.append((f"p{pi}/s{si}", sent))
    return res


def norm(s):
    s = s.lower()
    s = re.sub(r"\s+", " ", s)
    return s.strip(" \t\r\n.,;:!?。，；：！？")


# ---------- 词表 ----------

HEDGE_EN = re.compile(
    r"\b(?:may|might|could|would|suggest(?:s|ed|ing)?|indicat(?:e|es|ed|ing)|"
    r"appear(?:s|ed)?|seem(?:s|ed)?|likely|unlikely|probably|possibly|potentially|"
    r"presumably|arguably|tend(?:s|ed)?\s+to|is\s+consistent\s+with|are\s+consistent\s+with|"
    r"points?\s+to|hints?\s+at|it\s+is\s+plausible)\b", re.I)
HEDGE_CN = re.compile(r"(可能|或许|大概|似乎|倾向于|有望|初步|推测|暗示|提示|在一定程度上|或可|据估计)")
CLAIM_EN = re.compile(
    r"\b(?:demonstrat(?:e|es|ed)|prov(?:e|es|ed|en)|confirm(?:s|ed)?|establish(?:es|ed)?|"
    r"show(?:s|n|ed)?|reveal(?:s|ed)?|verif(?:y|ies|ied)|establishes)\b", re.I)
CLAIM_CN = re.compile(r"(证明|证实|表明|显示|说明|确认|确证)")

NEG_EN = re.compile(r"\b(?:not|no|never|none|neither|nor|without|lack(?:s|ed)?|fail(?:s|ed)?|cannot|n't)\b", re.I)
NEG_CN = re.compile(r"(不|未|无|非|没有|未能|无法|并非|不曾)")

INTENS_EN = re.compile(
    r"\b(?:significantly|markedly|substantially|considerably|greatly|dramatically|"
    r"remarkably|only|solely|exclusively|entirely|completely|all|every|"
    r"slightly|marginally|moderately)\b", re.I)
INTENS_CN = re.compile(r"(显著|明显|大幅|极大|仅|只|全部|完全|略微|轻微|一定程度上)")

CITE = re.compile(r"\[\d{1,3}(?:\s*[,\-–]\s*\d{1,3})*\]|\\cite[a-z]*\{[^}]+\}")
NUM = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?:[eE][+-]?\d+)?%?")
_UNITS = ["mA·cm⁻²", "wt%", "at%", "vol%", "mol%", "℃", "°C", "μg", "µg", "ng", "mL", "ml",
          "μL", "µL", "mM", "μM", "µM", "nM", "mol", "mmol", "mg", "kg", "km", "nm", "μm",
          "µm", "mm", "cm", "kV", "mV", "mA", "μA", "µA", "Hz", "kHz", "MHz", "GHz",
          "min", "ms", "h", "s", "K", "eV", "keV", "MeV", "GPa", "MPa", "kPa", "Pa",
          "rpm", "ppm", "ppb", "mAh", "Wh", "kWh", "L", "%"]
UNIT = re.compile(r"(?<![\w.])\d+(?:\.\d+)?\s*(" + "|".join(sorted(_UNITS, key=len, reverse=True)) + r")(?![\w])")
FIGREF = re.compile(r"(?:Fig(?:ure)?s?\.?\s*\d+[a-z]?|Tables?\s*\d+[a-z]?|Eqs?\.?\s*\(?\d+\)?|"
                    r"图\s*\d+[a-z]?|表\s*\d+[a-z]?|公式\s*\(?\d+\)?)", re.I)

COLLOQUIAL = re.compile(
    r"\b(?:a\s+lot\s+of|lots\s+of|kind\s+of|sort\s+of|pretty\s+much|really|very|huge|"
    r"big|stuff|things?|get|got|nice|okay|a\s+bit)\b", re.I)
PROMOTIONAL = re.compile(
    r"\b(?:groundbreaking|unprecedented|revolutionary|world-?class|cutting-?edge|"
    r"paradigm[- ]shift|game[- ]chang(?:er|ing)|state[- ]of[- ]the[- ]art)\b", re.I)
PROMO_CN = re.compile(r"(重大突破|国际领先|填补空白|首次实现|开创性|革命性|颠覆性|世界一流)")
ABSOLUTE = re.compile(
    r"\b(?:always|never|completely|totally|entirely|undoubtedly|certainly|definitely|obviously)\b", re.I)
ABS_CN = re.compile(r"(完全|必然|毫无疑问|绝对)")

PLURAL_SUBJ = r"(?:results?|findings?|studies|experiments?|measurements?|samples?|particles?|images?|patterns?|spectra)"
AGREEMENT = re.compile(
    r"\b(" + PLURAL_SUBJ + r")\s+(shows|indicates|reveals|suggests|demonstrates|confirms|was|has|is)\b", re.I)
# 拼写像元音开头但读音是辅音的例外（a unique / an hour）
A_EXCEPT = re.compile(r"^(?:uni|use|user|usu|uti|ure|uro|eu|ewe|one|once|ubiq)", re.I)
AN_EXCEPT = re.compile(r"^(?:hour|honest|honou?r|heir)", re.I)
ARTICLE_A = re.compile(r"\ba\s+([aeiou][a-z]{2,})", re.I)
ARTICLE_AN = re.compile(r"\ban\s+([bcdfgjklmnpqrstvwxyz][a-z]{2,})", re.I)


def read(p):
    try:
        return Path(p).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def cnt_nums(t):
    # 引用编号与图表编号不是"被测数值"，先剥掉，避免与 citation/figref 检查重复报
    return Counter(n.rstrip("%") for n in NUM.findall(FIGREF.sub(" ", CITE.sub(" ", t))))


def cnt_units(t):
    return Counter(m.group(1).replace("µ", "μ").replace("°C", "℃") for m in UNIT.finditer(CITE.sub(" ", t)))


def cnt_cites(t):
    return Counter(CITE.findall(t))


def cnt_figrefs(t):
    return Counter(re.sub(r"\s+", " ", x.lower()) for x in FIGREF.findall(t))


def hedge_count(s):
    return len(HEDGE_EN.findall(s)) + len(HEDGE_CN.findall(s))


def claim_count(s):
    return len(CLAIM_EN.findall(s)) + len(CLAIM_CN.findall(s))


def neg_count(s):
    return len(NEG_EN.findall(s)) + len(NEG_CN.findall(s))


def intens_count(s):
    return len(INTENS_EN.findall(s)) + len(INTENS_CN.findall(s))


def diff_counter(a, b):
    return {k: {"source": a.get(k, 0), "revised": b.get(k, 0)} for k in (a - b)}


# ---------- split ----------

def cmd_split(args):
    text = read(args.text)
    if not text:
        print(json.dumps({"ok": False, "error": "文本为空或路径不存在"}, ensure_ascii=False))
        return 1
    items = [{"location": loc, "sentence": s} for loc, s in numbered_sentences(text)]
    Path(args.out).mkdir(parents=True, exist_ok=True)
    p = Path(args.out) / "sentences.json"
    p.write_text(json.dumps({"ok": True, "count": len(items), "sentences": items},
                            ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "sentences": len(items),
                      "paragraphs": len(paragraphs_of(text)), "out": str(p)}, ensure_ascii=False))
    return 0


# ---------- terms ----------

ACRO = re.compile(r"\b[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*\b")


def word_shape(w):
    letters = [c for c in w if c.isalpha()]
    if not letters:
        return "na"
    if all(c.isupper() for c in letters):
        return "upper"
    if all(c.islower() for c in letters):
        return "lower"
    if letters[0].isupper() and all(c.islower() for c in letters[1:]):
        return "cap"
    return "mixed"


def cmd_terms(args):
    text = read(args.text)
    if not text:
        print(json.dumps({"ok": False, "error": "文本为空或路径不存在"}, ensure_ascii=False))
        return 1

    # 1) 大小写 / 连字符漂移：同一 token 归一后出现 ≥2 种写法
    buckets = {}
    for m in ACRO.finditer(text):
        w = m.group(0)
        if len(w) < 2 or w.isdigit():
            continue
        key = w.lower().replace("-", "")
        buckets.setdefault(key, Counter())[w] += 1
    drift = []
    for key, forms in buckets.items():
        if len(forms) < 2 or sum(forms.values()) < 2:
            continue
        shapes = {word_shape(f) for f in forms}
        # 句首大写（the / The）属正常大小写，不是漂移：
        # 只有出现全大写或混合形状，或连字符写法不一致，才算真漂移
        hyphen_variants = len({"-" in f for f in forms}) > 1
        upper_mixed = bool(shapes & {"upper", "mixed"}) and len(shapes - {"na"}) > 1
        if not (hyphen_variants or upper_mixed):
            continue
        drift.append({"normalized": key, "forms": dict(forms),
                      "reason": "连字符写法不一致" if hyphen_variants else "大小写形状不一致",
                      "action": "统一为一种写法（大小写/连字符全篇一致）"})
    drift.sort(key=lambda x: -sum(x["forms"].values()))

    # 2) 缩写首次出现是否给了全称（启发式，仅提示）
    abbrevs = []
    seen = set()
    for m in re.finditer(r"\b([A-Z]{2,6})\b", text):
        a = m.group(1)
        if a in seen or a in {"THE", "AND", "FOR", "NOT", "ALL", "USA", "DNA", "RNA", "PDF"}:
            continue
        seen.add(a)
        win = text[max(0, m.start() - 90):m.end() + 90]
        defined = bool(re.search(r"\([^)]{4,}\)", win)) or bool(re.search(r"[A-Za-z]{4,}", win))
        if not re.search(r"[（(][^)）]{4,}[)）]", win):
            defined = False
        abbrevs.append({"abbrev": a, "first_pos": m.start(), "has_definition_nearby": defined,
                        "window": re.sub(r"\s+", " ", win)[:160]})

    # 3) 候选术语（大写缩写 + 高频名词短语）
    cands = Counter()
    for m in re.finditer(r"\b(?:[A-Z]{2,6}|[A-Z][a-z]?[A-Z][A-Za-z0-9]{1,10})\b", text):
        cands[m.group(0)] += 1
    for w in re.findall(r"[a-z][a-z\-]{3,}(?:\s+[a-z][a-z\-]{3,}){1,2}", text.lower()):
        if len(w) >= 10:
            cands[w] += 1

    out = {
        "ok": True,
        "case_sensitive_drift": drift[:40],
        "case_drift_count": len(drift),
        "abbrev_first_use": abbrevs[:40],
        "abbrev_undefined_count": sum(1 for a in abbrevs if not a["has_definition_nearby"]),
        "term_candidates": [{"term": t, "count": c} for t, c in cands.most_common(120)],
    }
    Path(args.out).mkdir(parents=True, exist_ok=True)
    p = Path(args.out) / "terms_report.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "case_drift_count": out["case_drift_count"],
                      "abbrev_undefined_count": out["abbrev_undefined_count"],
                      "candidates": len(out["term_candidates"]), "out": str(p)}, ensure_ascii=False))
    return 0


# ---------- 对齐 ----------

def align(src_sents, rev_sents):
    a = [norm(s) for _, s in src_sents]
    b = [norm(s) for _, s in rev_sents]
    sm = SequenceMatcher(None, a, b, autojunk=False)
    pairs, unmatched_src, unmatched_rev = [], [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                pairs.append({"src_idx": i1 + k, "rev_idx": j1 + k, "changed": False,
                              "similarity": 1.0})
        elif tag == "replace":
            n = max(i2 - i1, j2 - j1)
            for k in range(n):
                si = i1 + k if i1 + k < i2 else None
                ri = j1 + k if j1 + k < j2 else None
                if si is None:
                    unmatched_rev.append(ri)
                    continue
                if ri is None:
                    unmatched_src.append(si)
                    continue
                ratio = SequenceMatcher(None, a[si], b[ri], autojunk=False).ratio()
                pairs.append({"src_idx": si, "rev_idx": ri, "changed": True, "similarity": round(ratio, 4)})
        else:  # delete / insert
            unmatched_src += list(range(i1, i2))
            unmatched_rev += list(range(j1, j2))
    return pairs, unmatched_src, unmatched_rev


# ---------- lint ----------

def cmd_lint(args):
    src, rev = read(args.source), read(args.revised)
    if not src or not rev:
        print(json.dumps({"ok": False, "error": "原文或改文为空/路径不存在"}, ensure_ascii=False))
        return 1

    src_sents, rev_sents = numbered_sentences(src), numbered_sentences(rev)
    pairs, lost_src, added_rev = align(src_sents, rev_sents)

    # ---- 保真：逐句对 ----
    number_changed, unit_changed, cite_changed, figref_changed = [], [], [], []
    hedge_removed, hedge_added, hedge_upgraded, hedge_downgraded = [], [], [], []
    neg_changed, intens_dropped = [], []

    for pr in pairs:
        si, ri = pr["src_idx"], pr["rev_idx"]
        s_loc, s = src_sents[si]
        r_loc, r = rev_sents[ri]

        ns, nr = cnt_nums(s), cnt_nums(r)
        if ns - nr:
            number_changed.append({"location": f"{s_loc}->{r_loc}", "missing": dict(ns - nr),
                                   "added": dict(nr - ns),
                                   "action": "数字被改动或丢失，按原文恢复"})
        us, ur = cnt_units(s), cnt_units(r)
        if us - ur:
            unit_changed.append({"location": f"{s_loc}->{r_loc}", "missing": dict(us - ur),
                                 "action": "单位被改动或丢失，单位应原样保留"})
        cs, cr = cnt_cites(s), cnt_cites(r)
        if cs - cr:
            cite_changed.append({"location": f"{s_loc}->{r_loc}", "missing": dict(cs - cr),
                                 "action": "引用标记被删改，必须原样保留"})
        fs, fr = cnt_figrefs(s), cnt_figrefs(r)
        if fs - fr:
            figref_changed.append({"location": f"{s_loc}->{r_loc}", "missing": dict(fs - fr),
                                   "action": "图表/公式指向被改动，核对是否仍指同一对象"})

        hs, hr = hedge_count(s), hedge_count(r)
        if hs and not hr:
            item = {"location": f"{s_loc}->{r_loc}", "source": s[:180], "revised": r[:180],
                    "action": "限定被删掉：同句已无 hedge，等于把弱结论说成定论，改回或明确说明"}
            hedge_removed.append(item)
            if not claim_count(s) and claim_count(r):
                hedge_upgraded.append({**item,
                                       "action": "限定被升级为强断言（may/suggest → show/demonstrate），这是最危险的一类改动"})
        elif not hs and hr:
            item = {"location": f"{s_loc}->{r_loc}", "source": s[:180], "revised": r[:180],
                    "action": "新增了限定：原文没有 hedge，改后加了，等于削弱作者结论"}
            hedge_added.append(item)
            if claim_count(s) and not claim_count(r):
                hedge_downgraded.append(item)

        gs, gr = neg_count(s), neg_count(r)
        if gs != gr:
            neg_changed.append({"location": f"{s_loc}->{r_loc}", "source_neg": gs, "revised_neg": gr,
                                "source": s[:160], "revised": r[:160],
                                "action": "否定词数量变化：核对否定范围是否被扩大或缩小"})

        is_, ir = intens_count(s), intens_count(r)
        if is_ and not ir:
            intens_dropped.append({"location": f"{s_loc}->{r_loc}", "missing_terms":
                                   INTENS_EN.findall(s) + INTENS_CN.findall(s),
                                   "source": s[:160], "revised": r[:160],
                                   "action": "强度词被吞掉（significantly/only/显著/仅），结论强度被改"})

    # ---- 保真：全文级（防漏句） ----
    g_nums_s, g_nums_r = cnt_nums(src), cnt_nums(rev)
    g_units_s, g_units_r = cnt_units(src), cnt_units(rev)
    g_cite_s, g_cite_r = cnt_cites(src), cnt_cites(rev)
    global_diff = {
        "numbers_missing": diff_counter(g_nums_s, g_nums_r),
        "units_missing": diff_counter(g_units_s, g_units_r),
        "citations_missing": diff_counter(g_cite_s, g_cite_r),
    }

    # ---- 术语 ----
    glossary_missing, glossary_inconsistent, glossary_na = [], [], []
    gterms = []
    if args.glossary:
        try:
            data = json.loads(Path(args.glossary).read_text(encoding="utf-8"))
            gterms = data.get("terms") if isinstance(data, dict) else data
            gterms = gterms or []
        except Exception:
            gterms = []
    for t in gterms:
        term = str(t.get("term") or "").strip()
        canon = str(t.get("canonical") or t.get("zh") or t.get("revised") or "").strip()
        if not canon:
            continue
        variants = [str(v).strip() for v in (t.get("variants") or []) if str(v).strip()]
        # 术语表写法与改文语言不同（如英文学术稿配了中文译名）时，"未出现"不成立
        if not same_script(canon, rev):
            glossary_na.append({"term": term, "canonical": canon,
                                "reason": "术语表写法与改文语言不一致，跳过包含性检查（检查大小写/连字符请换成目标语言写法）"})
            continue
        if canon not in rev:
            glossary_missing.append({"term": term, "canonical": canon,
                                     "action": "统一写法未在改文中出现：确认是否漏改或术语表写法有误"})
            continue
        # 大小写/连字符漂移：不区分大小写找出所有实际写法
        forms = Counter(m.group(0) for m in re.finditer(re.escape(canon).replace(r"\ ", r"\s*"), rev, re.I))
        if len(forms) > 1:
            glossary_inconsistent.append({"term": term, "canonical": canon,
                                          "forms": dict(forms),
                                          "action": f"同一术语多种写法并存，统一为「{canon}」"})
        hit = {v: rev.count(v) for v in variants if rev.count(v)}
        if hit:
            glossary_inconsistent.append({"term": term, "canonical": canon, "variants_used": hit,
                                          "action": f"改文中仍使用异体写法，统一为「{canon}」"})

    # ---- 语域 ----
    def reg(rx, text, label, action):
        return [{"location": "全文", "hit": h, "kind": label, "action": action}
                for h in dict.fromkeys(m.group(0) for m in rx.finditer(text))]

    register = {
        "colloquial": reg(COLLOQUIAL, rev, "口语化", "替换为学术语域表达"),
        "promotional": reg(PROMOTIONAL, rev, "宣传化", "删除宣传性修饰，改为可验证表述") +
                       reg(PROMO_CN, rev, "宣传化", "删除宣传性修饰，改为可验证表述"),
        "absolute": reg(ABSOLUTE, rev, "绝对化", "绝对化表述需弱化或限定适用范围") +
                    reg(ABS_CN, rev, "绝对化", "绝对化表述需弱化或限定适用范围"),
    }
    register_count = sum(len(v) for v in register.values())

    # ---- 硬错误 ----
    hard = []
    for m in re.finditer(r"  +", rev):
        seg = rev[max(0, m.start() - 30):m.end() + 30]
        if "\n" in seg:
            continue
        hard.append({"kind": "double_space", "at": m.start(), "snippet": seg})
    for m in re.finditer(r"\s+([,.;:!?，。；：！？])", rev):
        hard.append({"kind": "space_before_punct", "at": m.start(), "snippet": m.group(0)})
    for m in re.finditer(r"\b(\w+)\s+\1\b", rev, re.I):
        if m.group(1).lower() in {"that", "had", "is", "very"} or len(m.group(1)) > 2:
            hard.append({"kind": "repeated_word", "at": m.start(), "snippet": m.group(0)})
    for m in AGREEMENT.finditer(rev):
        hard.append({"kind": "subject_verb_agreement", "at": m.start(),
                     "snippet": m.group(0), "fix": f"{m.group(1)} + 复数动词"})
    for m in ARTICLE_A.finditer(rev):
        if A_EXCEPT.match(m.group(1)):
            continue
        hard.append({"kind": "article_a_vowel", "at": m.start(), "snippet": m.group(0),
                     "fix": "元音音素开头应用 an（注意 unique/hour 这类读音例外）"})
    for m in ARTICLE_AN.finditer(rev):
        if AN_EXCEPT.match(m.group(1)):
            continue
        hard.append({"kind": "article_an_consonant", "at": m.start(), "snippet": m.group(0),
                     "fix": "辅音音素开头应用 a"})
    # 句首小写（英文句）
    for loc, s in rev_sents:
        if cjk_ratio(s) < 0.1 and s[:1].islower() and len(s) > 3:
            hard.append({"kind": "sentence_start_lowercase", "location": loc, "snippet": s[:60]})
    # 中英标点混用（排除 1,000 这类千分位）
    for loc, s in rev_sents:
        if cjk_ratio(s) > 0.3 and re.search(r"[,;:!?](?!\d)", s):
            hard.append({"kind": "cn_en_punct_mix", "location": loc,
                         "snippet": re.findall(r".{0,12}[,;:!?](?!\d).{0,12}", s)[:2]})
        elif cjk_ratio(s) < 0.1 and re.search(r"[，。；：！？]", s):
            hard.append({"kind": "en_cn_punct_mix", "location": loc,
                         "snippet": re.findall(r".{0,12}[，。；：！？].{0,12}", s)[:2]})

    # ---- 整句增删（润色不该删作者内容）----
    sentence_dropped = [{"location": src_sents[i][0], "source": src_sents[i][1][:200],
                         "action": "整句在改文中消失：确认是有意删除还是漏保留；润色不得删掉作者内容或图表指向"}
                        for i in lost_src]
    sentence_added = [{"location": rev_sents[j][0], "revised": rev_sents[j][1][:200],
                       "action": "改文出现原文没有的句子：核对是否新增了事实、解释或结论"}
                      for j in added_rev]

    # ---- 过度改写 / 漏改 ----
    over_edit, heavy_edit = [], []
    for pr in pairs:
        if not pr["changed"]:
            continue
        s = src_sents[pr["src_idx"]][1]
        r = rev_sents[pr["rev_idx"]][1]
        loc = f"{src_sents[pr['src_idx']][0]}->{rev_sents[pr['rev_idx']][0]}"
        if not same_script(s, r):
            continue  # 跨语言改写（中译英等）相似度无意义
        if len(s) < 40:
            continue
        if pr["similarity"] < 0.55:
            over_edit.append({"location": loc, "similarity": pr["similarity"],
                              "source": s[:160], "revised": r[:160],
                              "action": "相似度过低：接近整句重写，违反最小编辑原则，只改错处"})
        elif pr["similarity"] < 0.75:
            heavy_edit.append({"location": loc, "similarity": pr["similarity"],
                               "source": s[:160], "revised": r[:160],
                               "action": "改动偏大：确认是否属于无必要同义替换，能用最小编辑就不用重写"})
    over_edit, heavy_edit = over_edit[:40], heavy_edit[:40]

    changed_pairs = [p for p in pairs if p["changed"]]
    edit_rate = round(len(changed_pairs) / max(1, len(pairs)), 4)

    # ---- 修改清单覆盖 ----
    changes = []
    if args.changes:
        try:
            cdata = json.loads(Path(args.changes).read_text(encoding="utf-8"))
            changes = cdata.get("changes") if isinstance(cdata, dict) else cdata
            changes = changes or []
        except Exception:
            changes = []
    ch_incomplete, ch_unmatched, ch_without_effect, covered_src = [], [], [], set()
    src_norm_all, rev_norm_all = norm(src), norm(rev)
    for i, c in enumerate(changes, 1):
        o = str(c.get("original") or "").strip()
        rv = str(c.get("revised") or "").strip()
        typ = str(c.get("type") or "").strip()
        rsn = str(c.get("reason") or "").strip()
        if not o or not rv:
            ch_incomplete.append({"index": i, "missing": "original/revised 为空"})
            continue
        if not typ or not rsn:
            ch_incomplete.append({"index": i, "missing": "type 或 reason 为空",
                                  "original": o[:80]})
        if norm(o) and norm(o) not in src_norm_all:
            ch_unmatched.append({"index": i, "original": o[:120],
                                 "action": "该条 original 在原文中找不到，可能记录有误或原文已变"})
            continue
        if norm(rv) and norm(rv) not in rev_norm_all:
            ch_without_effect.append({"index": i, "revised": rv[:120],
                                      "action": "记录声称改成这样，但改文里找不到该写法：记录与实际不一致"})
        for pr in changed_pairs:
            if norm(o) in norm(src_sents[pr["src_idx"]][1]):
                covered_src.add(pr["src_idx"])
    uncovered = [{"location": src_sents[p["src_idx"]][0],
                  "revised_location": rev_sents[p["rev_idx"]][0],
                  "similarity": p["similarity"],
                  "source": src_sents[p["src_idx"]][1][:160],
                  "action": "此句被改动但修改清单里没有对应条目，补记录（否则评审无法判断该不该改）"}
                 for p in changed_pairs if p["src_idx"] not in covered_src]

    report = {
        "ok": True,
        "source": str(args.source), "revised": str(args.revised),
        "sentences": {"source": len(src_sents), "revised": len(rev_sents), "aligned": len(pairs),
                      "source_only": len(lost_src), "revised_only": len(added_rev),
                      "changed": len(changed_pairs), "edit_rate": edit_rate},
        "faithfulness": {
            "number_changed": number_changed[:40], "number_changed_count": len(number_changed),
            "unit_changed": unit_changed[:40], "unit_changed_count": len(unit_changed),
            "citation_changed": cite_changed[:40], "citation_changed_count": len(cite_changed),
            "figref_changed": figref_changed[:40], "figref_changed_count": len(figref_changed),
            "hedge_removed": hedge_removed[:40], "hedge_removed_count": len(hedge_removed),
            "hedge_upgraded": hedge_upgraded[:40], "hedge_upgraded_count": len(hedge_upgraded),
            "hedge_added": hedge_added[:40], "hedge_added_count": len(hedge_added),
            "hedge_downgraded": hedge_downgraded[:40], "hedge_downgraded_count": len(hedge_downgraded),
            "negation_changed": neg_changed[:40], "negation_changed_count": len(neg_changed),
            "intensity_dropped": intens_dropped[:40], "intensity_dropped_count": len(intens_dropped),
            "sentence_dropped": sentence_dropped[:40], "sentence_dropped_count": len(sentence_dropped),
            "sentence_added": sentence_added[:40], "sentence_added_count": len(sentence_added),
            "global_diff": global_diff,
        },
        "terms": {"checked": len(gterms), "missing": glossary_missing[:40],
                  "missing_count": len(glossary_missing),
                  "inconsistent": glossary_inconsistent[:40],
                  "inconsistent_count": len(glossary_inconsistent),
                  "skipped": glossary_na[:40], "skipped_count": len(glossary_na)},
        "register": register, "register_count": register_count,
        "hard_errors": hard[:80], "hard_error_count": len(hard),
        "over_edit": over_edit, "over_edit_count": len(over_edit),
        "heavy_edit": heavy_edit, "heavy_edit_count": len(heavy_edit),
        "changes_coverage": {"records": len(changes), "uncovered_count": len(uncovered),
                             "uncovered": uncovered[:40],
                             "unmatched": ch_unmatched[:40], "unmatched_count": len(ch_unmatched),
                             "without_effect": ch_without_effect[:40],
                             "without_effect_count": len(ch_without_effect),
                             "incomplete": ch_incomplete[:40], "incomplete_count": len(ch_incomplete)},
        "verification_hint": {
            "semantic_preservation": (
                f"限定漂移 {len(hedge_removed) + len(hedge_added)} 处（升级 {len(hedge_upgraded)}、"
                f"新增限定 {len(hedge_downgraded)}）；强度词丢失 {len(intens_dropped)} 处；"
                f"否定范围变化 {len(neg_changed)} 处；整句消失 {len(sentence_dropped)} 处；"
                f"新增句 {len(sentence_added)} 处"),
            "data_units_citations": (
                f"数字差异 {len(number_changed)} 处；单位差异 {len(unit_changed)} 处；"
                f"引用差异 {len(cite_changed)} 处；图表指向差异 {len(figref_changed)} 处"),
            "minimal_edit": (
                f"改动句 {len(changed_pairs)} / 对齐句 {len(pairs)}（编辑率 {edit_rate}）；"
                f"疑似整句重写 {len(over_edit)} 处；改动偏大 {len(heavy_edit)} 处"),
            "traceability": (
                f"修改记录 {len(changes)} 条；未记录改动 {len(uncovered)} 处；"
                f"记录在原文找不到 {len(ch_unmatched)} 条；记录与改文不符 {len(ch_without_effect)} 条；"
                f"记录字段不全 {len(ch_incomplete)} 条"),
            "register_and_errors": (
                f"语域问题 {register_count} 处（口语 {len(register['colloquial'])}、"
                f"宣传 {len(register['promotional'])}、绝对 {len(register['absolute'])}）；"
                f"硬错误 {len(hard)} 处"),
            "glossary": (f"术语 {len(gterms)} 条；未落实 {len(glossary_missing)} 条；"
                         f"写法不一致 {len(glossary_inconsistent)} 条；跨语言跳过 {len(glossary_na)} 条"),
        },
    }

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "edit_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_md(report, outdir / "edit_report.md")
    print(json.dumps({k: report[k] for k in ["sentences", "register_count", "hard_error_count",
                                             "over_edit_count", "heavy_edit_count"]} |
                     {"hedge_removed_count": report["faithfulness"]["hedge_removed_count"],
                      "hedge_upgraded_count": report["faithfulness"]["hedge_upgraded_count"],
                      "hedge_added_count": report["faithfulness"]["hedge_added_count"],
                      "intensity_dropped_count": report["faithfulness"]["intensity_dropped_count"],
                      "sentence_dropped_count": report["faithfulness"]["sentence_dropped_count"],
                      "number_changed_count": report["faithfulness"]["number_changed_count"],
                      "citation_changed_count": report["faithfulness"]["citation_changed_count"],
                      "figref_changed_count": report["faithfulness"]["figref_changed_count"],
                      "changes_uncovered": report["changes_coverage"]["uncovered_count"],
                      "changes_without_effect": report["changes_coverage"]["without_effect_count"]},
                     ensure_ascii=False))
    return 0


def write_md(r, path):
    f = r["faithfulness"]
    md = ["# 润色核验报告（最小编辑 / 语义守恒 / 可追溯）", "",
          f"- 句子：原文 {r['sentences']['source']} / 改文 {r['sentences']['revised']}"
          f" / 对齐 {r['sentences']['aligned']} / 改动 {r['sentences']['changed']}"
          f"（编辑率 {r['sentences']['edit_rate']}）",
          f"- 语义守恒：限定漂移 {f['hedge_removed_count'] + f['hedge_added_count']}"
          f"（升级 {f['hedge_upgraded_count']}）/ 强度词丢失 {f['intensity_dropped_count']}"
          f" / 否定变化 {f['negation_changed_count']}"
          f" / 整句消失 {f['sentence_dropped_count']} / 新增句 {f['sentence_added_count']}",
          f"- 数据保真：数字 {f['number_changed_count']} / 单位 {f['unit_changed_count']}"
          f" / 引用 {f['citation_changed_count']} / 图表 {f['figref_changed_count']}",
          f"- 语域 {r['register_count']} / 硬错误 {r['hard_error_count']}"
          f" / 疑似整句重写 {r['over_edit_count']} / 改动偏大 {r.get('heavy_edit_count', 0)}",
          f"- 修改清单：{r['changes_coverage']['records']} 条，未记录改动 "
          f"{r['changes_coverage']['uncovered_count']} 处，记录对不上原文 "
          f"{r['changes_coverage']['unmatched_count']} 条，记录与改文不符 "
          f"{r['changes_coverage'].get('without_effect_count', 0)} 条", ""]
    sections = [
        ("限定被升级为强断言（最危险）", f["hedge_upgraded"]),
        ("限定被删掉", f["hedge_removed"]),
        ("新增限定（削弱结论）", f["hedge_added"]),
        ("强度词被吞掉", f["intensity_dropped"]),
        ("整句在改文中消失", f["sentence_dropped"]),
        ("改文新增原文没有的句子", f["sentence_added"]),
        ("否定范围变化", f["negation_changed"]),
        ("数字被改动", f["number_changed"]),
        ("单位被改动", f["unit_changed"]),
        ("引用标记被改动", f["citation_changed"]),
        ("图表/公式指向被改动", f["figref_changed"]),
        ("术语未落实", r["terms"]["missing"]),
        ("术语写法不一致", r["terms"]["inconsistent"]),
        ("术语检查跳过（跨语言）", r["terms"]["skipped"]),
        ("语域-口语化", r["register"]["colloquial"]),
        ("语域-宣传化", r["register"]["promotional"]),
        ("语域-绝对化", r["register"]["absolute"]),
        ("硬错误", r["hard_errors"]),
        ("疑似整句重写（违反最小编辑）", r["over_edit"]),
        ("改动偏大（确认是否无必要替换）", r["heavy_edit"]),
        ("被改动但未写进修改清单", r["changes_coverage"]["uncovered"]),
        ("修改记录对不上原文", r["changes_coverage"]["unmatched"]),
        ("修改记录与改文不符", r["changes_coverage"]["without_effect"]),
        ("修改记录字段不全", r["changes_coverage"]["incomplete"]),
    ]
    for label, items in sections:
        if items:
            md += [f"## {label}（{len(items)}）", ""]
            for it in items[:20]:
                md.append(f"- {json.dumps(it, ensure_ascii=False)[:260]}")
            md.append("")
    md += ["## 自检口径（可直接写入 verification）", ""]
    md += [f"- `{k}`：{v}" for k, v in r["verification_hint"].items()]
    path.write_text("\n".join(md), encoding="utf-8")


def cmd_report(args):
    try:
        r = json.loads(Path(args.report).read_text(encoding="utf-8"))
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"读取失败：{e}"}, ensure_ascii=False))
        return 1
    p = Path(args.report).with_suffix(".md")
    write_md(r, p)
    print(json.dumps({"ok": True, "out": str(p)}, ensure_ascii=False))
    return 0


def main():
    ap = argparse.ArgumentParser(description="学术润色核验器：最小编辑 / 语义守恒 / 可追溯")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("split")
    s.add_argument("--text", required=True)
    s.add_argument("--out", required=True)

    t = sub.add_parser("terms")
    t.add_argument("--text", required=True)
    t.add_argument("--out", required=True)

    l = sub.add_parser("lint")
    l.add_argument("--source", required=True)
    l.add_argument("--revised", required=True)
    l.add_argument("--glossary")
    l.add_argument("--changes")
    l.add_argument("--out", required=True)

    r = sub.add_parser("report")
    r.add_argument("--report", required=True)

    a = ap.parse_args()
    return {"split": cmd_split, "terms": cmd_terms, "lint": cmd_lint,
            "report": cmd_report}[a.cmd](a) or 0


if __name__ == "__main__":
    sys.exit(main())
