# codex_full_repo_alignment_audit_landing

- **Started**: 2026-05-07 05:23:08 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

- 上游：`logs/review_reports/2026-05-07_021956_codex_full-repo-alignment-audit.md`（codex 模型 `/full-review` 出报告，6 项 finding：H1 / H2 / M1 / M2 / M3 / L1）。
- 经 `/check-review codex` 复核：6 项全部判"真实"，无失效；与 35c803c 已落地的 opus-4-7 那批不重叠。
- 用户拍板：
  - Q-A：M1 走路径 A（改 prompt 不改 schema）。具体措辞：scene_split.md L29 "能 30 字写清的 summary 不要为凑 50 字注水" → "能用更少字写清的 summary 不要为凑字数上限而注水"（去除具体数字耦合，保留"硬上限不是配额"语义）。
  - Q-B：`read_structure_mode` 缺字段 raise（双兜底，validator 没接到的角落也保护）。
  - Q-C：post-processing 空 slice 仍 emit warning（信息提示，方便人工核查空阶段语义）。
  - Q-D：`automation/persona_extraction/cli.py` 加进 `conventions.md` Cross-File Alignment `structure_mode` 行（cli 是 ingestion gate 唯一调用点）。

## 结论与决策

按 codex 报告 6 项 finding 全部修，分 4 个 commit；范围严格收敛在报告内，不顺手扩范围。

- **H1**：`automation/persona_extraction/consistency_checker.py` 增加 list-shaped JSON loader；memory_id correspondence + memory_digest summary equality 两个检查改用新 loader；新加 fixture/单测覆盖 timeline 有 1 条/digest 空、summary != digest_summary 两个 regression 场景。
- **H2 + M2**（同 commit，"输入完整性"主题）：
  - `automation/persona_extraction/cli.py` 在 `acquire_lock()` + `preflight_check` 之后接 `validate_source_package(...)`；error 释放 lock + sys.exit(1)；仅 extraction 子命令需要。
  - `automation/persona_extraction/manifests.py::read_structure_mode` 改为 source-manifest authoritative；source 缺字段 → raise ValueError；source/works 不一致 → raise ValueError；不再静默 default `"monolithic"`。
  - `automation/README.md` 删 "default `monolithic`"，措辞改为"必填（schema required，缺省即校验失败）"，与 `docs/architecture/extraction_workflow.md:31` 对齐。
  - `automation/persona_extraction/scene_archive.py::_process_chapter` missing/empty 分支：新增 `_mark_input_error(entry, msg)` 直接置 `ChapterState.ERROR` + error_message + last_updated（不增 retry_count，不进 retry queue），替代当前空 return 让 entry 永远滞留在 PENDING。
  - `ai_context/conventions.md` Cross-File Alignment `structure_mode` 行末加 `automation/persona_extraction/cli.py (ingestion gate call site)`。
- **M3**：`automation/persona_extraction/post_processing.py` 两个 early-return 改 replace-slice：
  - `generate_memory_digest` (L101–110)：空 `new_entries` 仍走 read existing → kept = filter (drop current_stage slice) → write 路径，保留 warning issue。
  - `generate_world_event_digest` (L274–278)：空 `stage_events` 同改造。
  - `ai_context/decisions.md` 在 Phase 3.5 / post-processing 段补一句"post-processing 对 derived digests 永远走 replace-slice 语义，包括空源数组情形"。
- **L1**：`ai_context/skills_config.md` `## Example artifact directories` 段对 `users/_template/` 加注解，说明它是 substitution template（含 literal placeholders by design），不是可直接 schema validate 的 fixture。
- **M1**：`automation/prompt_templates/scene_split.md:29` 单行措辞修改（用户钦定）。

不动：schemas/、simulation/（除非 import smoke 命中）、`/full-review` 报告之外的旁枝、conventions.md 其他段、skills_config.md 其他段、users/_template/* 文件本体。

## 计划动作清单

### Commit 1 — H1：consistency_checker.py 修 memory_timeline 对账空跑

- file: `automation/persona_extraction/consistency_checker.py`
  - 新增 `_load_json_array(path: Path) -> list | None`（参照 `_load_json` 的"只读 + log warning + 返回 None"语义，但仅接受顶层 list；非 list/不可读返回 None）。
  - `_check_memory_id_correspondence` (L391) `_load_json(_timeline_path(...))` → `_load_json_array(_timeline_path(...))`，删除 `if isinstance(timeline, list):` 判型条件，改为 `if timeline is not None:`。
  - `_check_memory_digest_summary_equality` (L439) 同改造。
  - 不动 `_load_json` 本身（其它 dict-shaped 调用点保持现状）；不动 `_load_jsonl`。
- file: `automation/persona_extraction/consistency_checker.py`（同文件）
  - 在文件底部添加 `_smoke_memory_digest_correspondence()` 函数模式（仿照仓库现有 `_smoke_l3_gate` 风格），覆盖 4 场景：
    - A：timeline 1 条 / digest 空 → expect error "missing from digest"
    - B：timeline 空 / digest 1 条 → expect warning "in digest but not in any timeline"
    - C：timeline 1 条 / digest 1 条相同 mid 但 summary != digest_summary → expect error
    - D：timeline 1 条 / digest 1 条相同 mid 且 summary == digest_summary → expect no issue
  - 用 `tempfile.TemporaryDirectory()` 构造 work_dir 骨架：`works/{work_id}/characters/{cid}/canon/memory_timeline/{stage_id}.json` + `works/{work_id}/characters/{cid}/canon/memory_digest.jsonl`。

### Commit 2 — H2 + M2：ingestion validator 接入 CLI + structure_mode source-first + scene_archive missing/empty 进 ERROR 终态

- file: `automation/persona_extraction/cli.py`
  - 在 `acquire_lock()` 之后、preflight 之后（约 L237 之后），添加 `from automation.ingestion.validator import validate_source_package`；调 `validate_source_package(project_root, args.work_id)`；若 `not report.passed`，print summary、`orch.release_lock()`、`sys.exit(1)`。
  - 仅作用于 extraction 主子命令（即 cli.py 的 main extraction 路径），不影响其它查询子命令（如有）。
- file: `automation/persona_extraction/manifests.py`
  - `read_structure_mode` (L101–117) 改造：source manifest 优先；source 缺字段 raise `ValueError("source manifest missing structure_mode for work {work_id}")`；works manifest 存在且与 source 不一致 raise `ValueError(...mismatch...)`；source/works 都缺 → raise（不再 fallback `"monolithic"`）。
  - docstring 同步更新，去掉"works manifest 优先"措辞。
- file: `automation/README.md`
  - L357–358 把 "default `monolithic`" 删除，措辞改为与 `docs/architecture/extraction_workflow.md:31` 对齐（"必填（schema required，缺省即校验失败）"）。
- file: `automation/persona_extraction/scene_archive.py`
  - 在 `_mark_failed` 之后（约 L372）新增 `_mark_input_error(entry: ChapterEntry, msg: str) -> str`：直接置 `ChapterState.ERROR` + error_message + last_updated，不增 retry_count，返回 msg。
  - `_process_chapter` (L387/L394) 两个 missing/empty return 改成 `return chapter_id, False, _mark_input_error(entry, msg)`。
- file: `ai_context/conventions.md`
  - Cross-File Alignment `structure_mode` 行末加 `automation/persona_extraction/cli.py（ingestion validator 调用点）`。

### Commit 3 — M3：post_processing.py 两个 early-return 改 replace-slice

- file: `automation/persona_extraction/post_processing.py`
  - `generate_memory_digest` L101–110：把 `if not new_entries: issues.append(...) return issues` 改成"append warning issue 后继续走 read existing → kept = filter → write 三步"——保留 issue 让 caller 收 warning，但实际 IO 必须发生（kept 永远是"existing 中不属于 current_stage_num 的"，effectively 删除该 stage slice）。
  - `generate_world_event_digest` L274–278：同改造（但这里"空"是 `stage_events` 不是 `list` 或为空 → 区分清楚：现有 `if not isinstance(...) or not stage_events:` 判定 → 改为先确认 list 类型；若为空则 issue + 继续走 kept filter + write）。
  - 注意 `generate_world_event_digest` 接口的 `digest_path` 是 `works/{work_id}/world/world_event_digest.jsonl`；filter 用 `_parse_stage_number(stage_id)` 对应 `event_id` 的 S### 段。
- file: `ai_context/decisions.md`
  - 找现有 §27 系列或 Phase 3.5 / post-processing 段，补一句契约："post-processing 对 derived digests 永远走 replace-slice 语义；当前 stage 派生数组为空也要落盘移除该 stage 旧条目，不仅 emit warning"。具体编号根据现有索引顺延。

### Commit 4 — L1 + M1：skills_config.md 注解 + scene_split prompt 措辞

- file: `ai_context/skills_config.md`
  - L80–87 `## Example artifact directories` 段对 `users/_template/` 加注解：`(substitution template — literal placeholders by design; not schema-valid until replaced)`。
- file: `automation/prompt_templates/scene_split.md`
  - L29 "能 30 字写清的 summary 不要为凑 50 字注水" → "能用更少字写清的 summary 不要为凑字数上限而注水"。

## 验证标准

- [ ] 全 import chain 通过：`python -c "import automation.persona_extraction.cli, automation.persona_extraction.orchestrator, automation.persona_extraction.scene_archive, automation.persona_extraction.consistency_checker, automation.persona_extraction.post_processing, automation.persona_extraction.manifests, automation.persona_extraction.validator, automation.ingestion.validator, automation.repair_agent.coordinator"`
- [ ] H1 fixture：`python -m automation.persona_extraction.consistency_checker --smoke memory_digest_correspondence`（或同等 entry point）4 场景 A/B/C/D 全过
- [ ] 现有 `_smoke_l3_gate` 4 场景无回归
- [ ] 现有 `_smoke_recovery_sweep` 4 场景无回归
- [ ] grep `default \`monolithic\`` `automation/README.md` → 0 命中
- [ ] grep `return "monolithic"` `automation/persona_extraction/manifests.py` → 0 命中
- [ ] grep `validate_source_package` `automation/persona_extraction/cli.py` → ≥ 1 命中
- [ ] grep `_mark_input_error` `automation/persona_extraction/scene_archive.py` → ≥ 2 命中（定义 + 至少一个调用点；missing 与 empty 共两个调用 → 总共 ≥ 3）
- [ ] grep `30 字写清` `automation/prompt_templates/scene_split.md` → 0 命中
- [ ] grep `凑字数上限` `automation/prompt_templates/scene_split.md` → 1 命中
- [ ] grep `_load_json_array` `automation/persona_extraction/consistency_checker.py` → 定义 1 + 调用 ≥ 2
- [ ] post_processing 空 slice 路径手动 fixture：构造 timeline 空 + existing digest 含 current stage 旧条目 → 跑完 existing kept 不再含旧条目（手动 Python REPL 跑或在 consistency_checker 同位置加 `_smoke_post_processing_replace_slice`）

## 执行偏差

- **Step 7 review 发现并即修**：`automation/persona_extraction/manifests.py::write_works_manifest` (L93) 仍有 `source_manifest.get("structure_mode", "monolithic")` 残留 default fallback。这是 Phase 1.5 source → works manifest copy-forward 路径，与 H2 引入的"`structure_mode` no implicit default-fill"契约直接冲突。在新加的 source-mode 必填断言后改为直接传 `source_mode`（已在前面 raise 兜底）。属于 Step 7"一行能修的小问题 → 发现即修"范畴，未扩出 H2 intent。

## 已落地变更

### Commit 1 — H1：consistency_checker.py memory_timeline 对账

- `automation/persona_extraction/consistency_checker.py`
  - 新增 `_load_json_array(path) -> list | None`（第 192-216 行附近，docstring 区分对 `_load_json` 的职责切分；非 list 顶层返回 None）
  - `_check_memory_id_correspondence` (L391) timeline 读取改用 `_load_json_array`
  - `_check_memory_digest_summary_equality` (L439) timeline 读取改用 `_load_json_array`
- `automation/persona_extraction/_smoke_memory_digest_correspondence.py`（新文件，~170 行）：4 场景 A/B/C/D 覆盖 timeline 1/digest 0、timeline 0/digest 1、summary 不等、summary 相等

### Commit 2 — H2 + M2：ingestion validator 接入 CLI + structure_mode source-first + scene_archive 输入失败终态

- `automation/persona_extraction/cli.py`
  - import `validate_source_package`
  - 在 `acquire_lock()` + `preflight_check` 之后新增 ingestion gate：失败 print summary → release_lock → sys.exit(1)
- `automation/persona_extraction/manifests.py`
  - `read_structure_mode` (L101+) 改为 source-manifest authoritative；source 缺字段或 source/works 不一致直接 raise ValueError；不再 default `"monolithic"`
  - `write_works_manifest` (L63+) 顶部新增 source_mode 断言，缺字段 raise；下方 `manifest["structure_mode"]` 直接传 `source_mode`，不再 `.get(..., "monolithic")` fallback
- `automation/README.md`
  - L357-363 措辞改为"必填——schema required，缺省即校验失败；works manifest 在 Phase 1.5 从 source 拷字段，read_structure_mode 以 source 为权威，works/source 不一致直接 raise"
- `automation/persona_extraction/scene_archive.py`
  - 新增 `_mark_input_error(entry, msg)`（L375 附近）：直接置 `ChapterState.ERROR` + error_message + last_updated，不增 retry_count、不进 retry queue
  - `_process_chapter` (L387-394) 两个 missing/empty return 改成 `return chapter_id, False, _mark_input_error(entry, msg)`
- `ai_context/conventions.md` Cross-File Alignment `structure_mode` 行末加 `automation/persona_extraction/cli.py (ingestion gate call site)` + 在 `read_structure_mode` 注释位补"source-manifest authoritative, raises on missing field or source/works mismatch — no implicit default-fill"
- `docs/architecture/extraction_workflow.md`
  - §1（作品入库）新增"自动 gate：cli.py 在 lock + preflight 之后调 validate_source_package"
  - §Phase 4 段补"输入层确定性失败由 _mark_input_error 直接置 ERROR（不增 retry_count、不进 retry queue），与 LLM/解析路径的 _mark_failed 终态分流"

### Commit 3 — M3：post_processing replace-slice

- `automation/persona_extraction/post_processing.py`
  - `generate_memory_digest` (L101-110) 空 `new_entries` 不再 early-return；warning issue 仍 emit，但 IO 路径继续走 read existing → kept = filter(drop current_stage_num) → write
  - `generate_world_event_digest` (L274-285) `stage_events` 类型不对仍 early-return；空数组改为 emit warning + 继续 replace-slice；下方"No digest entries generated" 改成只在"stage_events 非空但 new_entries 为空"时 emit（避免对 empty stage_events 重复 warning）
- `ai_context/decisions.md` 新增 §50：post-processing replace-slice 永远落盘，包括空源数组情形；与 #32/#33 1:1 拷贝契约 + Phase 3.5 一致性检查互锁
- `automation/persona_extraction/_smoke_post_processing_replace_slice.py`（新文件，~210 行）：4 场景 memory-A/B + world-A/B 覆盖空源 + 非空源、replace + keep

### Commit 4 — L1 + M1：skills_config 注解 + scene_split prompt 措辞

- `ai_context/skills_config.md` `## Example artifact directories` 段对 `users/_template/` 加行内注解："(substitution template — literal placeholders like `{user_id}` / `{stage_id}` are by design; not schema-valid until a real user package is created from it. See `users/README.md`.)"
- `automation/prompt_templates/scene_split.md` L29 "能 30 字写清的 summary 不要为凑 50 字注水" → "能用更少字写清的 summary 不要为凑字数上限而注水"

## 与计划的差异

- **新增**：`automation/persona_extraction/_smoke_post_processing_replace_slice.py`（PRE 计划只在 H1 加 fixture，M3 计划是"手动 fixture 跑 Python REPL"——实际写成可重复 smoke 文件，与现有 `_smoke_recovery_sweep.py` 风格一致，4 场景全过）。
- **新增**：`automation/persona_extraction/manifests.py::write_works_manifest` 也加 source_mode 必填断言 + 删 default fallback——Step 7 review 发现的小残留，与 H2 contract 严格对齐，已记入"执行偏差"段。
- **新增**：`docs/architecture/extraction_workflow.md` §1 / §Phase 4 两段补充——Step 3 实际产出，让自动 gate 与 _mark_input_error 在权威架构文档里有解释；PRE 没显式列出但在"Step 3 检查 docs/architecture/ 是否需要更新"范畴内。
- **未做**：未触及 `ai_context/current_status.md` / `next_steps.md` / `handoff.md`——本次改动属于已知架构内的 hardening / 缺口补齐，没有改 mental model 或 roadmap，不需要更新。
- **未做**：未触及 `docs/todo_list.md`——6 项 finding 都不对应现有 T-* 条目，T-INGEST-STRUCTURE-MODE 仍待 runtime 验证，本次 H2 的 CLI 接入算是该 ticket 的代码完整性 hardening，不算推进 ticket，不动其状态。

## 验证结果

- [x] 全 import chain 通过：`cli / orchestrator / scene_archive / consistency_checker / post_processing / manifests / validator / ingestion.validator / repair_agent.coordinator / repair_agent.checkers.schema` 全过
- [x] H1 fixture (`_smoke_memory_digest_correspondence`) 4/4 过：A/B/C/D 全 OK
- [x] M3 fixture (`_smoke_post_processing_replace_slice`) 4/4 过：memory-A/B + world-A/B 全 OK
- [x] `_smoke_recovery_sweep` 4 场景无回归（A/B/C/D 全 OK）
- [x] `_smoke_l3_gate` 4 场景无回归（A/B/C/D 全 OK）
- [x] grep `default \`monolithic\`` `automation/README.md` → 0 命中
- [x] grep `return "monolithic"` `automation/persona_extraction/manifests.py` → 0 命中
- [x] grep `"monolithic"` `automation/persona_extraction/manifests.py` → 0 命中（write_works_manifest 残留 default 也清掉）
- [x] grep `validate_source_package` `automation/persona_extraction/cli.py` → 2 命中（import + 调用）
- [x] grep `_mark_input_error` `automation/persona_extraction/scene_archive.py` → 3 命中（def + 2 调用）
- [x] grep `30 字写清` `automation/prompt_templates/scene_split.md` → 0 命中
- [x] grep `凑字数上限` `automation/prompt_templates/scene_split.md` → 1 命中
- [x] grep `_load_json_array` `automation/persona_extraction/consistency_checker.py` → 3 命中（def + 2 调用）
- [x] grep `isinstance(timeline, list)` `automation/persona_extraction/consistency_checker.py` → 2 命中（仍存在但前面是新 loader 取值）
- [x] grep `Draft7Validator` automation + schemas → 0 命中（35c803c 已清理无回归）
- [x] 35 个 schema `validator_for(...).check_schema(...)` → 0 失败

## Completed

- **Status**: DONE
- **Finished**: 2026-05-07 05:36:16 EDT
