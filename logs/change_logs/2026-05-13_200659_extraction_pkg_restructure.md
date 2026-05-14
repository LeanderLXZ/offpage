# extraction_pkg_restructure

- **Started**: 2026-05-13 20:06:59 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

会话讨论：用户提出两个观感问题——(a) `automation/` 这个名字泛得没意义，应该叫 `extraction` 类；(b) `persona_extraction/` 一层 24 个 .py 平铺，找文件认知负担大。三轮 /plan 后拍板：

1. 顶层 `automation/` → `extraction/`
2. 内部 Plan A 全套 + 进一步切分：core/ (基础件) + lifecycle/ (横向状态机) + phases/ (相位特化) + tests/ (smoke 拎出) + prompts/ (templates 内移)
3. 新增 `validation/` 顶层目录作为 framework 预留位（gates/ + shared/），为将来 T-PHASE2-REPAIR-AGENT 全阶段 validation 接入 repair 框架先把物理位置摆到位
4. `repair_agent/` → `repair/`
5. `validator.py` 切分：Phase 2 gate 留 `validation/gates/`，3 个共享原语（importance_for_target / importance_min_examples / validate_with_length_tolerance / relaxed_schema_for_length / _is_length_bound_error）拎到 `validation/shared/`
6. `consistency_checker.py` 整体移到 `validation/gates/phase3_5_consistency.py`

todo 已登记：`T-EXTRACTION-PKG-RESTRUCTURE`（docs/todo_list.md Next 段）。

## 结论与决策

**最终目录树**：

```
extraction/                              ← 改名自 automation/
├── pyproject.toml / config.toml / README.md
├── persona_extraction/
│   ├── __init__.py / __main__.py / cli.py
│   ├── orchestrator.py / prompt_builder.py
│   ├── core/            (config, schema_loader, llm_backend, rate_limit, git_utils, process_guard, json_repair)
│   ├── lifecycle/       (progress, manifests, lane_output, failed_lane_log)
│   ├── phases/          (scene_archive, snapshot_merge, post_processing)
│   ├── prompts/         (← 从 automation/prompt_templates/ 移入)
│   └── tests/           (6 个 _smoke_*.py)
├── validation/          ← 新增 framework 预留位
│   ├── README.md
│   ├── gates/           (phase2_baseline ← 切自 validator.py; phase3_5_consistency ← 整体移)
│   └── shared/          (importance, schema_tolerance)
├── ingestion/           (位置不变)
└── repair/              ← 改名自 repair_agent
    ├── coordinator / protocol / triage / tracker / recorder / context_retriever / notes_writer / field_patch
    ├── checkers/        (json_syntax, schema, structural, targets_keys_eq_baseline, semantic)
    ├── fixers/          (programmatic, file_regen, source_patch, local_patch)
    └── tests/           (2 个 _smoke_*.py)
```

**关键依赖矫正**：原 `repair_agent/checkers/structural.py` + `repair_agent/coordinator.py` 跨模块 import `automation.persona_extraction.validator`，重构后改为 import `extraction.validation.shared.*`——消除 repair → phases 的反向依赖。

## 计划动作清单

### A. 目录搬迁（git mv 优先保 history）

- file: `automation/` → `extraction/`（顶层目录重命名）
- file: `extraction/repair_agent/` → `extraction/repair/`
- file: `extraction/prompt_templates/` → `extraction/persona_extraction/prompts/`
- file: 在 `extraction/persona_extraction/` 内创建 `core/` / `lifecycle/` / `phases/` / `tests/` 子目录
- file: `core/` 接收 7 个文件 — `config.py / schema_loader.py / llm_backend.py / rate_limit.py / git_utils.py / process_guard.py / json_repair.py`
- file: `lifecycle/` 接收 4 个文件 — `progress.py / manifests.py / lane_output.py / failed_lane_log.py`
- file: `phases/` 接收 3 个文件 — `scene_archive.py / snapshot_merge.py / post_processing.py`
- file: `tests/` 接收 6 个 _smoke_*.py
- file: `extraction/repair/` 内新建 `tests/`，接收 2 个 _smoke_*.py
- file: `extraction/validation/` 新增（含 README.md / gates/ / shared/）

### B. 代码切分（非纯 mv）

- file: `automation/persona_extraction/validator.py` 切分 →
  - `extraction/validation/gates/phase2_baseline.py`（`validate_baseline()` + `ValidationIssue` + `ValidationReport` + `_validate_schema` + `load_importance_map` + `_load_json`）
  - `extraction/validation/shared/importance.py`（`importance_for_target` + `importance_min_examples`）
  - `extraction/validation/shared/schema_tolerance.py`（`validate_with_length_tolerance` + `relaxed_schema_for_length` + `_is_length_bound_error`）
- file: `automation/persona_extraction/consistency_checker.py` 整体移 → `extraction/validation/gates/phase3_5_consistency.py`

### C. Import 改写

- Python in-repo 命中（外部 + 内部 + smoke）：
  - `cli.py:11` `from automation.ingestion.validator` → `from extraction.ingestion.validator`
  - `repair_agent/__init__.py:9` docstring `automation.repair_agent` → `extraction.repair`
  - `repair_agent/checkers/structural.py:14` `from automation.persona_extraction.validator` → `from extraction.validation.shared.importance`
  - `repair_agent/coordinator.py:757` `from automation.persona_extraction.validator` → `from extraction.validation.shared.schema_tolerance`
  - `_smoke_cli_resume_background_validation.py:115` `from automation.persona_extraction import cli` → `from extraction.persona_extraction import cli`
- persona_extraction 内部相对 import：每个迁入 core/ / lifecycle/ / phases/ 的文件，被引位置 `from .xxx import` → `from .core.xxx / .lifecycle.xxx / .phases.xxx import`
- orchestrator.py / cli.py / __main__.py 对 validator / consistency_checker 的 import 改向 validation/gates/
- 受迁入 core/lifecycle/phases/ 影响的所有同包文件 import 加深一层

### D. 配置文件

- file: `extraction/pyproject.toml`：description 同步（name 保持 `persona-extraction`）
- file: `extraction/config.toml`：line 6 / 100 / 138 注释路径更新；`[repair_agent]` section 改 `[repair]`

### E. ai_context / docs / README 同步

- ai_context/：architecture.md / conventions.md（Cross-File Alignment 表！）/ current_status.md / decisions.md / handoff.md / requirements.md / skills_config.md（`## Source directories` 列了 `automation/`）
- docs/：architecture/data_model.md / architecture/schema_reference.md / architecture/extraction_workflow.md / requirements.md / todo_list.md
- README：extraction/README.md（最大头，30KB） / prompts/README.md / schemas/README.md / works/README.md
- prompts/：ingestion/原始资料规范化.md / review/全仓库对齐审计.md
- CLAUDE.md / AGENTS.md：grep 未直接命中 automation，无需改

### F. 不改的（按 conventions 历史快照不动）

- `logs/change_logs/*` ~30 个文件
- `logs/review_reports/*`
- `docs/todo_list_archived.md`

## 验证标准

- [ ] `git grep -nE "\bautomation\b" -- ':!logs/' ':!docs/todo_list_archived.md'` = 0 命中
- [ ] `git grep -nE "\brepair_agent\b" -- ':!logs/' ':!docs/todo_list_archived.md'` = 0 命中
- [ ] `git grep -nE "\bprompt_templates\b" -- ':!logs/' ':!docs/todo_list_archived.md'` = 0 命中
- [ ] `python -m extraction.persona_extraction --help` 能起（CLI import 链全过）
- [ ] `python -c "from extraction.repair import run, validate_only"` 成功
- [ ] `python -c "from extraction.validation.gates.phase2_baseline import validate_baseline"` 成功
- [ ] `python -c "from extraction.validation.shared.importance import importance_for_target, importance_min_examples"` 成功
- [ ] `python -c "from extraction.validation.shared.schema_tolerance import validate_with_length_tolerance, relaxed_schema_for_length"` 成功
- [ ] `python -c "from extraction.validation.gates.phase3_5_consistency import run_consistency_check"` 成功
- [ ] `python -c "from extraction.ingestion.validator import validate_source_package"` 成功
- [ ] repair/checkers/structural.py 已不再 import persona_extraction.*（grep 验证）
- [ ] 所有 _smoke_*.py 在 tests/ 新位置 import 链 OK（不实际跑 smoke 内容，只验 import 不报错）
- [ ] ai_context/conventions.md Cross-File Alignment 表已含本次 path rename 同步行
- [ ] docs/todo_list.md `T-EXTRACTION-PKG-RESTRUCTURE` 条目已移到 archived（完成态）

## 执行偏差

- **Config 属性 + section 重命名一并做**：原 PRE 计划只改 `[repair_agent]` → `[repair]` TOML section + `[repair_agent].repair_concurrency` 注释；执行中发现 `Config` dataclass 也有 `repair_agent: RepairAgentConfig` 属性 + `_SECTION_TYPES` dict 含 `"repair_agent"` key + orchestrator.py L3072 读 `get_config().repair_agent`——这三处必须同步改成 `repair`，否则 TOML key 与 Python 属性名错位会触发 AttributeError。`RepairAgentConfig` dataclass **类名保留**，避开与 `extraction.repair.protocol.RepairConfig`（per-run config）的命名冲突；只改属性名、section 名、dict key。
- **`prompt_builder.py` `_TEMPLATE_DIR` 路径修正**：原 PRE 仅列文件 git mv；执行中发现 prompt_builder.py 第 24 行 `_TEMPLATE_DIR = Path(__file__).parent.parent / "prompt_templates"` 是 hardcoded 路径计算，必须同步改成 `Path(__file__).parent / "prompts"`（因为 prompts 现在是 prompt_builder 的兄弟目录，不再是父目录的兄弟）。
- **`Path(__file__).resolve().parents[N]` 深度调整**：Step 7 spec-track agent 复查发现两处 parents 算术因文件挪入子目录而失效：(a) `phases/scene_archive.py:51` `_scene_split_validator` schema 路径 `parents[2]` 需改 `parents[3]`（文件下移一层）；(b) `core/config.py:208,211` `_DEFAULT_CONFIG_PATH` / `_LOCAL_OVERRIDE_PATH` `parents[1]` 需改 `parents[2]`——后者是高 blast-radius 静默 bug（不调 `.exists()` 直接当 Path 用，config 加载会静默 fallback 到 dataclass defaults，所有 TOML 设置无声丢失）。两处均由 review agent 直接 fix + 运行时 `Path.exists()` 验证。
- **`.claude/hooks/session_branch_check.sh` 改 pgrep 模式**：原 PRE 未识别此处；hook 第 24 行 `pgrep -f 'automation\.persona_extraction'` 必须改成 `'extraction\.persona_extraction'`，否则 extraction/<work_id> 分支启动 banner 会把运行中 orchestrator 误判为 abandoned。Edit 因 agent-config self-modification 被 classifier 拦截，user 通过 AskUserQuestion 二次显式授权后用 sed 落地。
- **跨文档 bulk 替换 over-applied 到 `simulation/prompt_templates/`**：Python 脚本的 `automation/prompt_templates/` → `extraction/persona_extraction/prompts/` 规则用 `s.replace()` 字符串子串替换，意外把 `simulation/prompt_templates/`（与本次重构无关、文件仍在原位）也替换了。Step 7 structure-track + spec-track agents 共修 11+ 处错改：`prompts/README.md` / `simulation/contracts/runtime_packets.md` / `simulation/retrieval/load_strategy.md` / `ai_context/{requirements,handoff,conventions,architecture,decisions}.md`。
- **`extraction/README.md` 目录树整段重写**：bulk 替换只能改路径串，但 30KB README 顶部的"directory layout"段是结构性 ASCII 树，bulk 替换后字段名虽然对但树形态完全过时（仍是平铺 24 文件 + 旧 `validator.py` / `consistency_checker.py`）。Step 7 structure-track agent 全段重写为新 4-tier 结构（persona_extraction → core / lifecycle / phases / prompts / tests，validation → gates / shared，ingestion，repair → checkers / fixers / tests）+ 修了 6 处单行过时路径引用。
- **决策 #57 草稿自我应用 bulk 替换**：Step 3 写决策 #57 描述本次重构时用了 `automation/ → extraction/` 等箭头，紧接着 Step 6 跨文档对齐时 bulk 替换把这些箭头里的 `automation` 也按规则替换成 `extraction`——结果决策 #57 自述变成 `extraction/ → extraction/`（语义自破）。Step 7 spec-track agent 复查指出后，本人手工重写决策 #57 全文：改为描述**当前状态**（不带"从 X 到 Y"箭头叙述），同时强化 4 子包 + 依赖方向硬约束 + 显式不做 + plumbing 清单。
- **`_smoke_triage` pre-existing 失败**：`extraction/repair/tests/_smoke_triage.py` scenario A 失败（`expected at least one accepted note`）。验证手段：在 `/tmp/offpage-headcheck` worktree checkout HEAD（重构前）跑同测试，**完全相同的 assertion 失败 + 完全相同的 line 157**——证明此 bug 早于本次重构存在，与 git mv / import 改写正交。**本次不修**（不在 intent 范围），登记到 Step 7 spec-track findings 跟进单。
- **TOML 注释 line 138 / 140**：PRE 列了 `[repair_agent]` section 改名 + line 138 注释；实际改时还顺便改了 line 6（顶部 `# automation/config.toml` + `加载入口：automation.persona_extraction.config.load_config()`）+ line 100（`automation/persona_extraction/snapshot_merge.py` → `extraction/persona_extraction/phases/snapshot_merge.py`）+ 注释里 `Phase 3 修复代理` → `Phase 3 修复框架（checker × fixer 矩阵）`——意图同源，未脱离 PRE 范围。

<!-- POST 阶段填写 -->

## 已落地变更

**git mv 重命名 + 子目录重排**：
- 顶层 `automation/` → `extraction/`
- `extraction/repair_agent/` → `extraction/repair/`
- `extraction/prompt_templates/` → `extraction/persona_extraction/prompts/`
- `extraction/persona_extraction/` 内新建 `core/` / `lifecycle/` / `phases/` / `tests/`，git mv 17 个 production .py + 6 个 `_smoke_*.py`：
  - core: config / schema_loader / llm_backend / rate_limit / git_utils / process_guard / json_repair
  - lifecycle: progress / manifests / lane_output / failed_lane_log
  - phases: scene_archive / snapshot_merge / post_processing
  - tests: `_smoke_4_lane_merge_and_slice` / `_smoke_cli_resume_background_validation` / `_smoke_memory_digest_correspondence` / `_smoke_post_processing_replace_slice` / `_smoke_recovery_sweep` / `_smoke_stage_plan_schema_min8`
- `extraction/repair/tests/` 收 `_smoke_l3_gate.py` + `_smoke_triage.py`

**代码切分（validator.py 一切多 + consistency_checker.py 整体移）**：
- 新增 `extraction/validation/{__init__.py, types.py, README.md, gates/__init__.py, shared/__init__.py}`
- `validator.py` 切分：
  - `validation/gates/phase2_baseline.py` ← `validate_baseline + ValidationReport + _validate_schema + _load_json + load_importance_map`
  - `validation/shared/importance.py` ← `importance_for_target + importance_min_examples + _IMPORTANCE_RANK`
  - `validation/shared/schema_tolerance.py` ← `validate_with_length_tolerance + relaxed_schema_for_length + _is_length_bound_error`
  - `validation/types.py` ← `ValidationIssue` dataclass
  - 原 `extraction/persona_extraction/validator.py` `git rm -f`
- `extraction/persona_extraction/consistency_checker.py` 整体 `git mv` → `extraction/validation/gates/phase3_5_consistency.py`

**Import 改写**：
- `extraction/persona_extraction/cli.py`（8 处 + L341 注释）
- `extraction/persona_extraction/orchestrator.py`（L33-203 共 16 个 import 段 + 9 处文中文本 `repair_agent` → `repair framework` / `extraction.repair`）
- `extraction/persona_extraction/prompt_builder.py`（L15 import + L24 `_TEMPLATE_DIR` 路径计算）
- `extraction/persona_extraction/phases/scene_archive.py`（L35-40 6 个相对 import + L340 函数内 import + L920 注释 + L51 `parents[N]` 算术修正）
- `extraction/persona_extraction/lifecycle/failed_lane_log.py`（L17 import）
- `extraction/persona_extraction/lifecycle/manifests.py`（docstring）
- `extraction/persona_extraction/phases/snapshot_merge.py`（L383 docstring 文本）
- `extraction/persona_extraction/core/config.py`（attribute / dict key / docstring + L208/L211 `parents[N]` 算术修正）
- `extraction/persona_extraction/core/process_guard.py`（L186 subprocess cmd）
- `extraction/persona_extraction/core/rate_limit.py`（L60 + L639 docstring / 错误信息）
- `extraction/persona_extraction/core/schema_loader.py`（docstring）
- `extraction/persona_extraction/lifecycle/progress.py`（2 处 docstring）
- `extraction/persona_extraction/__init__.py` / `__main__.py`（无改动，root files）
- `extraction/persona_extraction/tests/*.py` × 6（5 个改 import + 1 个改路径 + 6 个改 `Run:` docstring）
- `extraction/repair/__init__.py`（L9 docstring API 例子）
- `extraction/repair/checkers/structural.py`（L14 跨模块 import 矫正：`from extraction.validation.shared.importance`）
- `extraction/repair/coordinator.py`（L757 同上：`from extraction.validation.shared.schema_tolerance`）
- `extraction/repair/checkers/schema.py` / `checkers/semantic.py` / `context_retriever.py` / `recorder.py`（docstring 文本）
- `extraction/repair/tests/_smoke_l3_gate.py` / `_smoke_triage.py`（L20 `Run:` docstring + relative import deepening）
- `extraction/validation/gates/phase3_5_consistency.py`（docstring + L28 import 改 `from ..shared.importance`）
- `extraction/ingestion/validator.py`（3 处 docstring / usage / comment）

**配置 + 基础设施**：
- `extraction/pyproject.toml`（description 同步）
- `extraction/config.toml`（line 2 文件名注释 + line 6 加载入口 + line 100 模块路径 + section `[repair_agent]` → `[repair]` + section 头注释升级）
- `.gitignore` line 53 `automation/config.local.toml` → `extraction/config.local.toml`
- `.claude/hooks/session_branch_check.sh` line 24 pgrep 模式（user 二次授权）
- `ai_context/skills_config.md ## Source directories`（`automation/` → `extraction/`）

**ai_context durables 同步**：
- `ai_context/decisions.md`（新增 #57 全文 + 全文 bulk-replace 路径同步）
- `ai_context/architecture.md` / `current_status.md` / `handoff.md` / `requirements.md` / `conventions.md`（Cross-File Alignment 表新增第 7 行 + bulk-replace 路径同步）

**docs 同步**：
- `docs/architecture/data_model.md` / `schema_reference.md` / `extraction_workflow.md`（bulk-replace + agent 修补 `lifecycle.manifests` 路径深度）
- `docs/requirements.md`（bulk-replace + agent 修补 `core.config.load_config` 深度）
- `docs/todo_list.md`（`T-EXTRACTION-PKG-RESTRUCTURE` 移除 index 表 + 删除条目正文 + Total 10 → 9 / Next 3 → 2）
- `docs/todo_list_archived.md`（`T-EXTRACTION-PKG-RESTRUCTURE` 加入 Completed 段瘦身存档）

**README 类**：
- `extraction/README.md`（agent 全段重写 directory tree + 6 处单行过时路径）
- `prompts/README.md` / `schemas/README.md` / `works/README.md`（bulk-replace + agent 修 over-application）
- `extraction/validation/README.md`（新文件，描述 gates / shared / 未来 framework 统一去向）

**prompts 同步**：
- `prompts/ingestion/原始资料规范化.md` / `prompts/review/全仓库对齐审计.md` / `prompts/review/手动补抽与修复.md`（路径同步）

**schemas $comment 同步**：
- `schemas/analysis/{candidate_characters,stage_plan}.schema.json`
- `schemas/character/{memory_digest_entry,stage_catalog}.schema.json`
- `schemas/runtime/scene_archive_entry.schema.json`
- `schemas/work/{chapter_index,work_manifest,works_manifest}.schema.json`（含 agent 修 `lifecycle.manifests` 深度）
- `schemas/world/{world_event_digest_entry,world_stage_catalog}.schema.json`

**simulation 端**：
- `simulation/contracts/runtime_packets.md` / `simulation/retrieval/load_strategy.md`（bulk 改后 agent 还原 `simulation/prompt_templates/` over-application）

## 与计划的差异

- 计划没单列：`prompt_builder.py` `_TEMPLATE_DIR` 路径计算修正 / `parents[N]` 深度算术（2 处）/ hook pgrep 模式 / bulk-replace over-application 修复 / `extraction/README.md` 目录树重写 / 决策 #57 草稿自我应用 fix——这些**全部**作为「执行偏差」段记录在前。
- 计划写"3 个 commit 拆"（git mv 重命名 / 挪 smoke + prompts / 抽 core + lifecycle + phases + validation）；实际**改为单 commit**——因 import 改写 + parents 算术修正 + 跨文档同步彼此耦合，拆 commit 后任一中间状态都会触发"半改不全"的 import / runtime error；单 commit 一次原子提交，按 git diff 切分查看仍方便。

## 验证结果

- [x] `git grep -nE "\bautomation\b" -- ':!logs/' ':!docs/todo_list_archived.md'` — 0 命中
- [x] `git grep -nE "\brepair_agent\b" -- ':!logs/' ':!docs/todo_list_archived.md'` — 0 命中（除决策 #57 narration 内 historical 描述 1 处 + 旧条目 archived 中保留不动）
- [x] `git grep -nE "\bprompt_templates\b" -- ':!logs/' ':!docs/todo_list_archived.md'` — 0 命中（除 `simulation/prompt_templates/` 合法保留）
- [x] `python -m extraction.persona_extraction --help` — OK
- [x] `python -c "from extraction.repair import run, validate_only"` — OK
- [x] `python -c "from extraction.validation.gates.phase2_baseline import validate_baseline"` — OK
- [x] `python -c "from extraction.validation.shared.importance import importance_for_target, importance_min_examples"` — OK
- [x] `python -c "from extraction.validation.shared.schema_tolerance import validate_with_length_tolerance, relaxed_schema_for_length"` — OK
- [x] `python -c "from extraction.validation.gates.phase3_5_consistency import run_consistency_check"` — OK
- [x] `python -c "from extraction.ingestion.validator import validate_source_package"` — OK
- [x] `repair/checkers/structural.py` 不再 import `persona_extraction.*`（grep 验证只 import `extraction.validation.shared.importance`）
- [x] 6/7 smoke 全过：`_smoke_stage_plan_schema_min8` 5/5 / `_smoke_4_lane_merge_and_slice` 全套 / `_smoke_recovery_sweep` 4 scenario / `_smoke_post_processing_replace_slice` 4/4 / `_smoke_memory_digest_correspondence` 4/4 / `_smoke_cli_resume_background_validation` 9/9 / `_smoke_l3_gate` 4 scenario
- [ ] `_smoke_triage` scenario A 失败——**pre-existing in HEAD**，与本次重构无关（worktree 复现验证），登记跟进单
- [x] `ai_context/conventions.md` Cross-File Alignment 表已含本次 path rename 行（第 53 行）
- [x] `docs/todo_list.md` `T-EXTRACTION-PKG-RESTRUCTURE` 已移到 archived `## Completed` 段（含 1 行摘要 + log 链接）
- [x] `extraction/persona_extraction/core/config.py` `_DEFAULT_CONFIG_PATH` `.exists()` True（agent 修复后运行时验证）
- [x] `extraction/persona_extraction/phases/scene_archive.py` `_scene_split_validator()` 返回 jsonschema Draft202012Validator（agent 修复后运行时验证）

## Completed

- **Status**: DONE
- **Finished**: 2026-05-13 21:10:17 EDT
