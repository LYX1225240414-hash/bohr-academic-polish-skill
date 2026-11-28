# 使用增益对照协议（质量增益 / 效率增益 / 增益可验证性）

本题"使用增益"占 25 分，其中"增益可验证性 5 分"要求**用证据说明改善**，不能只写"改得更地道"。本协议给出可在单次运行内完成的对照记录方法。

## 1. 对照条件（必须一致）

| 项目 | 要求 |
|---|---|
| 原文 | 同一份原稿，一字不改 |
| 术语表 | 同一份 `glossary.json`；对照时不得换术语表 |
| 风格规则 | 同一份 `style_guide.md` 与目标文体 |
| 预算 | 同一模型、同一次运行预算（64 请求 / 900 秒） |
| 度量 | 同一组指标与同一判定口径（见第 3 节） |

不满足任一项，增益结论无效，写 `uncertainties` 说明对照不成立。

## 2. 两种记录方式（按可得性择一）

### 方式 A：同原稿两次产出的可对比指标（首选）
若平台提供基础 Agent 的产出，或可复跑一次不加载 Skill 的条件，对两份改稿分别跑 `edit_lint.py lint`（**都对照同一份原稿**），按第 3 节填表。

### 方式 B：单次运行内的两版改稿对照（无基础产出时）

1. 先按"直接通读改一遍"的方式产出 `/app/work/draft_blind.md`；
2. 再按本 Skill 工作流产出 `/app/output/polished_text.md`；
3. 两版都对照 `/app/work/source.txt` 跑 `lint`，比较下列计数的变化。

这种方式不是"跑两次模型"，而是**同一运行内的两版改稿**，成本低、可复核，且直接对应"是否减少了事后逐句校对与返工"的效率增益。

## 3. 指标与口径（只报能算出来的）

| 指标 | 定义 | 采集方式 |
|---|---|---|
| 限定漂移数 | `hedge_removed_count + hedge_added_count` | `edit_report.json`，应为 0 |
| 限定升级数 | 弱限定被改成强断言 | `hedge_upgraded_count`，尤其应为 0 |
| 强度词丢失数 | `significantly`/`only`/`显著`/`仅` 等被吞 | `intensity_dropped_count`，应为 0 |
| 整句增删数 | `sentence_dropped_count + sentence_added_count` | 应为 0 |
| 数据保真数 | 数字/单位/引用/图表指向差异合计 | 四类 `*_changed_count` 之和，应为 0 |
| 硬错误残留数 | 主谓一致、冠词、重复词、标点等 | `hard_error_count`，越低越好 |
| 语域问题数 | 口语/宣传/绝对化 | `register_count`，越低越好 |
| 最小编辑合规 | 疑似整句重写 + 改动偏大 | `over_edit_count + heavy_edit_count` |
| 修改清单覆盖 | 未记录改动 + 记录对不上原文 + 记录与改文不符 | `changes_coverage` 三项之和，应为 0 |
| 返工轮次 | 从初稿到定稿的修正轮数 | `change_log` 条目数 |
| 耗时 | 从读原稿到产出定稿的 wall time | 运行日志时间戳 |

## 4. 记录格式（写入 result.json）

```json
"gain_record": {
  "conditions": {"same_source": true, "same_glossary": true, "same_style": true, "same_budget": true},
  "mode": "B_single_run_two_drafts",
  "baseline": {"draft": "/app/work/draft_blind.md", "hedge_drift": 0, "hedge_upgraded": 0,
               "intensity_dropped": 0, "sentence_dropped": 0, "data_fidelity_issues": 0,
               "hard_error_count": 0, "register_count": 0, "changes_uncovered": 0},
  "with_skill": {"draft": "/app/output/polished_text.md", "hedge_drift": 0, "hedge_upgraded": 0,
                 "intensity_dropped": 0, "sentence_dropped": 0, "data_fidelity_issues": 0,
                 "hard_error_count": 0, "register_count": 0, "changes_uncovered": 0},
  "delta_note": "限定漂移由 N 降至 0；硬错误由 N 降至 M；未记录改动由 N 降至 0；返工 2 轮",
  "verifiable_artifacts": ["/app/output/edit_report.json", "/app/output/edit_report.md", "/app/output/change_log.jsonl"]
}
```

## 5. 诚实性红线

- 不得编造对照数据、耗时或返工轮次；无法测量就写 `na` 并说明。
- 不得把平台提供的白板或官方结果写成自己的对照产出。
- 增益结论必须能由 `verifiable_artifacts` 里的文件复算出来；只写结论不附产物，视为不可验证。
- 不得为了让指标好看而减少改动：`hard_error_count` 为 0 但 `edit_rate` 为 0 也说明没做事，两者要一起报。
