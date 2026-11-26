# 最小调用示例（示意）

以下仅为字段结构演示，不是正式案例答案，也不是任何真实稿件的润色结果。

## 输入

```text
请按期刊论文语域润色下面这段摘要，要求：修正硬错误、统一术语、保留限定强度与数据，并逐处给出修改理由。
[此处粘贴原文]
```

## 调用方式

在 Agent 中加载本 Skill（目录 p02-skill/），把上述输入直接发给 Agent。Agent 会按 SKILL.md 的 6 步流程执行，输出 result.json。

## 示意输出

见 ../resources/output_example.json，其中 polished_text 为完整改稿，changes 逐处记录原文/改文/类型/理由/位置，术语进 glossary，守恒自检进 verification，需人工确认项进 uncertainties。

## 说明

- 示意输出里的文字仅展示结构，不代表任何真实稿件的润色质量。
- 真实评测由平台用固定的 3 个案例运行，参赛者不提供测试案例或白板。
