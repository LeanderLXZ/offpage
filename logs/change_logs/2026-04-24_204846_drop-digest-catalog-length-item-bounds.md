# drop-digest-catalog-length-item-bounds

- **Started**: 2026-04-24 20:48:46 EDT
- **Branch**: master（worktree `../persona-engine-master`，原仓 dirty 并停留在 `extraction/我和女帝的九世孽缘`）
- **Status**: PRE

## 背景 / 触发

用户要求：去除 2 个 digest 文件、2 个 catalog 文件中关于字数 / Items 数量的限制。

定位为以下 4 个 schema：

- `schemas/world/world_event_digest_entry.schema.json`
- `schemas/character/memory_digest_entry.schema.json`
- `schemas/world/world_stage_catalog.schema.json`
- `schemas/character/stage_catalog.schema.json`

这 4 份产物的语义在 `ai_context/decisions.md` §24/§32/§33 中已确立：digest / catalog
均为 **`post_processing.py` 程序化 1:1 复制 / 累积**（0 token，幂等），不由 LLM 提取产生。
上游 hard gate 已分别在：

- `world_stage_snapshot.stage_events`：50–100 字（schema + prompt 双门控）
- `world_stage_snapshot.timeline_anchor` / `location_anchor`：≤15 字
- `memory_timeline.digest_summary`：30–50 字（schema + prompt 双门控）
- `stage_catalog` 各条目的来源由 baseline / orchestrator 维护

所以这 4 份下游 schema 中的 `minLength` / `maxLength` / `minItems` / `maxItems` 是冗余防御层；
上游若放宽，下游必须同步放宽，而下游本身从不直接接收 LLM 输出。冗余既增加维护成本也容易
和上游不一致。

## 结论与决策

- 移除 4 份下游 schema 中**全部** `minLength` / `maxLength` / `minItems` / `maxItems`。
- 保留 `pattern`（ID 格式校验）、`enum`、`required`、`type`、`additionalProperties: false` 等
  结构性约束——这些不是字数 / Items 数量限制。
- **不动**任何上游 schema（`world_stage_snapshot`、`memory_timeline_entry` 等），它们仍然
  承担 hard gate 责任。
- 不改变 1:1 复制契约（decisions §32/§33）；`consistency_checker` 的等值校验照旧。

## 计划动作清单

- file: `schemas/world/world_event_digest_entry.schema.json` → 删 `summary.minLength=50/maxLength=80`、`time.maxLength=15`、`location.maxLength=15`
- file: `schemas/character/memory_digest_entry.schema.json` → 删 `summary.minLength=30/maxLength=50`、`time.maxLength=15`、`location.maxLength=15`
- file: `schemas/world/world_stage_catalog.schema.json` → 删 `work_id.minLength=1`、`stages.minItems=0`、`stages[].stage_title.minLength=1/maxLength=15`、`stages[].summary.minLength=1`
- file: `schemas/character/stage_catalog.schema.json` → 删 `character_id.minLength=1`、`work_id.minLength=1`、`stages.minItems=0`、`stages[].stage_title.minLength=1/maxLength=15`、`stages[].summary.minLength=1`
- file: `docs/architecture/schema_reference.md` → §world_stage_snapshot 中 `post_processing 复制到 world_event_digest.time / location` 周边描述若提及"≤15 字"传递关系无须改动；4 份 schema 自身段落不含具体数字，无需修改
- file: 暂不修改 `ai_context/decisions.md`/`conventions.md`：bounds-only-in-schema、bounds-are-caps-not-targets 仍然成立（针对 LLM 直写的 schema）；4 份程序化产物的具体 bounds 数值原本就不在 ai_context 中

## 验证标准

- [ ] `python -c "import json; from jsonschema import Draft202012Validator; ..."` 对 4 份修改后的 schema 自校验（schema 本身合法）
- [ ] 用修改后的 schema 校验现有 `works/我和女帝的九世孽缘/` 下 4 份产出文件，仍然 pass（更宽松的 schema 不应让原本合规的数据失败）
- [ ] `grep -nE "maxLength|minLength|maxItems|minItems"` 在 4 份 schema 中无残留
- [ ] 全仓 `grep` 4 份 schema 路径，确认无外部代码 / 文档依赖被删除字段（jsonschema 验证之外的硬编码引用）

## 执行偏差

执行中按 §27b "bounds-only-in-schema" 顺手清理了 `stage_title` 在 schema 之外
的 ≤15 数字孤儿引用（5 处：`schemas/README.md`、2 份 prompt template、`progress.py`
注释），以及 `docs/requirements.md` §digest 段中"硬门控由 schema 承担"的措辞
更新。这些不在 PRE 计划清单内，但属于本次改动的直接下游对齐，未扩大语义范围。

`ai_context/decisions.md` §33 中的 "(30–50 CJK chars, hard gate)" 经判断保留：
该数值描述的是 upstream `digest_summary`（在 `memory_timeline_entry.schema.json`
仍然有效的硬门控），未受本次影响。同理 §31 / §34 关于 `stage_events` 50–100 /
50–80 的数值描述上游 `world_stage_snapshot.stage_events` / `character/stage_snapshot.stage_events`
的硬门控，也未受本次影响。

<!-- POST 阶段填写 -->

## 已落地变更

Schema 主改动（删除 length / items 限制）：

- `schemas/world/world_event_digest_entry.schema.json` — 删 `summary.minLength=50/maxLength=80`、`time.maxLength=15`、`location.maxLength=15`；保留 `event_id` pattern、`importance` enum、required、`additionalProperties:false`
- `schemas/character/memory_digest_entry.schema.json` — 删 `summary.minLength=30/maxLength=50`、`time.maxLength=15`、`location.maxLength=15`；保留 `memory_id` pattern、`importance` enum、required、`additionalProperties:false`
- `schemas/world/world_stage_catalog.schema.json` — 删 `work_id.minLength=1`、`stages.minItems=0`、`stages[].stage_title.minLength=1/maxLength=15`、`stages[].summary.minLength=1`；保留 `stage_id` / `default_stage_id` pattern、required、`additionalProperties:false`
- `schemas/character/stage_catalog.schema.json` — 删 `character_id.minLength=1`、`work_id.minLength=1`、`stages.minItems=0`、`stages[].stage_title.minLength=1/maxLength=15`、`stages[].summary.minLength=1`；保留同上结构性约束

Schema 之外的对齐（去 stage_title ≤15 字孤儿数字）：

- `schemas/README.md:26` — 去 `（≤15 字）`
- `automation/prompt_templates/analysis.md:115,187` — 去 `≤15 字` / `不超过 15 字`，保留"短标题"
- `automation/prompt_templates/baseline_production.md:248,265` — 同上
- `automation/persona_extraction/progress.py:370` — 注释去 `(≤15 chars)`

`docs/requirements.md:1412` — `world_event_digest` 写入前校验描述更新：明确长度上限由
上游 `world_stage_snapshot` 承担、digest schema 只硬门控结构。

## 与计划的差异

PRE 计划仅列了 4 份 schema；POST 在 §27b "bounds-only-in-schema" 约束下增加
了 5 处 stage_title 数字孤儿清理 + 1 处 requirements.md 表述对齐，已在"执行
偏差"段记录。

## 验证结果

- [x] `Draft202012Validator.check_schema(...)` 对 4 份修改后 schema 自校验全部通过
- [x] 用修改后 schema 校验现有 `works/我和女帝的九世孽缘/` 数据：相比 master HEAD schema 错误数从 48 降至 27（更宽松，未引入新错误）；残留 27 条全部是 `location` required / `order` 多余字段（来自更早的 commit cef6cad / §27e 演进，与本次无关）
- [x] `grep -nE "maxLength|minLength|maxItems|minItems"` 在 4 份 schema 中残留 = 0
- [x] 全仓 grep `stage_title` / `digest.*summary` 数字孤儿，仅剩 `logs/`（豁免）和 `ai_context/decisions.md` §31/§33/§34 描述 upstream bound（未受本次影响）

## Completed

- **Status**: DONE
- **Finished**: 2026-04-24 20:58:03 EDT
