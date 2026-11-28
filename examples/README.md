# 最小调用示例（示意）

以下用一份**合成的教学样例**（4 段英文摘要式文本，非任何真实稿件）走完从原稿到核验报告的全流程，用于说明接口与输出。**不是正式案例答案，也不是任何真实稿件的润色结果。**

## 一、输入

原稿 `/app/work/source.txt`（合成样例）：

```text
LiFePO4 electrodes may deliver a capacity retention of 92% after 500 cycles at 1C [1].

The XRD patterns show no impurity phase, and the SEM images reveal uniform particles of 200 nm.

The diffusion coefficient was significantly increased by 3.5 times compared with the pristine sample [2,3], which suggests that surface coating plays a key role.

We only observed a slight decrease in rate capability at high current density (Fig. 3).
```

改稿 `/app/output/polished_text.md`（**故意保留 4 处典型事故**用于演示检出）：

```text
LiFePO4 electrodes deliver a capacity retention of 92% after 500 cycles at 1C [1].

The XRD patterns showed no impurity phase, and SEM images revealed uniform particles of 200 nm.

The diffusion coefficient was increased by 3.5 times compared with the pristine sample [2], which demonstrates that surface coating plays a crucial role.

We observed a decrease in rate capability at high current density.
```

## 二、调用方式

```bash
L=/skills/weekly-skill/resources/scripts/edit_lint.py

# 1) 术语摸底：大小写/连字符漂移 + 缩写首次定义 + 候选术语
python3 "$L" terms --text /app/work/source.txt --out /app/work

# 2) 句级切分（可选，需要逐句定位时用）
python3 "$L" split --text /app/work/source.txt --out /app/work

# 3) 六类核验：语义守恒 / 数据保真 / 术语 / 语域与硬错误 / 最小编辑 / 修改清单覆盖
python3 "$L" lint --source /app/work/source.txt \
                  --revised /app/output/polished_text.md \
                  --glossary /app/output/glossary.json \
                  --changes /app/output/changes.json --out /app/output
```

## 三、真实运行输出（本次实测，非虚构）

`lint` 的 stdout：

```json
{"sentences": {"source": 4, "revised": 4, "aligned": 4, "source_only": 0, "revised_only": 0,
               "changed": 4, "edit_rate": 1.0},
 "hedge_removed_count": 2, "hedge_upgraded_count": 1, "hedge_added_count": 0,
 "intensity_dropped_count": 2, "sentence_dropped_count": 0,
 "number_changed_count": 0, "citation_changed_count": 1, "figref_changed_count": 1,
 "register_count": 0, "hard_error_count": 0, "over_edit_count": 0,
 "changes_uncovered": 3, "changes_without_effect": 0}
```

`edit_report.md` 的关键几行：

```text
## 限定被升级为强断言（最危险）（1）
- {"location": "p3/s1->p3/s1", "...": "...", "action": "限定被升级为强断言（may/suggest → show/demonstrate），这是最危险的一类改动"}

## 限定被删掉（2）
- {"location": "p1/s1->p1/s1", "source": "...may deliver...", "revised": "...deliver...", ...}

## 强度词被吞掉（2）
- {"location": "p3/s1->p3/s1", "missing_terms": ["significantly"], ...}
- {"location": "p4/s1->p4/s1", "missing_terms": ["only"], ...}

## 引用标记被改动（1）
- {"location": "p3/s1->p3/s1", "missing": {"[2,3]": 1}, "action": "引用标记被删改，必须原样保留"}

## 图表/公式指向被改动（1）
- {"location": "p4/s1->p4/s1", "missing": {"fig. 3": 1}, ...}

## 被改动但未写进修改清单（3）
```

读法：四处事故全部被抓到——`may deliver → deliver`（限定被删）、`suggests → demonstrates`（升级为强断言，最危险）、`significantly` 与 `only` 被吞、`[2,3] → [2]` 引用被删、`(Fig. 3)` 指向丢失、3 处改动没写进修改清单。这些都是"读起来更顺了但主张被改了"的典型，人工通读极易漏过。

## 四、第二个样例：中文稿 + 整句消失

原稿 4 段中文，改稿只剩 3 段（第 4 段整段丢失），且把「可能表明/在一定程度上」改成「证明」、「仅/显著」删掉、加了「完全」：

```json
{"sentences": {"source": 4, "revised": 3, "aligned": 3, "source_only": 1, "changed": 3},
 "hedge_removed_count": 2, "hedge_upgraded_count": 1, "intensity_dropped_count": 1,
 "sentence_dropped_count": 1, "number_changed_count": 0, "citation_changed_count": 0,
 "figref_changed_count": 0, "register_count": 1, "hard_error_count": 2, "changes_uncovered": 2}
```

读法：`sentence_dropped_count: 1` 精确指出第 4 段整段消失；`register_count: 1` 抓到「完全」这一绝对化表述；`intensity_dropped` 给出被吞的具体词 `["仅","显著"]`；`hard_error_count: 2` 抓到「92% ,」空格前标点与中英标点混用。中文稿同样适用。

## 五、另一个样例：术语漂移与硬错误

`terms` 对一段混用 `XRD`/`Xrd`、`e-mail`/`email` 的文本：

```json
{"ok": true, "case_drift_count": 1, "abbrev_undefined_count": 1}
```

```json
[{"normalized": "xrd", "forms": {"XRD": 3, "Xrd": 1}, "reason": "大小写形状不一致", ...},
 {"normalized": "email", "forms": {"e-mail": 2, "email": 1}, "reason": "连字符写法不一致", ...}]
```

句首大写的 `The`/`the` **不会**被判为漂移——判定按"词形形状"（全大写/首字母大写/全小写/混合）做，只有出现全大写或混合形状、或连字符写法不一致才算。

`lint` 对英文硬错误的检出（`hard_errors`）：

```text
repeated_word | is is
subject_verb_agreement | results shows
article_a_vowel | a apple
article_an_consonant | an book
sentence_start_lowercase | the results shows ...
```

`a unique setup` 与 `an hour` **不会**误报——冠词检查内置读音例外表。

## 六、示意输出结构

见 `../resources/output_example.json`：`polished_text` 为完整改稿，`changes` 逐处记录原文/改文/类型/理由/位置，`glossary` 给 canonical 与依据，`verification` 与 `edit_report` 带计数，`uncertainties` 记录需人工确认项。

## 七、说明

- 上述样例文本为合成的教学用例，不代表任何真实稿件的润色质量。
- 真实评测由平台用固定的 3 个案例运行，参赛者不提供测试案例或白板。
- 提交包不含任何 `result.json`；运行时的结果只对应当次真实输入。
