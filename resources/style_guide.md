# 分文体语域要点

## 期刊论文（研究论文）
- 客观、第三人称或被动语态为主；避免口语与第一人称单数。
- 结论用限定表述，避免绝对化（prove/always/never 需谨慎）。
- 术语遵循目标期刊与领域惯例。

## 学位论文
- 允许适度第一人称（"本文"/"本研究"）；叙述完整、衔接清晰。
- 章节间术语必须一致；方法章用过去时，普遍结论用现在时。

## 基金申请书
- 强调问题的重要性与创新性，但避免宣传化与夸大。
- 目标与可交付成果表述具体；避免绝对化承诺。

## 审稿回复
- 语气礼貌、逐点对应审稿意见；承认合理批评，明确修改位置。
- 不回避问题，不改变审稿人意见的原意。

## 英文摘要
- 结构：背景 → 方法 → 结果 → 结论；结果给具体数据。
- 避免直译腔与冗余名词化；主语与信息重心按英文习惯重排。

## 通用红线
- 限定强度守恒：may/can/partially/significantly 不可随意升级为 is/proves。
- 因果 ≠ 相关：correlate with 不可改为 cause。
- 数据与单位不参与润色。
- 引用编号与图表指向不参与润色；编号不得合并、重排或"优化"。
- 不删原文句子；确需删（如重复句）必须写入 `changes` 并在 `uncertainties` 说明。

## 脚本可检的语域词表（`edit_lint.py` 内置，改稿里出现即报）

| 类别 | 词例 | 处置 |
|---|---|---|
| 口语化 | a lot of, lots of, kind of, pretty much, really, very, huge, big, stuff, get/got, a bit | 换学术表达：substantially / considerably / obtain / a small amount of |
| 宣传化 | groundbreaking, unprecedented, revolutionary, cutting-edge, world-class, paradigm shift；重大突破、国际领先、填补空白 | 删除或改为可验证的具体表述（如"较基线提升 X%"） |
| 绝对化 | always, never, completely, totally, entirely, undoubtedly, certainly, obviously；完全、必然、毫无疑问、绝对 | 弱化并限定适用范围（in this system / under the tested conditions） |

> 注：`novel`、`significantly`、`consistent with` 这类在学术写作中高频且合法的词**不在**告警词表内，不要为了"看起来更学术"而替换它们——替换会触发强度词丢失告警。

## 分文体语域速查

| 文体 | 人称 | 时态 | 限定密度 | 特别禁止 |
|---|---|---|---|---|
| 期刊论文 | 第三人称/被动 | 方法过去时、结论现在时 | 高 | 宣传化、绝对化 |
| 学位论文 | 可"本文/本研究" | 章节混合 | 中 | 章节间术语不一致 |
| 基金申请书 | 可"我们" | 将来时为主 | 中 | 夸大承诺、无依据的"首次" |
| 审稿回复 | 第一人称复数 | 现在/过去混用 | 低 | 回避问题、曲解审稿意见 |
| 英文摘要 | 第三人称 | 结果过去时、结论现在时 | 中 | 直译腔、冗余名词化 |
