# drop-schema-bounds-in-load-contract-rag-docs

- **Started**: 2026-04-29 00:33:46 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

接续上一条 `2026-04-28_234002_load-strategy-drop-schema-bounds`：load_strategy.md 三处复述 schema bound 已清除。Step 7 全库扫描发现同类问题在 sibling 文档（同属 conventions.md `Cross-File Alignment` "Loading strategy" 行 + 邻近 contracts 文档）也存在。用户指示"扫一遍，然后改了 /go"。

判定准则（沿用上轮）：**这个数字改了之后，谁要跟着改？** 跟 schema 走 → 删；跟 loader 代码 / runtime 行为 / 决策历史走 → 留。

进一步与 `ai_context/conventions.md:82` 对齐：
> **Bounds only in schema.** All `maxLength` / `minLength` / `maxItems` / `required` live in `schemas/**.schema.json`; no duplicates anywhere else. Exact values → schema file. Index → `docs/architecture/schema_reference.md`.

## 结论与决策

**清掉**（schema 数值复述，违反 conventions.md L82）：

- `simulation/contracts/baseline_merge.md:59` — `character_arc … single string (≤ 200 chars)` — `character_arc` 是 `schemas/character/stage_snapshot.schema.json` L785 字段；此处复述 maxLength
- `simulation/retrieval/index_and_rag.md:45-48` — memory_timeline 字段 prose 描述含 `≤15 字`/`150–200 字`/`30–50 字`/`100–200 字`+`schema 硬门控`；全部是 `schemas/character/memory_timeline_entry.schema.json` 已有的 maxLength/minLength
- `simulation/retrieval/index_and_rag.md:222-225` — 同上字段在 SQL DDL 注释中重复

**保留**（不是 schema bound 复述）：

- `simulation/contracts/baseline_merge.md:37` — `each entry ~30–40 tokens` — 是 prompt 预算估算，非 schema 强制，描述 loader/runtime cost
- `simulation/retrieval/index_and_rag.md:168` — `~60-80 tokens/条` — 同上
- `simulation/retrieval/load_strategy.md:45` — `~30-40 tokens per entry; 22-29K tokens` — 同上
- `simulation/contracts/runtime_packets.md:106` — `character_anchor ≤300 字` — `character_anchor` 是 runtime-constructed Turn Packet 字段，无对应 schema；本 contract 文档自身就是 source of truth
- `simulation/prompt_templates/会话防稀释检查清单.md:23` — 同上 `≤300 字` 回声；prompt template 不在本次 load/contract/rag scope
- `docs/architecture/schema_reference.md:146 / 362` — schema_reference 本就是 conventions L82 指定的 "Index → schema_reference.md"，允许枚举数值
- `docs/requirements.md:1863` — `quote ≤200 字` 是 requirements 自身定义的程序化引文规格，非 schema 复制
- `docs/requirements.md:2868` / `docs/todo_list.md:131/142/174` — 业务规格 / 文档自身规则，非 schema 复述
- `ai_context/decisions.md:99/101/102` (#31 / #33 / #34) — 决策记录，bound 是决策内容本身的一部分；删除会丢失 decision 的参数化语义。决策历史与 `Bounds only in schema` 是不同轴向，本次明确不动

## 计划动作清单

- file: `simulation/contracts/baseline_merge.md`
  - L59 `single string (≤ 200 chars). Complements stage_delta.` → 改为指针："single string (length capped by `stage_snapshot.schema.json`). Complements stage_delta."
- file: `simulation/retrieval/index_and_rag.md`
  - L42-49（memory_timeline prose）：删除字段后跟的 `≤15 字短语, required` / `150–200 字客观描述, schema 硬门控` / `30–50 字独立撰写的精简摘要, schema 硬门控` / `100–200 字` 等具体数值与"schema 硬门控"措辞；保留字段名与角色定位（"独立撰写的精简摘要；是 memory_digest 的 1:1 来源" 等）；末尾追加"详见 `schemas/character/memory_timeline_entry.schema.json`"指针（已有）
  - L222-225（SQL DDL 注释）：删除 `≤15 字` / `150–200 chars` / `30–50 chars` 数字；保留中文短描述（"故事内时间" / "事件地点" / "客观描述" / "精简摘要（memory_digest 的来源）"）

## 验证标准

- [ ] `grep -nE '(50.{1,3}80|50.{1,3}100|30.{1,3}50|150.{1,3}200|100.{1,3}200|≤\s*200\s*chars|≤\s*15\s*字|hard schema gate|schema 硬门控)' simulation/contracts/baseline_merge.md simulation/retrieval/index_and_rag.md` 返回空
- [ ] 上述文件内 token 估算 / loader 行为参数 / 字段 role 描述均原样保留
- [ ] schema 自身、decisions.md、schema_reference.md、requirements.md、prompt_templates/、todo_list.md 不被本次改动触及

## 执行偏差

无

<!-- POST 阶段填写 -->

## 已落地变更

- `simulation/contracts/baseline_merge.md` L58-60
  - `single string (≤ 200 chars). Complements stage_delta.` → `single string (length capped by stage_snapshot.schema.json). Complements stage_delta.`
- `simulation/retrieval/index_and_rag.md` L42-49（memory_timeline prose）
  - 字段后缀去除：`≤15 字短语` → `短语锚点`；`150–200 字客观描述, schema 硬门控` → `客观描述`；`30–50 字独立撰写的精简摘要, schema 硬门控` → `独立撰写的精简摘要`；`100–200 字` → 删除（subjective_experience 仅留字段名）
  - 把原本独立成行的 "详见 …schema.json" 整合进同一段尾："字段长度上限以 `schemas/character/memory_timeline_entry.schema.json` 为准"
- `simulation/retrieval/index_and_rag.md` L220-223（SQL DDL 注释）
  - `≤15 字` → `短语锚点`；`150–200 chars 客观描述` → `客观描述（长度上限见 memory_timeline_entry.schema.json）`；`30–50 chars 精简摘要（memory_digest 的来源）` → `精简摘要（memory_digest 的来源；长度上限见 schema）`

## 与计划的差异

无

## 验证结果

- [x] `grep -nE '(50.{1,3}80|50.{1,3}100|30.{1,3}50|150.{1,3}200|100.{1,3}200|≤\s*200\s*chars|≤\s*15\s*字|hard schema gate|schema 硬门控)' simulation/contracts/baseline_merge.md simulation/retrieval/index_and_rag.md` 返回空
- [x] token 估算 / loader 行为参数 / 字段角色描述均原样保留（baseline_merge.md L37 `~30–40 tokens`、index_and_rag.md L168 `~60-80 tokens/条`、L226 `5 levels: trivial/...` 等都原样）
- [x] schema 自身、`ai_context/decisions.md`、`docs/architecture/schema_reference.md`、`docs/requirements.md`、`simulation/prompt_templates/`、`docs/todo_list.md` 未触及

## Completed

- **Status**: DONE
- **Finished**: 2026-04-29 00:36:16 EDT
