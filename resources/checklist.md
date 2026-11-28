# 润色自检清单（带计数口径）

先核对"运行契约"，再逐项核对内容。**能用脚本算的用脚本算，算不出的才人工填**；每项结论写进 `result.json` 的 `verification`，且必须带计数或抽查片段，不能只写"通过"。发现问题回到 SKILL.md 第 3 步修正并记入 `change_log`。

| # | 项 | 口径 | 数据来源 |
|---|---|---|---|
| 1 | `semantic_preservation` | 限定漂移 + 强度词丢失 + 否定变化 + 整句增删，全部应为 0 | `edit_report.faithfulness` |
| 2 | `data_units_citations` | 数字/单位/引用/图表指向四类差异之和，应为 0 | `edit_report.faithfulness` |
| 3 | `minimal_edit` | 改动句/对齐句 + 疑似整句重写数 + 改动偏大数 | `edit_report.sentences`、`over_edit`、`heavy_edit` |
| 4 | `traceability` | 未记录改动 + 记录对不上原文 + 记录与改文不符 + 字段不全 | `edit_report.changes_coverage` |
| 5 | `register_and_errors` | 口语+宣传+绝对化 + 硬错误 | `edit_report.register`、`hard_errors` |
| 6 | `glossary_consistent` | 术语未落实 + 写法不一致（跨语言跳过的不算） | `edit_report.terms` |
| 7 | `causality_preserved` | 因果/相关、指代抽查通过数/抽查数 | **人工**（脚本测不出） |
| 8 | `no_new_facts` | 新增句 + 人工核出的事实/数字/引用增补数，应为 0 | `sentence_added` + 人工 |

## 运行契约（先做）
- [ ] 已读取 `/input/case.json` 与 `/input/task.md` 并打开全部材料文件，未凭标签猜内容
- [ ] `case_id` 来自输入；`output_contract` 的每个字段都出现在 `result.json` 中且名称一致
- [ ] 已在 `/app/work` 保存中间稿，并写入 `/app/output/result.json`、`polished_text.md`、`changes.json`
- [ ] 已跑 `edit_lint.py terms` 与 `lint`，两份报告落在 `/app/output`
- [ ] 结果与稿件为真实运行结果，未包含预制答案、正式案例答案或虚构成绩

## 改得对（硬错误真改掉）
- [ ] `hard_error_count` 已清零（双空格、空格前标点、重复词、主谓一致、冠词 a/an、句首小写、中英标点混用）
- [ ] 主谓一致、时态、语态、冠词、介词、单复数错误已修正
- [ ] 悬垂修饰、标点、长句切分已处理
- [ ] 是"改错"而非"换一种说法掩盖错误"（对照 `heavy_edit` 清单逐条自问：这处不改会不会错？）
- [ ] `changes` 中每一处 `revised` 都能在 `polished_text` 中逐字找到（`without_effect_count` 为 0）

## 说得像（术语与语域）
- [ ] 术语表每条 canonical 写法在全文完全一致（`terms.inconsistent_count` 为 0）
- [ ] `terms_report.json` 的 `case_sensitive_drift` 逐条处理（`XRD`/`Xrd`、`e-mail`/`email`）
- [ ] 缩写首次出现给全称（对照 `abbrev_first_use` 中 `has_definition_nearby: false` 的条目）
- [ ] 无引言/方法之间的术语漂移
- [ ] 语域贴合目标文体（期刊/学位/基金/审稿回复/摘要）；`register` 三类已清零或说明
- [ ] 无口语化、宣传化、绝对化表述与人称误用
- [ ] 无中式英语、直译腔、冗余名词化、逻辑连接词滥用（人工）

## 没改坏（语义守恒，逐项对照不变量清单）
- [ ] `hedge_upgraded_count` 为 0：没有把 may/suggests 改成 is/demonstrates
- [ ] `hedge_removed_count` 为 0，或每处都在 `uncertainties` 写明依据
- [ ] `hedge_added_count` 为 0：没有给作者结论添加原文没有的限定
- [ ] `intensity_dropped_count` 为 0：significantly/only/显著/仅 一个都没吞
- [ ] `negation_changed_count` 为 0，或逐处核对后说明否定范围未变
- [ ] `sentence_dropped_count` 与 `sentence_added_count` 为 0
- [ ] 数字、单位、有效数字四类差异为 0（`number_changed` / `unit_changed`）
- [ ] 引用编号、图表指向原样保留（`citation_changed` / `figref_changed`）
- [ ] 因果与相关性未被互换（人工）；条件句、量词保持原样（人工）
- [ ] 未新增材料外的任何事实、数字或引用
- [ ] 上述每一项在 `verification` 中都有 `result` 和具体计数/片段

## 讲得清（可核验）
- [ ] `changes_coverage.uncovered_count` 为 0：每处改动都有条目
- [ ] `unmatched_count` 与 `without_effect_count` 为 0：记录与原文、改文都对得上
- [ ] `incomplete_count` 为 0：每条都有 type 与 reason
- [ ] `polished_text` 段落数与原文一致，`scope` 覆盖任务要求的全部段落
- [ ] `edit_report` 字段数值与 `edit_report.json` 一致（不是另算一套）
- [ ] 需人工确认、材料冲突、无法判断处写入 `uncertainties`
- [ ] `status` 与实际完成情况一致；partial 写明未完成范围与人工接管点
- [ ] `change_log` 记录了自检发现的问题与回修；`result.json` 可被 JSON 解析
