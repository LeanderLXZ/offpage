# codex_check_review_followup

- **Started**: 2026-04-30 11:05:06 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

`/check-review codex` 复核了 `logs/review_reports/2026-04-26_235116_codex_full-repo-alignment-audit.md` 全部 H/M/L findings，
逐条给出真实性结论与方案草稿；用户逐条拍板：H1–H4 + M1/M3/M6/M7/M8/L3 按建议落地，
M2 放宽允许空，M5 仅 Claude 端补 `429`（Codex 端登记到 todo），L1 登记 schema-injection todo，
H5 无需修复，M4 不动。

## 结论与决策

- **H1（Phase 0 chunk 完整性 gate）**：partial 改返回 `False`；`reconcile_with_disk` 增加完整性判据；
  resume skip 路径加 schema + count 校验；最终 gate 同步加判据。
- **H2（Phase 1 三件套缺失 gate）**：`data is None` 视为 `missing` 失败入 `schema_failures`，
  共享 retry budget；retry 耗尽 `sys.exit(1)`，去掉 `else: break` 静默通过路径。
- **H3（L3 semantic false-pass）**：`_llm_call` 在 `result.success=False` 时抛
  `SemanticReviewLLMUnavailable`；semantic checker 把异常转成 blocking
  `Issue(rule="semantic_unavailable", severity="error")`，空响应 / 无法解析也判 blocking。
- **H4（RateLimitHardStop swallowed）**：Phase 0 / Phase 3 repair / Phase 4 scene_archive
  三处 worker `except Exception` 之前加 `except RateLimitHardStop: raise`。
- **H5（ai_context handoff）**：用户确认无需修复（已经在最近的更新中纠正），跳过。
- **M1（memory_importance）**：进 `memory_timeline_entry.schema.json` 的 `required`；
  `post_processing.py:184-189` 删除 `"minor"` 缺省。
- **M2（stage_snapshot 维度）**：放宽方向——schema 顶层 required 维持现状（不强制
  emotional_baseline / current_status / misunderstandings / concealments / stage_delta）；
  prompt + docs 在文案上承认"该阶段无变化"为合法空。
- **M3（commit_stage 越界）**：`commit_stage` 加 `work_id` 参数；`files` 为空时
  `git add -A works/{work_id}/`；commit 前断言所有 staged paths 在 `works/{work_id}/` 内；
  改 5 处 caller。
- **M4**：不动。
- **M5（rate-limit signals）**：抽 `_classify_rate_limit` 共用函数（signals = `rate limit / rate_limit / too many requests / 429`）；
  Claude backend 调用之；Codex backend 端登记到 todo（暂不动）。
- **M6（manual repair evidence_ref）**：改 `prompts/review/手动补抽与修复.md` 第 28 行，
  以 conventions 为主——记录在外部修复日志，不写入 schema 实例字段。
- **M7（decisions.md scene_archive stage_id）**：改 decision #29，明示 scene_archive 同时
  携带 `stage_id` + `scene_id`，digest 类才不带。
- **M8（stage_catalog 路径漂移）**：`conventions.md:86` 拆 world / character 两行；
  `requirements.md:1509` 把 character 与 world 的 `snapshot_path` 拆开。
- **L1（bounds-only）**：登记 todo（schema-injection 自动生成 prompt 段），本轮不改。
- **L3（foundation schema stale）**：改 `current_status.md:48` + `next_steps.md:26-28`，
  说明 foundation 已 schema 化（permissive）；timeline / events / locations / maps 仍待补。

## 计划动作清单

- file: `automation/persona_extraction/orchestrator.py` — H1 partial 改 False / skip 路径 schema check / final gate；H2 missing 入 failures + retry-exhaust exit；H3 `_llm_call` raise；H4 三处 except 前置 RateLimitHardStop；M3 commit_stage 5 处 caller 传 work_id
- file: `automation/persona_extraction/progress.py` — H1 `reconcile_with_disk` 加完整性判据
- file: `automation/persona_extraction/git_utils.py` — M3 `commit_stage` 加 `work_id` 参数
- file: `automation/persona_extraction/llm_backend.py` — M5 抽 `_classify_rate_limit`
- file: `automation/persona_extraction/scene_archive.py` — H4 worker except
- file: `automation/repair_agent/checkers/semantic.py` — H3 转 blocking issue
- file: `schemas/character/memory_timeline_entry.schema.json` — M1 `memory_importance` 入 required
- file: `automation/persona_extraction/post_processing.py` — M1 删 `"minor"` 兜底
- file: `automation/prompt_templates/character_snapshot_extraction.md` — M2 文案放宽（允许空）
- file: `docs/requirements.md` — M2 §940 维度文案；M8 §1509 path 拆分
- file: `ai_context/conventions.md` — M8 §86 stage_catalog 拆 world / character
- file: `ai_context/decisions.md` — M7 #29 scene_archive stage_id 表述
- file: `ai_context/current_status.md` — L3 World schemas 行
- file: `ai_context/next_steps.md` — L3 删除 "foundation schema still implicit"
- file: `prompts/review/手动补抽与修复.md` — M6 第 28 行 evidence_ref
- file: `automation/README.md` — H1/H2/H3/H4 段落同步
- file: `docs/todo_list.md` — 新增 Codex backend rate-limit + bounds-only schema-injection 两条；登记本轮已完成项移到 archived

## 验证标准

- [ ] `python -m py_compile automation/persona_extraction/orchestrator.py automation/persona_extraction/progress.py automation/persona_extraction/git_utils.py automation/persona_extraction/llm_backend.py automation/persona_extraction/scene_archive.py automation/persona_extraction/post_processing.py automation/repair_agent/checkers/semantic.py` 全过
- [ ] `python -c "import automation.persona_extraction.orchestrator; import automation.persona_extraction.progress; import automation.persona_extraction.git_utils; import automation.persona_extraction.llm_backend; import automation.persona_extraction.scene_archive; import automation.persona_extraction.post_processing; import automation.repair_agent.checkers.semantic"` 无 ImportError
- [ ] `jsonschema.Draft202012Validator.check_schema` 对所有 `schemas/**/*.schema.json` 通过
- [ ] `grep -n "evidence_ref" prompts/review/手动补抽与修复.md` 仅剩"不写入 schema 字段"语境
- [ ] `grep -n "foundation schema still implicit" ai_context/` 残留 0
- [ ] `grep -n "schemas/{world,character}/stage_catalog.schema.json" ai_context/conventions.md` 残留 0
- [ ] `_classify_rate_limit("blah 429 too many")` 返回 True 的 unit smoke
- [ ] `decisions.md` #29 包含 "scene_archive entries DO carry"
- [ ] `memory_timeline_entry.schema.json` 的 `required` 含 `memory_importance`
- [ ] `commit_stage` signature 含 `work_id` 参数；orchestrator / scene_archive 全部 caller 已更新

## 执行偏差

- 计划只改 `docs/requirements.md` §1509 path 拆分（M8）；执行时一并拆了
  `ai_context/conventions.md:86` 的 stage_catalog 段，并补了 world schema 的
  `snapshot_path` 描述（`schemas/world/world_stage_catalog.schema.json`），让
  schema 描述与新拆分一致。属于同一 finding 的连带文件，未越界。
- Step 7 复查发现 `automation/README.md` 的"磁盘对账自愈"段没有覆盖新
  `_chunk_passes_full_check` 引入的 partial / schema-fail 回退分支，加了
  规则 (2)；`docs/architecture/extraction_workflow.md` 的 Phase 0 完成门控
  + Phase 1 出口验证段也按新契约扩写。属于 Cross-File Alignment 表
  "Extraction workflow" 行的内联同步。
- M1 的"删除 `\"minor\"` 兜底"在实施时改为 `entry["memory_importance"]`
  直接索引——`entry.get(..., "minor")` 删了之后还有个 fallback，索引取值
  让缺失的 schema-illegal 状态更早 raise。语义同向，未走偏。

## 已落地变更

- `automation/persona_extraction/orchestrator.py`
  - 新增 `_chunk_passes_full_check(output_path, expected)` 静态方法（H1）。
  - `_summarize_chunk` partial 改 L3 retry → 失败再 return False（不再 True；H1）。
  - Phase 0 skip 路径改用 `_chunk_passes_full_check`，partial / corrupt 自动重抽（H1）。
  - Phase 0 worker `as_completed` 加 `except RateLimitHardStop: raise`（H4）。
  - Phase 0 final gate 改成逐 chunk schema-gated 检查 + 列出失败 chunks（H1）。
  - Phase 1 schema gate 把 `data is None` 视为 `missing_files`，与 `schema_failures`
    共享 retry budget；retry 耗尽 `sys.exit(1)`（H2）。
  - mark_done(`phase_1`) 前 defense-in-depth：三件套任一缺失即 `sys.exit(1)`（H2）。
  - Phase 3 repair worker `as_completed` 加 `except RateLimitHardStop: raise`（H4）。
  - `_llm_call` 在 `result.success=False` 时 `raise SemanticReviewLLMUnavailable`（H3）。
  - `commit_stage` 五处 caller 增传 `work_id=pipeline.work_id`（M3）。
  - 新 import：`RateLimitHardStop`（rate_limit）、`SemanticReviewLLMUnavailable`
    （repair_agent.checkers.semantic）。
- `automation/persona_extraction/progress.py`
  - `Phase0Progress.reconcile_with_disk` 加完整性判据（partial/corrupt 也回退 +
    purge），通过 `ExtractionOrchestrator._chunk_passes_full_check` 单源（H1）。
  - 新静态方法 `_expected_chapter_count(entry)` 解析 chunks 字符串。
- `automation/persona_extraction/git_utils.py`
  - `commit_stage` 加 `work_id` 参数：`files` 为空且 `work_id` 给定时
    `git add -A works/{work_id}/`；commit 前用 `git diff --cached --name-only`
    断言 staged paths 全部以 `works/{work_id}/` 起头，越界即 return None（M3）。
- `automation/persona_extraction/llm_backend.py`
  - 抽 `_classify_rate_limit(text)` + `_RATE_LIMIT_SIGNALS`
    （含 `429`）（M5）。
  - Claude backend 撞限额分支改用 `_classify_rate_limit(stderr) or
    _classify_rate_limit(stdout)`，覆盖 `429`（M5）。
- `automation/persona_extraction/scene_archive.py`
  - import `RateLimitHardStop`；Phase 4 chapter worker `future.result()` 加
    `except RateLimitHardStop: raise`（H4）。
- `automation/persona_extraction/post_processing.py`
  - `_timeline_to_digest` 把 `entry.get("memory_importance", "minor")` 改成
    `entry["memory_importance"]`：缺失时 KeyError，依赖 schema-required gate
    把空值挡在更早层（M1）。
- `automation/repair_agent/checkers/semantic.py`
  - 新异常 `SemanticReviewLLMUnavailable`（H3）。
  - `_review_file` 把 `except SemanticReviewLLMUnavailable` 转 blocking
    `Issue(rule="semantic_unavailable", severity="error")`；其它 `Exception`
    转 `semantic_check_crashed`；不再 `return []`（H3）。
  - `_parse_response` 把空响应 / 找不到 `[`/`]` / `JSONDecodeError` 都转
    blocking `Issue(rule="semantic_unparseable", severity="error")`，
    `text == "[]"` 仍是 clean pass（H3）。
- `automation/prompt_templates/character_snapshot_extraction.md`
  - §10.1 自包含维度段：把 "必须包含以下全部维度" 改成 "必须考虑以下全部维度"，
    并增加"结构性骨架 vs 情境维度"分层说明，承认情境维度（emotional_baseline
    / current_status / misunderstandings / concealments / stage_delta）允许空
    数组 / 空对象 / 省略，但 stage_delta 必须显式说明对照过哪些维度（M2）。
- `schemas/character/memory_timeline_entry.schema.json`
  - `required` 增加 `memory_importance`（M1）。
- `schemas/world/world_stage_catalog.schema.json`
  - `snapshot_path.description` 加上 "通常为 world/stage_snapshots/{stage_id}.json"
    具体前缀（M8）。
- `docs/requirements.md`
  - §10.1 stage_snapshot 维度章节加"结构性骨架 vs 情境维度"分层段（M2）。
  - §11.3a stage_catalog 维护表把 `snapshot_path` 拆 character / world 两行
    （character → `canon/...`，world → `world/...`）（M8）。
- `docs/architecture/extraction_workflow.md`
  - Phase 0 完成门控段重写为 `_chunk_passes_full_check` 四条判据 +
    `sys.exit(1)`（H1）。
  - Phase 1 出口验证段补"三件套齐全"为第 1 层校验，retry 预算覆盖
    `missing_files`；mark_done 前 defense-in-depth 描述（H2）。
- `automation/README.md`
  - "磁盘对账自愈"段加 partial / corrupt / schema-failing 回退规则（H1）。
  - L3 表行注明"LLM 调用失败 / 空响应 / 不可解析时不再视为 pass"（H3）。
- `prompts/review/手动补抽与修复.md`
  - 第 28 行把"标注 evidence_ref"改成"证据记录在外部修复日志，禁止写入
    schema 实例字段"（M6）。
- `ai_context/conventions.md`
  - §"Data Separation" stage_catalog 段拆 world / character 两行 +
    `snapshot_path` 差异说明（M8）。
- `ai_context/decisions.md`
  - #29 改为 "digest entries no separate stage_id; scene_archive entries
    DO carry stage_id (sourced from stage_plan.json) alongside scene_id"（M7）。
- `ai_context/current_status.md`
  - "What Exists / Gaps" 行 foundation 表述改成"foundation schema exists at
    schemas/world/foundation.schema.json (permissive); timeline / events /
    locations / maps still need directly writable schemas"（L3）。
- `ai_context/next_steps.md`
  - Highest Priority §1 同步 L3 描述。
- `docs/todo_list.md`
  - 新增 `T-CODEX-RATE-LIMIT`（Discussing）：CodexBackend 限额分类。
  - 新增 `T-PROMPT-SCHEMA-INJECT`（Discussing）：bounds-only schema-injection 路径选型。
  - 索引 Discussing 段从 6 条扩到 8 条，Total 10→12。

## 与计划的差异

- 计划：Cross-File Alignment 仅口头列出。实际：Step 7 复查后实补
  `automation/README.md` + `docs/architecture/extraction_workflow.md`
  两份文档的 Phase 0/1/L3 段同步——属于必须同步的连带文件，已落地。
- 计划：Cross-File Alignment 表中"Extraction workflow"行 docs 已对齐；
  `docs/architecture/data_model.md` / `simulation/retrieval/*` /
  `ai_context/architecture.md` 经子代理审计判定无 stale 文本，未改。
- 其它差异见上"执行偏差"段。

## 验证结果

- [x] `python -m py_compile` 全过 — `py_compile OK`。
- [x] imports 无 ImportError — orchestrator / progress / git_utils /
  llm_backend / scene_archive / post_processing / semantic 全部加载。
- [x] `jsonschema.Draft202012Validator.check_schema` 全部 35 个 schema 通过。
- [x] `_classify_rate_limit("Server returned 429 too many requests")` → True；
  `_classify_rate_limit("rate_limit hit")` → True；
  `_classify_rate_limit("connection refused")` → False。
- [x] `commit_stage` signature 含 `work_id`：参数列表
  `['project_root', 'stage_id', 'work_id', 'message', 'files']`；orchestrator
  五处 caller 已更新（`grep commit_stage` 全过）。
- [x] `memory_timeline_entry.schema.json.required` 含 `memory_importance` —
  Python 检查 True。
- [x] `decisions.md` #29 含 "scene_archive entries DO carry"。
- [x] `prompts/review/手动补抽与修复.md` 残留 `evidence_ref` 仅在"不要写入"
  上下文（grep -c 输出 1，正面引用为 0）。
- [x] `grep -rn "foundation schema still implicit" ai_context/` → 0。
- [x] `grep -rn 'schemas/{world,character}/stage_catalog' ai_context/` → 0。
- [x] `Phase0Progress.reconcile_with_disk` lazy-import 通过空目录 smoke：
  `{'reverted': 0, 'purged': 0}`。

## Completed
- **Status**: DONE
- **Finished**: 2026-04-30 11:30:47 EDT

<!-- /post-check 填写 -->

## 复查结论（对话里有完整报告）

### 轨 1 — 需求落实
- 落实率：13/13 项计划 + 11/11 项验证（全部 ✅）
- Missed updates: 0 条

### 轨 2 — 影响扩散
- Findings: High=0 / Medium=1 / Low=1
- Open Questions: 0 条
- 核心发现：commit_stage scope guard 不识别中文路径（与本项目 work_id 中文化直接相关）；`_classify_rate_limit` 扫 stdout 存在低概率误报。
- sub-agent 报的 Phase 3 extraction lane RateLimitHardStop 漏防是 false positive（无 enclosing except Exception，hard stop 自然透传）。

## 复查时状态
- **Reviewed**: 2026-04-30 11:50:00 EDT
- **Status**: REVIEWED-PARTIAL
  - 轨 1 全过，轨 2 1 条 Medium → PARTIAL（不是 PASS）
- **Conversation ref**: 同会话内 /post-check 输出
