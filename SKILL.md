---
name: academic-polish-faithful
description: 学术语言润色的「最小编辑 + 语义守恒 + 可追溯」工作流，在不改变作者主张的前提下修正硬错误、统一全篇术语、守住限定强度与引用指向，并逐处输出可复核的原文-改文对照；内置可离线运行的核验脚本（edit_lint.py），把原稿与改稿做句级对齐后机械检出限定被删或升级为强断言、强度词被吞掉、否定范围变化、数字/单位/引用/图表指向被改、整句消失或新增、术语大小写与连字符漂移、口语化与绝对化表述、常见硬错误，以及「改了却没写进修改清单」；当用户要求润色英文学术稿件、检查术语漂移、核对改写是否悄悄加强或削弱结论、或需要带理由的逐句修改清单时使用，支持期刊论文、学位论文、基金申请书、摘要与审稿回复。
---

# 学术语言润色：改得对、说得像、没改坏、讲得清

把学术稿件润色成语言过硬、术语统一、语义守恒的文本，同时交付**逐处可核验的修改记录**。核心不是"重写得更漂亮"，而是**最小编辑 + 语义守恒 + 全程可追溯**。

## 何时使用

- 需要润色学术稿件的语法、术语、语气、中英文表达，且要求保留作者原意。
- 需要一份能交给第三方判断"这处该不该改"的原文—改文对照。
- 涉及限定词强度、数据单位、引用编号、图表指向等不能被改写的要素。

不适用：纯内容问答、要求整段重写或代写新内容、无原文材料的场景。用户只想讨论内容而不要求改稿时，不擅自改写。

## 评测环境运行契约（必须遵守）

平台会把本 Skill 安装到 `/skills/weekly-skill`，用固定的 3 个案例运行：

1. **先读真实输入**：读取 `/input/case.json` 与 `/input/task.md`。`case.json` 可能含 `case_id`、`output_contract`、材料文件路径、文体/受众/禁止改动项等；**以实际字段为准**，不要从标签或文件名猜材料内容。材料文件按给出的路径逐个打开读取。
2. **工作目录**：中间文件写在 `/app/work`，不要污染输入目录。资源文件从 `/skills/weekly-skill/resources/` 读取。
3. **最终产物**：写入 `/app/output/result.json`（UTF-8、合法 JSON），并同时保存可编辑稿件 `/app/output/polished_text.md` 与修改清单 `/app/output/changes.md` 供复核。
4. **输出字段**：若 `case.json` 提供 `output_contract`，逐字段原样包含其中所有字段（不得改名、不得遗漏），再补充本 Skill 的扩展字段；若无 `output_contract`，使用下节结构。`case_id` 必须来自输入。
5. **尽早落盘**：先写一份 `status: partial` 的骨架结果到 `/app/output/result.json`，再逐段完善并覆盖更新；运行中断时也留下诚实的部分产物，不要事后编造。
6. **预算**：控制在 64 次模型请求、900 秒、单次 16384 tokens 内；长文分块处理，优先保证覆盖全部原文和结构化字段，再追求措辞精致。
7. **禁止**：提交预制答案、正式案例答案或假造的运行日志/成绩；本 Skill 包内不应含任何 `result.json`。

## 输入输出

输入：待润色文本或文件路径（TXT / MD / LaTeX 片段 / 章节稿）；可选：目标文体（期刊/学位/基金/审稿回复）、术语表、目标读者、禁止改动项。

输出：结构化结果 `result.json`，字段如下（`output_contract` 字段优先）：

| 字段 | 要求 |
|---|---|
| case_id | 输入标识；无则填 `N/A` |
| status | `success` / `partial` / `unable` / `refused`；部分完成必须说明未完成范围 |
| polished_text | 润色后的**完整**文本，段落数与原文一致，不省略、不改写为建议 |
| changes | 逐处修改数组，每处含 `original` / `revised` / `type` / `reason` / `location`；`location` 用到章节+段号+句号 |
| glossary | 数组，每项含 `term` / `canonical` / `positions` / `decision_basis`；统一写法逐条回扫确认 |
| verification | 字符串键到对象的映射，逐项给 `result`（pass/fail/na）与 `evidence`（**带具体计数**）：`semantic_preservation`（限定漂移/强度词/否定/整句增删）、`data_units_citations`、`minimal_edit`、`traceability`、`register_and_errors`、`glossary_consistent`、`causality_preserved`（人工）、`no_new_facts` |
| edit_report | 对象，原样转述 `edit_report.json` 的关键计数（`sentences` / `faithfulness` / `changes_coverage` / `hard_error_count` / `register_count`），不得另算一套 |
| gain_record | 对象，含 `conditions` / `mode` / `baseline` / `with_skill` / `delta_note` / `verifiable_artifacts`；按 `resources/gain_protocol.md` 填写，无对照产出时写 `na` 并说明 |
| uncertainties | 需人工确认、材料冲突、无法判断的条目及原因；不把猜测写成事实 |
| change_log | 自检回修记录：问题、修正、位置、轮次 |
| scope | 已处理的章节/段落范围，供第三方判断完整性 |

## 工作流

### 第 0 步：解析案例与建立任务清单
读取 `case.json` / `task.md` 与全部材料文件；列出 `output_contract` 字段、待处理章节、文体、禁止改动项。立即写骨架 `result.json`（`status: partial`，`case_id` 已填），并把待办范围记入 `scope`。

### 第 1 步：读取输入边界
确认语言、文体、篇幅、是否有公式/引用/图表标记。缺文件 → `status: unable` 并说明具体缺失路径。识别目标文体：期刊论文/学位论文/基金申请/审稿回复/摘要，不同文体的语域要求不同。

### 第 2 步：抽取不变量并建术语表

先做**不变量清单**，逐字记录：数字与单位/有效数字、限定词（only/partially/significantly/may/can/主要/部分）、否定词、因果或相关动词、引用编号、图表编号与指向、缩写首次出现形式。终稿前要逐项比对，不因润色发生变化。

再从全文抽取术语与缩写，记录：原文写法、统一写法（canonical）、出现位置、定名依据。先跑脚本摸底：

```bash
L=/skills/weekly-skill/resources/scripts/edit_lint.py
python3 "$L" terms --text /app/work/source.txt --out /app/work
```

`terms` 输出 `terms_report.json`，给出三类可直接用的事实：

| 字段 | 用法 |
|---|---|
| `case_sensitive_drift` | 同一词出现多种写法（`XRD`/`Xrd`、`e-mail`/`email`），逐条定一个 canonical |
| `abbrev_first_use` / `abbrev_undefined_count` | 缩写首次出现附近有没有"中文全称（缩写）"式定义，没有的要补 |
| `term_candidates` | 候选术语与出现次数，作为术语表底稿 |

然后按脚本提示定术语表：

- 同一概念的中英文写法、缩写首次出现形式、大小写、连字符全篇统一。
- 检查引言与方法之间是否术语漂移，发现即锁定唯一写法。
- 术语表是执行依据：后续每处修改前必须重读。

### 第 3 步：分句级最小编辑
逐句处理，遵守最小编辑原则：

1. **硬错误优先**：主谓一致、时态语态、冠词介词、单复数、悬垂修饰、标点、长句切分——只改错处，不换说法掩盖。
2. **语义守恒（关键）**：逐句比对并原样保留——限定强度、否定范围、因果与相关性的区别、条件句、量词、数据、单位、有效数字、引用编号、图表指向。
3. **语域贴合**：消除口语化、宣传化、绝对化表述与人称误用；处理中式英语、直译腔、冗余名词化、逻辑连接词滥用；重新安排中译英的主语与信息重心，但不添加原文没有的事实。
4. 每处修改立即记入 `changes`：原文、改文、修改类型标签（语法/术语/语域/语义/格式）、理由、位置。改文只覆盖出错片段，其余句子原样保留。

**红线**：不做无必要的同义替换；不因润色加强或削弱结论；不新增材料外的任何事实、数字或引用。

同时落盘三份：`/app/output/result.json`、完整改稿 `/app/output/polished_text.md`（段落结构与原稿一致）、修改清单 `/app/output/changes.json`（与 `result.json` 的 `changes` 同源）。改稿必须是纯文本可读件，脚本要靠它核验。

### 第 4 步：机械核验与回修（没改坏 + 讲得清）

**先跑脚本，再人工判读**——限定漂移、强度词丢失、数字被改这类事故，靠通读几乎查不出来：

```bash
python3 "$L" lint --source /app/work/source.txt \
                  --revised /app/output/polished_text.md \
                  --glossary /app/output/glossary.json \
                  --changes /app/output/changes.json --out /app/output
```

产物：`/app/output/edit_report.json`（机读）、`/app/output/edit_report.md`（人读，按类别分组）。脚本把原稿与改稿做**句级对齐**，逐类处置如下：

| 类别 | 含义 | 必须动作 |
|---|---|---|
| `hedge_upgraded` | 限定被升级为强断言（may/suggests → is/demonstrates） | **改回原限定**。这是最危险的一类：悄悄把弱结论说成定论 |
| `hedge_removed` | 同句已无 hedge | 改回原限定，或在 `uncertainties` 写明为何去掉 |
| `hedge_added` | 原文没有限定，改后加了 | 删掉新增限定——等于削弱作者结论 |
| `intensity_dropped` | 强度词被吞（significantly/only/显著/仅） | 补回原强度词；强度不可随手改 |
| `sentence_dropped` / `sentence_added` | 整句消失 / 新增句 | 润色不得删作者内容；新增句要核对是否引入了原文没有的事实 |
| `negation_changed` | 否定词数量变化 | 逐处核对否定范围有没有被扩大或缩小 |
| `number_changed` / `unit_changed` | 数字或单位被改（引用与图表编号已剥离，不重复报） | 按原稿恢复；数据单位不参与润色 |
| `citation_changed` | `[n]` / `\cite` 被删改 | 原样恢复，不得合并或重编号 |
| `figref_changed` | 图/表/公式指向被改 | 核对是否仍指同一对象，改错即恢复 |
| `terms.missing` / `terms.inconsistent` | canonical 未出现 / 多种写法并存 | 统一为 canonical；跨语言术语表会被 `skipped` 跳过，不误报 |
| `register`（口语/宣传/绝对） | 语域不合目标文体 | 按 `resources/style_guide.md` 替换；绝对化需弱化并限定适用范围 |
| `hard_errors` | 双空格、空格前标点、重复词、主谓一致、冠词 a/an、句首小写、中英标点混用 | 逐条修正；冠词已排除 `a unique` / `an hour` 这类读音例外 |
| `over_edit` / `heavy_edit` | 相似度 <0.55 / <0.75 | 回第 3 步改回最小编辑。**跨语言改写（中译英）不做此项判定** |
| `changes_coverage.uncovered` | 句子被改了但清单里没有条目 | **补记录**；否则评审无法判断这处该不该改 |
| `changes_coverage.unmatched` / `without_effect` | 记录里的原文找不到 / 记录说的改文不存在 | 修正记录，不得让清单与改稿脱节 |
| `changes_coverage.incomplete` | 缺 `type` 或 `reason` | 补全；"改了但说不出为什么"等于不可核验 |

修完重跑 `lint`，直到语义守恒四类（`hedge_*` / `intensity_dropped` / `sentence_dropped` / `negation_changed`）与数据保真四类（number/unit/citation/figref）的计数全部为 0，或每条残留都在 `uncertainties` 有明确理由；`changes_coverage.uncovered` 应为 0。每轮回修写入 `change_log`。

脚本测不出、必须人工判断的部分（写进 `verification` 的 `causality_preserved` 与 `uncertainties`）：因果是否被改成相关、指代对象是否仍指同一事物、条件句范围是否被改、学科惯例上术语是否真的等价。**脚本给 0 差异不等于改对了意思，只等于没动数据、没动限定词。**

### 第 5 步：术语与语域全篇回扫
- 术语表逐条回扫全文，确认 canonical 写法一致、缩写首次出现给全称（对照 `terms_report.json` 的 `abbrev_first_use`）。
- 检查同一段落重复润色后结论是否漂移（稳定性）：对同一段跑两遍，比较 `lint` 计数是否一致。
- 检查语域是否贴合目标文体，跨章节是否一致。
- 对照第 2 步不变量清单，逐项写成 `verification` 的 `evidence`，不要只写"通过"。

### 第 5.5 步：增益记录（使用增益 25 分）

按 `resources/gain_protocol.md` 记录对照条件、指标与可复算产物，写入 `result.json` 的 `gain_record`。无外部白板时用"同一运行内两版改稿"方式：先按"直接通读改一遍"产出 `draft_blind.md`，再按本工作流产出定稿，两版**对照同一份原稿**分别跑 `lint`，比较语义守恒与可追溯项计数的变化。**不得编造对照数据**，测不出就写 `na` 并说明原因。

### 第 6 步：自检与输出
逐项核对 `resources/checklist.md`，**优先采用 `edit_report.json` 的机械计数**，只有脚本测不出的项才人工计数：

- 硬错误是否真改掉（不是换个说法）——取 `hard_error_count`。
- 限定强度/否定/因果/数据单位/引用编号/图表指向是否逐一保留——取 `faithfulness` 各计数，人工补因果与指代。
- 每处修改是否有 original / revised / type / reason / location——取 `changes_coverage` 的四类缺口。
- `polished_text` 段落数与原文一致；`scope` 覆盖任务要求的全部段落。
- 术语全篇一致；语域贴合；无新增事实。
- 需人工确认、材料冲突、无法判断处写入 `uncertainties`。

写 `/app/output/result.json`，校验 JSON 可解析、`output_contract` 字段齐全、`case_id` 正确、`verification` 每项带计数、`edit_report` 与 `edit_report.json` 数值一致。`partial` 状态必须指明未完成范围与可人工接管位置。

## 异常处理

| 情况 | 处理 |
|---|---|
| 超长输入 / 编码混乱 | 分块处理并标注边界；无法解码段落写入 `uncertainties` |
| 公式与引用混杂 / 中英日混排 | 公式与引用原样保留，只润色自然语言部分 |
| 术语表内部冲突 | 分列两条并写清位置，按位置区分，写入 `uncertainties` |
| 术语表与改文语言不一致 | 脚本会放入 `terms.skipped` 并说明原因，不误报"未落实"；按目标语言另给 canonical |
| 目标文体不明 | 按通用学术语域处理，并在 `uncertainties` 请求确认 |
| 引用编号无法核验 | 原样保留，说明无法核验，不猜 |
| 脚本报 source/revised 为空 | 检查路径与编码（必须 UTF-8）；改稿须是纯文本，不能只存在于 `result.json` 里 |
| 运行中断或时间不足 | 保留已写的 partial 结果与已完成段落，写明未完成范围 |

## 资源

- `resources/scripts/edit_lint.py`：**执行内核**。`split` 句级切分并给 `p<段>/s<句>` 定位、`terms` 抽术语并检大小写/连字符漂移与缩写首次定义、`lint` 做句级对齐后的六类核验（语义守恒 / 数据保真 / 术语 / 语域与硬错误 / 最小编辑 / 修改清单覆盖）、`report` 由 json 重出 md。纯标准库（`argparse`/`re`/`json`/`difflib`/`collections`/`pathlib`），无第三方依赖，可完全离线运行。
- `resources/checklist.md`：带计数口径的自检清单，对应 `verification` 六项。
- `resources/style_guide.md`：分文体语域要点与通用红线（含脚本可检的语域词表）。
- `resources/gain_protocol.md`：使用增益对照协议与 `gain_record` 记录格式。
- `resources/field_dict.md`：字段字典、`location` 与锚点格式、`changes` 条目规范。
- `resources/output_example.json`：输出结构示意（非答案）。
- `environment/resources.yaml`：资源清单、依赖、运行时与产物说明。
- `examples/README.md`：最小调用示例（含真实实测输出，非虚构）。

## 最小示例（示意，非真实稿件）

```bash
L=/skills/weekly-skill/resources/scripts/edit_lint.py
python3 "$L" terms --text /app/work/source.txt --out /app/work
python3 "$L" lint  --source /app/work/source.txt \
                   --revised /app/output/polished_text.md \
                   --glossary /app/output/glossary.json \
                   --changes /app/output/changes.json --out /app/output
```

示意输出（仅结构与计数口径，数值为占位）：

```json
{"sentences": {"source": 12, "revised": 12, "aligned": 12, "changed": 7, "edit_rate": 0.5833},
 "hedge_removed_count": 1, "hedge_upgraded_count": 1, "hedge_added_count": 0,
 "intensity_dropped_count": 1, "sentence_dropped_count": 0,
 "number_changed_count": 0, "citation_changed_count": 0, "figref_changed_count": 0,
 "register_count": 2, "hard_error_count": 3, "over_edit_count": 0,
 "changes_uncovered": 2, "changes_without_effect": 0}
```

真正的结果必须来自本次实际运行，示意输出不得冒充正式案例答案。
