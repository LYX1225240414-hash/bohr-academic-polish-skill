# 最小调用示例（示意）

以下仅为字段结构演示，不是正式案例答案，也不是任何真实稿件的润色结果。

## 输入

```text
请按期刊论文语域润色下面这段摘要，要求：修正硬错误、统一术语、保留限定强度与数据，并逐处给出修改理由。
[此处粘贴原文]
```

## 调用方式

在 Agent 中加载本 Skill（评测环境中位于 `/skills/weekly-skill`）。评测时 Agent 先读 `/input/case.json` 与 `/input/task.md`，按 SKILL.md 的第 0–6 步执行：解析输出契约 → 读取边界 → 抽取不变量与术语表 → 分句最小编辑 → 全篇回扫 → 自检回修 → 写 `/app/output/result.json` 与可编辑稿件。

普通使用时，把待润色文本或文件路径与目标文体一起发给 Agent 即可；输出 `result.json` 中未由输入提供 `output_contract` 时采用 SKILL.md 的扩展字段。

## 示意输出

见 `../resources/output_example.json`：`polished_text` 为完整改稿，`changes` 逐处记录原文/改文/类型/理由/位置，`glossary` 逐项给统一写法与依据，`verification` 逐项给结果与证据，`uncertainties` 记录需人工确认项。示意内容全部是结构占位符。

## 说明

- 示意输出里的文字仅展示结构，不代表任何真实稿件的润色质量。
- 真实评测由平台用固定的 3 个案例运行，参赛者不提供测试案例或白板。
- 提交包不含任何 `result.json`；运行时的结果只对应当次真实输入。
