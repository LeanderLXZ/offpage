# Codex 二轮交叉审查修复（Codex Cross-Review Round 2 Fixes）

**日期**：2026-04-16
**范围**：schema 条件校验、users/_template 漂移、commit gate 加固、
`--resume` baseline 验证、文档一致性

## 起因

Codex 对 persona-engine 做了第二轮交叉审查，报告了 8 条 finding（High /
Medium / Low），外加 1 条残留风险。核心关切是"校验/规格/模板三层之间
出现了不一致"，具体症状：

- JSON Schema Draft 2020-12 的 `if: { properties: {X: {const: Y}} }`
  在 `X` 缺失时**空真（vacuously true）**，导致 `then` 分支里的
  `required` 被错误触发 —— 典型反例：
  `counterpart_mode = "user_self"` 也会被要求填写
  `counterpart_stage_id`。
- `users/_template/` 里的字段名、枚举值、必填项与现行 schema 脱节
  （例如 `counterpart_mode: "custom"`、`counterpart_custom_label`、
  `origin`、`sessions`、`notes` 等）。
- 提交门控在 `stage_catalog.json` / `memory_digest.jsonl` 缺失时
  静默跳过；`world_event_digest.jsonl` 完全没有进入门控检查。
- Phase 2.5 在 `--resume` 路径下，只要三个 baseline 文件存在就直接
  标记 `phase_2_5 = done`，跳过 `validate_baseline()`，schema 损坏或
  字段缺失会悄悄滑进 Phase 3。
- 文档内互相打架：`data_model.md` 把 digest 写成 `.json`，
  `users/README.md` 和 schema 写成 `.jsonl`；`ingestion_status` 枚举
  在 `data_model.md` 是三态（`pending / active / complete`），但
  `schemas/work_manifest.schema.json` 与 `docs/requirements.md` 已经
  是六态；`automation/README.md` 的 Phase 4 命令行示例前后不一致。

## 变更

### 1. `schemas/*.schema.json` — 修复 if/properties/const 空真 bug

对以下四个 schema 做了机械化扫描，在每一个
`if: { properties: { X: { const: Y } } }` 块上补 `required: [X]`，
避免字段缺失时 `then` 分支空真触发：

- `schemas/role_binding.schema.json`（3 处）
- `schemas/context_manifest.schema.json`（3 处）
- `schemas/session_manifest.schema.json`（3 处）
- `schemas/runtime_session_request.schema.json`（11 处）

共 20 处修正。

**回归测试**：手写 8 组用例覆盖
`user_self` / `user_persona` / `canon_character` / `bootstrap_user`
四种模式 × 字段齐全 / 字段缺失两种情况，8/8 通过
（该通过的通过，该失败的失败）。

### 2. `automation/persona_extraction/review_lanes.py` — 门控硬失败 + world_event_digest 纳管

- 把"文件不存在 → 静默跳过"改成硬失败并发 `GateIssue`，覆盖：
  - `world/stage_catalog.json`
  - `world/world_event_digest.jsonl`（新增）
  - `characters/{cid}/canon/stage_catalog.json`
  - `characters/{cid}/canon/memory_digest.jsonl`
- 新增 helper `_validate_world_event_digest_has_stage()`，镜像
  `_validate_digest_has_stage()` 的实现，但改用 `event_id` 与
  `E-S{stage:03d}-` 前缀做 stage 对应校验。
- 把 `world_event_digest_missing` 加入 `POST_PROCESSING_RECOVERABLE`
  frozenset —— 该类失败走"免费 PP 重跑"恢复路径，与
  `catalog_missing` / `digest_missing` 同策略，不升级为整 stage 回滚。

### 3. `automation/persona_extraction/orchestrator.py` — `--resume` 强制 baseline 验证

Phase 2.5 的 resume 路径之前长这样：

```python
if foundation.exists() and identities_ok and fixed_rel.exists():
    pipeline.mark_done("phase_2_5")
    # 直接跳过，不验证文件内容
```

改成：

```python
if foundation.exists() and identities_ok and fixed_rel.exists():
    baseline_report = validate_baseline(...)
    if not baseline_report.passed:
        # 重跑 Phase 2.5 + 重新 commit baseline
        self.run_baseline_production(pipeline.target_characters)
        commit_stage(self.project_root, "baseline", message=...)
    else:
        pipeline.mark_done("phase_2_5")
```

即：文件存在 ≠ 内容合法。resume 时必须强制过一遍 `validate_baseline()`，
失败即触发 Phase 2.5 自愈。

### 4. `users/_template/**` — 对齐 schema

按现行 schema 重写 6 个模板文件：

- `users/_template/profile.json` —
  删除非 schema 字段 `language`。
- `users/_template/role_binding.json` —
  `counterpart_mode: "custom" → "user_self"`；
  `counterpart_custom_label → counterpart_label`；
  `status: "draft" → "active"`。
- `users/_template/long_term_profile.json` —
  改用 schema 名（`persona_shift_history` /
  `event_history` / `memory_history`）；补上
  `character_drift_history`；删除 `notes`。
- `users/_template/relationship_core/manifest.json` —
  单数 `relationship_label`；
  `personalized_voice_shift` / `personalized_behavior_shift`
  改为 `{}`；补上
  `current_relation_summary` / `pinned_memories` /
  `event_refs` / `profile_shift_refs` / `mutual_agreements`；
  删除 `notes`。
- `users/_template/contexts/{context_id}/manifest.json` —
  `origin → origin_type`；
  `sessions → session_ids`；补上
  `counterpart_mode` / `merge_policy` / `writeback_policy`；
  删除 `notes`。
- `users/_template/contexts/{context_id}/sessions/{session_id}/manifest.json` —
  `terminal: "" → "agent"`；补上 `status: "active"`；
  删除 null 字段和 `notes`。

**回归测试**：替换占位符（`{user_id}` → `user_template` 等）后，
6 个模板全部通过各自 schema 的 `Draft202012Validator.iter_errors()`。

### 5. 文档一致性

- `docs/architecture/data_model.md`：`ingestion_status` 三态 → 六态
  （`planned` / `raw_imported` / `normalized` / `chunked` /
  `indexed` / `active`），明确以 `schemas/work_manifest.schema.json`
  与 `docs/requirements.md §8.4` 为权威。
- `automation/README.md`：Phase 4 示例命令从
  `python -m persona_extraction "<work_id>" -r ..`
  统一改成
  `python -m automation.persona_extraction "<work_id>" --start-phase 4`，
  与同文件 L71-92 的 repo-root 调用风格一致。
- `ai_context/current_status.md`：说明 baseline 出口验证在 fresh 与
  `--resume` 两条路径都会跑；gate 对缺失 catalog / digest 发硬错。
- `ai_context/decisions.md` §25：补充 gate 对缺失文件硬失败 +
  `world_event_digest` 走免费 PP 重跑的路由语义。

### 6. `docs/requirements.md`

- §8.4 `ingestion_status` 从三态扩成六态，加入每态定义块，并标注
  schema 为权威真源。
- §9 门控检查项 #5 要求 `world_event_digest.jsonl` 存在且含
  `E-S{stage:03d}-` 前缀。
- §11.4b 门控失败映射表补齐 `world_event_digest → world` 路由行。
- §11.7 "Baseline 恢复"加关键约束：`validate_baseline()` 必须在
  `--resume` 下也运行，不能因文件存在而跳过。

## 风险与边界

- **schema if/properties/const 修法是否过窄**：仅给
  `properties.X.const` 这一种 if 模式补 `required: [X]`。若将来新
  加 `properties.X.enum` / `pattern` 等条件分支，需同样处理；否则
  会重演空真陷阱。短期不加通用 linter，靠 review 习惯守住。
- **`world_event_digest` 门控**：新增硬失败会让现存跑到一半、但
  尚未生成 `world_event_digest.jsonl` 的 stage 进不了 commit；这是
  有意的（它们本就应被 PP 重跑捕获）。恢复策略走免费 PP 重跑，无额
  外 LLM 成本。
- **`--resume` 下 Phase 2.5 重跑的 commit 语义**：重跑会新增一条
  `Phase 2.5 baseline (validation-triggered recovery)` commit，而非
  `--amend` 既有 baseline commit。原因：保持 commit graph 线性可
  追溯；缺点是仓库里会出现两条 baseline commit，review 时需留意。
- **`users/_template/` 与 schema 的长期同步**：目前靠 CI-less 的手动
  校验。建议后续加 `tests/test_templates.py`（用
  `jsonschema.Draft202012Validator` 遍历 `users/_template/`），
  避免再次漂移。本次未实装，列为 follow-up。

## Follow-up（未在本次 commit 落地）

1. 给 `users/_template/**` 加 schema 回归测试（pytest 一行 per
   模板），挂在 `automation/tests/` 下。
2. 给 schema 仓库做一次统一 lint：扫出任何
   `if: { properties: { X: {...} } }` 没有配套 `required: [X]` 的
   写法，防止未来再踩同一个坑。
3. 审查 `runtime_session_request.schema.json` 的 11 处 if/then，
   评估是否能合并进更少的 `oneOf` / `discriminator`，降低维护面。
