# 字段字典、定位格式与修改条目规范

## 1. `location` 格式

| 形式 | 用法 | 示例 |
|---|---|---|
| `p<段>/s<句>` | 纯文本/无章节结构时首选，段与句都从 1 起 | `p3/s2` |
| `sec:<章节>/p<段>/s<句>` | 有明确章节结构 | `sec:Methods/p2/s1` |
| `abs` / `title` / `caption<号>` | 摘要、标题、图注等特殊块 | `caption2` |
| `line:<起>-<止>` | LaTeX 或代码型材料 | `line:41-58` |

规则：`location` 必须能定位到**原稿里的具体句子**，不能写"摘要附近""第二节"。脚本产出的 `p<段>/s<句>` 可直接复用。

## 2. `changes` 条目规范

每条记录必须回答四个问题，缺一条就不可核验：

```json
{
  "original": "The diffusion coefficient may increased by 3.5 times",
  "revised": "The diffusion coefficient may increase by 3.5 times",
  "type": "语法",
  "reason": "情态动词 may 后须接动词原形，increased → increase",
  "location": "p3/s1"
}
```

| 字段 | 必填 | 规则 |
|---|---|---|
| `original` | 是 | 从**原稿逐字复制**的片段，必须能在原稿里搜到；脚本会核 `unmatched` |
| `revised` | 是 | 改稿中的对应片段，必须能在改稿里搜到；脚本会核 `without_effect` |
| `type` | 是 | 取值见下表，不要写"优化""润色"这类无法判断的标签 |
| `reason` | 是 | 说清"为什么这样改"，能让第三方判断该不该改；不要写"更自然" |
| `location` | 是 | 见第 1 节 |

### `type` 建议取值

| 值 | 含义 | 典型判据 |
|---|---|---|
| `语法` | 主谓一致、时态、语态、单复数、冠词、介词、悬垂修饰 | 违反语法规则 |
| `标点` | 逗号/分号/破折号、长句切分、中英标点混用 | 违反标点规范 |
| `术语` | 统一为术语表 canonical 写法 | 与 `glossary` 不一致 |
| `语域` | 口语化、宣传化、绝对化、人称误用 | 与目标文体不符 |
| `语义` | 限定强度、否定范围、因果/相关、量词 | 改动会影响主张强度 |
| `格式` | 缩写首次出现、上下标、引用与图表标记 | 格式规范 |

**红线**：`语义` 类改动最敏感。凡是会改变限定强度或否定范围的改动，`reason` 必须写清依据，否则应保留原表述。

## 3. `verification` 各项计数口径

| 键 | 口径 | 数据来源 |
|---|---|---|
| `semantic_preservation` | 限定漂移 + 强度词丢失 + 否定变化 + 整句增删，全部应为 0 | `edit_report.faithfulness` |
| `data_units_citations` | 数字/单位/引用/图表指向四类差异，全部应为 0 | `edit_report.faithfulness` |
| `minimal_edit` | 改动句/对齐句比值 + 疑似整句重写数 | `edit_report.sentences`、`over_edit` |
| `traceability` | 未记录改动 / 记录对不上原文 / 记录与改文不符 / 字段不全 | `edit_report.changes_coverage` |
| `register_and_errors` | 口语+宣传+绝对化计数、硬错误计数 | `edit_report.register`、`hard_errors` |
| `glossary_consistent` | 术语未落实数 + 写法不一致数 | `edit_report.terms` |
| `causality_preserved` | 因果是否被改成相关，抽查通过数/抽查数 | **人工**（脚本测不出） |
| `no_new_facts` | 改文中出现原稿没有的事实/数字/引用条数 | `sentence_added` + 人工 |

## 4. `status` 判定

| 值 | 条件 |
|---|---|
| `success` | 任务要求范围内全部段落处理完，语义守恒与数据保真计数为 0 或有书面理由，`changes` 覆盖全部改动 |
| `partial` | 部分段落未处理、或材料残缺、或存在需作者决定的语义歧义；必须写出范围与人工接管位置 |
| `unable` | 原稿不可读（编码损坏、空文件、纯图片），未产出任何改稿 |
| `refused` | 输入不属于润色范围（要求代写新内容、纯内容问答、要求改变作者结论） |

## 5. 术语表 `glossary.json` 规范

```json
{"terms": [
  {"term": "XRD", "canonical": "XRD", "variants": ["Xrd"],
   "positions": ["p1/s2", "p4/s1"], "decision_basis": "领域惯例全大写；首次出现给中文全称"},
  {"term": "e-mail", "canonical": "email", "variants": ["e-mail"],
   "positions": ["p2/s3"], "decision_basis": "目标期刊要求无连字符"}
]}
```

- `canonical` 必须与改稿语言一致；术语表写了中文译名而改稿是英文时，脚本会放入 `terms.skipped` 并说明，不会误报"未落实"。
- `variants` 填**不该再出现的写法**，脚本发现即报 `inconsistent`。
- `decision_basis` 空着等于没定名依据，评审会视为术语表未被真正执行。
