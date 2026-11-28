# 学术语言润色 Skill（最小编辑 · 语义守恒 · 可追溯）

玻尔科学空间高校挑战赛 · 北京化工大学分站赛 —— 写作02｜学术语言润色 赛题作品。

## 简介

面向学术稿件的润色 Skill，核心不是"改得更漂亮"，而是**最小编辑 + 语义守恒 + 全程可追溯**。它解决的是润色里最隐蔽的事故：读起来更顺了，但作者的限定强度被悄悄改掉、数字单位被顺手换掉、引用编号被合并、整句被重写成了另一种主张。

两条核心设计：

1. **不变量先立、后改**——润色前把数字、单位、限定词、否定、引用编号、图表指向逐字记成清单，改完逐项比对。
2. **守恒靠机械核验**——`edit_lint.py` 把原稿与改稿做句级对齐后逐句比对，把"限定被删/被升级为强断言/强度词被吞/整句消失/改了却没写进清单"变成可数的计数，而不是靠通读感觉。

## 目录结构

```
SKILL.md                           Skill 定义（YAML frontmatter + 7 步工作流 + 运行契约）
environment/resources.yaml         资源清单、依赖、运行时与产物说明
resources/scripts/edit_lint.py     执行内核：split / terms / lint / report（纯标准库，可离线）
resources/field_dict.md            字段字典、location 格式、changes 条目规范与 type 取值
resources/gain_protocol.md         使用增益对照协议与 gain_record 记录格式
resources/checklist.md             带计数口径的自检清单（对应 verification 八项）
resources/style_guide.md           分文体语域要点 + 通用红线 + 脚本可检的语域词表
resources/output_example.json      输出结构示意（非答案）
examples/README.md                 最小调用示例（含真实实测输出，非虚构）
```

## 执行内核 `edit_lint.py`

四个子命令，纯标准库（`argparse`/`re`/`json`/`difflib`/`collections`/`pathlib`），无第三方依赖：

| 子命令 | 作用 |
|---|---|
| `terms` | 抽候选术语；检大小写/连字符漂移（`XRD`/`Xrd`、`e-mail`/`email`）；检缩写首次出现是否给全称 |
| `split` | 句级切分，输出 `p<段>/s<句>` 定位 |
| `lint` | 原稿 vs 改稿句级对齐后做六类核验（见下） |
| `report` | 由 `edit_report.json` 重新生成人读 md |

`lint` 的六类检查：

| 类别 | 具体项 |
|---|---|
| 语义守恒 | `hedge_removed` / `hedge_upgraded`（升级为强断言）/ `hedge_added` / `intensity_dropped` / `negation_changed` / `sentence_dropped` / `sentence_added` |
| 数据保真 | `number_changed` / `unit_changed` / `citation_changed` / `figref_changed` |
| 术语 | canonical 未落实 / 多种写法并存 / 跨语言自动跳过 |
| 语域与硬错误 | 口语化、宣传化、绝对化；双空格、空格前标点、重复词、主谓一致、冠词 a/an、句首小写、中英标点混用 |
| 最小编辑 | `over_edit`（相似度 <0.55，疑似整句重写）/ `heavy_edit`（<0.75，改动偏大） |
| 修改清单覆盖 | `uncovered`（改了没记录）/ `unmatched`（记录找不到原文）/ `without_effect`（记录与改文不符）/ `incomplete`（缺 type/reason） |

工程上刻意处理了五个容易误报的地方，避免"脚本乱报带着人改坏稿子"：

- 切句保护 `et al.` / `Fig.` / `Eq.` 等缩写，`(Fig. 3)` 不会被切成两句。
- 数数字前剥掉引用标记与图表编号，`[2,3]` 的 2、3 不会被当数值重复报。
- 术语表与改稿语言不一致时（英文学术稿配中文译名）自动进 `terms.skipped`，不误报"未落实"。
- 冠词检查内置读音例外（`a unique`、`an hour` 不误报）。
- 术语漂移按"词形形状"判，句首大写的 `The`/`the` 不算漂移；跨语言改写（中译英）不做相似度判定。

## 使用方式

在支持 Skill 的 Agent 环境中加载本目录，把待润色文本或路径与目标文体一起交给 Agent。Agent 按 SKILL.md 的工作流执行：

落盘骨架 → 确认输入边界 → `terms` 摸底并建术语表 → 分句级最小编辑（产出改稿与 `changes.json`）→ `lint` 机械核验并回修 → 语域回扫 → 增益记录 → 自检与输出。

## 输出约定

`/app/output/result.json` 原样回填 `case_id`、完整包含 `output_contract` 全部字段，并提供 `polished_text`、`changes`、`glossary`、`verification`（八项带计数）、`edit_report`（转述 `edit_report.json`）、`gain_record`、`uncertainties`、`change_log`、`scope`。同时落盘可编辑改稿 `polished_text.md`、修改清单 `changes.json` 与核验报告 `edit_report.md`。

## 版本

- v1.1.0：接入 `edit_lint.py` 执行内核；新增 `environment/resources.yaml`、`field_dict.md`、`gain_protocol.md`；`checklist` 补计数口径表；`style_guide` 补脚本可检语域词表与分文体速查。
- v1.0.0：不变量清单 + 分句最小编辑 + 自检清单的纯文档版工作流。

## 授权

仅供赛事评审与学习交流使用。
