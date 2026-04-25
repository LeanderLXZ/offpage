# 2026-04-21 19:14 EDT — coverage_shortage accept_with_notes

## 起因

2026-04-21 Phase 3 stage 01 提取在 repair agent 里跑了 18m24s、16 次尝试
后以 `T3_CORRUPTED` FAIL，根因是 `min_examples` 结构规则判定
`dialogue_examples` / `action_examples` 条数不足
`importance_min_examples`（主角≥5、重要配角≥3、其他≥1），而原文本身
并不存在足够素材。T0 无法凭空造例、T1 无原文易胡编、T2 三次 source_patch
也找不出原文没写的台词、T3 整文件重写更不会让原文变长——最终 T3 还破坏
了结构校验，触发硬停。

这类 issue 既不是提取错误也不是源文本 bug，而是**覆盖度天然有限**。
需要一条不同于"author contradiction"的 accept_with_notes 通道。

## 改动概要

### 规则

`min_examples` L2 结构 issue：
- `severity=error → warning`，`context.coverage_shortage=True`
- 路由 `START_TIER=T2, MAX_TIER=T2`（跳过 T0 / T1 / T3）
- T2 只给一次机会，失败即走 0-token triage 构造 SourceNote
- `discrepancy_type="coverage_shortage"`，与原有 L3 source_inherent 共用
  `accept_cap_per_file`（3→5）
- Runtime 不消费 `extraction_notes/`（仅审计）；Phase 3.5
  consistency_checker 遇到 min_examples 不足但有匹配 json_path 的
  coverage_shortage SourceNote 时视为已达标、不报 warning

### 改动的文件

**代码**：
- `automation/repair_agent/protocol.py`
  - `RepairConfig.accept_cap_per_file`: 3 → 5
  - `DISCREPANCY_TYPES`: 追加 `"coverage_shortage"`
  - `SourceNote.issue_category` docstring 放开到 `semantic` / `structural`
  - 新增 `is_coverage_shortage(issue)` helper + `COVERAGE_SHORTAGE_START_TIER=2` / `COVERAGE_SHORTAGE_MAX_TIER=2` 常量
- `automation/repair_agent/checkers/structural.py`
  - `min_examples` issue `severity=warning`，`context.coverage_shortage=True`
- `automation/repair_agent/coordinator.py`
  - `_filter_blocking`：errors + `is_coverage_shortage` warnings 一起进入 blocking
  - `_group_by_start_tier`：coverage_shortage → tier 2
  - `_issue_max_tier`：coverage_shortage 上限 T2
  - `_run_fixer_with_escalation`：T2 attempt>0 时 prune coverage_shortage；T2 后调用 `_run_coverage_shortage_triage`
  - 新增 `_run_coverage_shortage_triage`：0-token 程序化构造并持久化 SourceNote
- `automation/repair_agent/triage.py`
  - 新增 `Triager.build_coverage_shortage_verdict`：从 stage 首章取一段子串作为 quote，自带 `evidence_verified=True`
  - `build_source_note` 放开 category 校验：`semantic` 或 `structural + coverage_shortage`
- `automation/persona_extraction/config.py`
  - `RepairAgentConfig.triage_accept_cap_per_file`: 3 → 5
- `automation/persona_extraction/consistency_checker.py`
  - 新增 `_extraction_notes_path` / `_load_coverage_shortage_paths`
  - `_check_target_map_counts`：匹配 json_path 的 coverage_shortage note 抑制 warning

**Schema**：
- `schemas/shared/source_note.schema.json`
  - `issue_category` enum: `["semantic"]` → `["semantic", "structural"]`
  - `discrepancy_type` enum: 追加 `"coverage_shortage"`
  - title/description 更新

**配置**：
- `automation/config.toml`
  - `triage_accept_cap_per_file = 3 → 5`，注释说明共用机制

**文档**：
- `docs/requirements.md`：§11.4.4 增加 coverage_shortage 特殊路由说明；
  §11.4.5 修复循环加一步 coverage_shortage triage；§11.4.6 cap
  3→5、说明共用；§11.4.7 完全重写，拆成两条 path 并补全 L2 程序化流程
- `ai_context/requirements.md`：triage 段改为两条 path
- `ai_context/decisions.md`：§25a 拆成 Path A / Path B 并加 runtime 约定
- `ai_context/architecture.md`：repair agent 段更新
- `ai_context/current_status.md`：triage 行更新
- `docs/architecture/extraction_workflow.md`：源文件问题 triage 段拆成两条 path
- `docs/architecture/schema_reference.md`：source_note 条目更新
- `automation/README.md`：triage 段拆成 Path A / Path B + runtime 约定

## 预期影响

- 类似 2026-04-20 这种单 stage 18m T3_CORRUPTED 会降为 ~3-5 min PASS +
  N 条 SourceNote（N ≤ 5）
- Phase 3.5 不会再对有 coverage_shortage note 的字段重复报 warning
- Runtime 行为完全不变（不加载 extraction_notes/）
- `accept_cap_per_file` 从 3 升到 5，为两条 path 共用留空间；超过上限
  的 coverage_shortage issue 仍 blocking、stage FAIL

## 校验

- 4 个 import 检查通过（protocol / triage / coordinator / structural /
  consistency_checker / config）
- schema syntactic check + 3 份样本 note（semantic / coverage_shortage /
  应该拒绝的 json_syntax）通过
- 结构校验：产出 issue 正确为 severity=warning + coverage_shortage flag
- `Triager.build_coverage_shortage_verdict` + `build_source_note` 端到端
  产生 schema-valid note，`future_fixer_hint` 含 resolvable_when /
  manual_action / importance / current / required
- `_filter_blocking` / `_group_by_start_tier` / `_issue_max_tier` 行为符合预期
- 现有 `_smoke_triage`（5 个场景 A-E）与 `_smoke_l3_gate` 全通过，未回退

## 备注

- 用户在对齐方案时取消了 T2 自报反向 anchor（复杂度）、采用一次 PR
  全上；runtime 不感知 SourceNote（仅审计）
- coverage_shortage 上限与 source_inherent 共享 cap，意图：原文真不够的
  情况下接受条数不应被"作者 bug"额度挤掉
