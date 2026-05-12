# char_snapshot_sub_lanes

- **Started**: 2026-05-12 09:17:48 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

T-CHAR-SNAPSHOT-SUB-LANES（`docs/todo_list.md:21,377-676`，状态 🟢 High /
✅ Ready / 2026-05-12 修订）。Phase 3 单 stage 的 char_snapshot lane 是
当前 wall-time 最长的瓶颈。讨论方案：把单 char_snapshot lane 拆 3 个
并行 sub-lane（按字段聚类）→ 程序 merge → file-level repair_agent
（lifecycle 2 启动按 sub-lane 模式重新 extract）。schema 不动、世界
lane / char_support lane 不动、其他 phase 不动。

todo 已对齐前置工作（决策 #13 phase 3 keys==baseline 已落 +
checker `targets_keys_eq_baseline.py` 已注册 + 决策 #11f 四态已落
prompt §核心规则 #2 + 决策 #11e maxItems 裁剪已落 + 决策 #54
target_baseline 准入门槛已落），本 todo 仅做 sub-lane 拆分本身。

## 结论与决策

按 todo body §字段归属表 + §流程 实施。具体选择：

- **lane_states 粒度**：保持 `snapshot:{char_id}` 单 lane 标记不变；
  sub-lane 3 调用 + merge 在该 lane 闭包内完成。资源失败时整 lane 重
  跑（与 R3 ".partial 残留清理一律删" 一致）
- **partial 路径**：`works/{wid}/characters/{cid}/canon/stage_snapshots/.partial/{stage_id}_{lane}.json`
  （`.partial/` 目录与最终产物同父，方便 reconcile 扫描）
- **字段归属**（与 todo §字段归属表逐字一致）：
  - `char_expression` = voice_state / active_aliases / current_mood /
    failure_modes.tone_traps
  - `char_decision` = behavior_state / boundary_state / emotional_baseline /
    current_personality / current_status / stage_delta.{status_changes,
    mood_shift, personality_changes}
  - `char_cognition` = knowledge_scope / misunderstandings / concealments /
    relationships / relationship_state_summary / stage_events / character_arc /
    snapshot_summary / stage_delta.{trigger_events, relationship_changes,
    voice_shift} / failure_modes.{common_failures, relationship_traps,
    knowledge_leaks}
  - 程序注入 = schema_version / work_id / character_id / stage_id /
    stage_title / timeline_anchor / chapter_scope
- **merge 校验**（snapshot_merge.py 前置 hard gate，merge 失败即视为
  partial 失败 → 整 snapshot lane 失败）：
  1. 每 partial 顶层字段集合 == 字段归属表中该 lane 的分配（多/少都失败）
  2. failure_modes 4 子键互斥 across 2 lane（tone_traps 仅 expr / 其余
     3 子键仅 cog）+ 全 4 子键覆盖
  3. stage_delta 6 子键互斥 across 2 lane（dec / cog）+ 全 6 子键覆盖
     （S001 允许 stage_delta 整体不出现 — 此时 dec / cog 都不写入该顶层 key，
     都不出现则 merge 后 stage_delta 也不出现）
  4. 三方 keys（voice_state.target_voice_map / behavior_state.target_behavior_map
     / relationships）keys 集合相互相等且 == target_baseline.targets[].target_character_id
     — 复用现有 `automation/repair_agent/checkers/targets_keys_eq_baseline.py`
     做早期预检
  5. (D) drop entry 不被误判：merge 仅查字段集合互斥 + 全覆盖，**不查**
     partial entry 数 ≥ prev — 此规则由实现 + 文档双重明示
- **重抽路径（lifecycle 2 sub-lane 重抽）**：通过给 `FileRegenFixer` 加
  可选 `sub_lane_regen` 回调实现。当 char_snapshot 文件命中且回调存在
  → 走 3 sub-lane 并行 + 注入 prior_attempt_context + merge → 写盘
  + 写 file-level fingerprint。命中不到则回退默认全量 regen 路径。
  回调由 orchestrator 在构造 `_repair_cfg()` 时按 `char_snapshot_sub_lanes`
  开关绑定，通过 `coordinator.run` 新增 kwarg 透传到 `_build_fixers`。
  保留 repair_agent 内 lifecycle 计数与 T3_EXHAUSTED 终止语义不变（R1）
- **rate-limit / hard-stop**：sub-lane 走现有 `run_with_retry` 自然继承
  RateLimitController；hard-stop 时 sub-lane sub-executor 走
  `shutdown(cancel_futures=True)` + `RateLimitHardStop` 上抛到 phase 3
  外层 ThreadPool（R2）。lifecycle 槽计数不变（R1）
- **target_baseline read list 校准（来自 PRE 阶段发现的现状偏离）**：
  todo body 写"`target_baseline` 已通过 `_build_char_snapshot_read_list`
  写入 read list（phase 3 现状）"——**实际现状不是**：
  [prompt_builder.py:685-723](automation/persona_extraction/prompt_builder.py#L685-L723)
  只加 identity + prev snapshot + 源章节，没加 target_baseline。三 sub-lane
  都需要看见 baseline 的 target_character_id 集合来正确填三方 keys，本次
  把 baseline 加进 read list，视作"phase 3 现状校准"，**不**经过单独
  /go 流程（错误小、与本 todo 同源、ai_context 描述本就假设 baseline 是
  read list 一部分）

## 计划动作清单

新增文件：
- `automation/persona_extraction/snapshot_merge.py` — sub-lane partial 合并
  + 字段归属表（同一来源给 prompt + merge 用）+ merge 前置校验（字段集合
  互斥 + 全覆盖 + failure_modes / stage_delta 子键互斥 + 调用
  `targets_keys_eq_baseline` 预检 + 注入结构性字段 + 写 file-level
  fingerprint）

修改文件：
- `automation/prompt_templates/character_snapshot_extraction.md` — 头部加
  `{lane_scope}` / `{lane_field_whitelist}` 占位 + "本次仅写以下字段"
  约束段；保留 §核心规则 #2 (B/C/D 三态) 与 §maxItems 裁剪段不动
- `automation/persona_extraction/prompt_builder.py` —
  `build_char_snapshot_prompt` 增 `lane_scope: str = "ALL"` 入参；context
  注入 `{lane_scope}` / `{lane_field_whitelist}`；`_build_char_snapshot_read_list`
  加入 `target_baseline.json`（如上"校准"段所述）
- `automation/persona_extraction/orchestrator.py` — `_extract_char_snapshot`
  在 `char_snapshot_sub_lanes=true` 时走 3 sub-lane 并行 + merge 路径；
  hard-stop 取消同胞 sub-lane；构造 `_repair_cfg()` 时按开关绑定
  `sub_lane_regen` 回调透传到 `run_repair`
- `automation/persona_extraction/lane_output.py` — 暴露 partial 目录路径
  常量 / helper（merge / reconcile 共用）
- `automation/persona_extraction/progress.py` — `reconcile_with_disk` 扩展：
  当 snapshot lane 不完整（state ∈ intermediate / not in lane_states）
  时扫 `<canon>/stage_snapshots/.partial/{stage_id}_*.json` 一律删
- `automation/persona_extraction/config.py` — `Phase3Config.char_snapshot_sub_lanes: bool = True`
- `automation/config.toml` — `[phase3]` 段加 `char_snapshot_sub_lanes = true`
  + 注释
- `automation/persona_extraction/cli.py` — `--char-snapshot-sub-lanes` /
  `--no-char-snapshot-sub-lanes` argparse boolean flag pair，覆盖 toml；
  传入 `ExtractionOrchestrator`
- `automation/repair_agent/coordinator.py` — `run()` 增 kwarg
  `sub_lane_regen`；`_build_fixers` 接收 + 透传到 `FileRegenFixer`
- `automation/repair_agent/fixers/file_regen.py` — `FileRegenFixer` 增
  `sub_lane_regen` 字段；`fix()` 中若 callback 存在 + 文件路径匹配
  `characters/<cid>/canon/stage_snapshots/<sid>.json` → 调 callback
  得到新 content；callback 返回 None 则回退默认 regen
- `.gitignore` — `works/*/characters/*/canon/stage_snapshots/.partial/`

文档同步：
- `docs/architecture/extraction_workflow.md` §Phase 3 — 描述 sub-lane 拆分
  3 lane 并行 → merge → file-level repair_agent（lifecycle 2 重抽走
  sub-lane 模式）；保留 schema_reference / 决策 #11f / #13 描述不动
- `docs/requirements.md` §11 — 同步 phase 3 char_snapshot lane 拆分一段
- `automation/README.md` — Phase 3 说明 + `[phase3].char_snapshot_sub_lanes`
  toml 配置文档 + CLI 双向 flag
- `ai_context/architecture.md` §Automated Extraction Pipeline — 一句话
  补充 sub-lane 拆分
- `ai_context/decisions.md` — 新增决策（55）：char_snapshot sub-lane 拆分
  （字段归属表 + merge 校验 + file-level repair lifecycle 2 重抽走
  sub-lane 模式 + 单 toml bool + CLI 双向 flag，light_novel 由用户手切）
- `ai_context/conventions.md` — Cross-File Alignment 表新增一行映射
  `schemas/character/stage_snapshot.schema.json` 字段拆 sub-lane 时的同步
  目标（snapshot_merge.py + prompt template + ai_context/decisions.md），
  确保下次改 schema 时知道 sub-lane 归属也要更
- `docs/todo_list.md` — 把 T-CHAR-SNAPSHOT-SUB-LANES 整条移到
  `docs/todo_list_archived.md` 的 `## Completed` 段；刷新顶部 `## Index`

## 验证标准

- [ ] `python -c "from automation.persona_extraction import snapshot_merge,
      prompt_builder, orchestrator, progress, config, cli; from
      automation.repair_agent import coordinator; from
      automation.repair_agent.fixers import file_regen; print('ok')"`
      — 全部 import 无报错
- [ ] `python -c "from automation.persona_extraction.snapshot_merge import
      FIELD_ALLOCATION, merge_partials; print(sorted(FIELD_ALLOCATION))"`
      返回 ['char_cognition', 'char_decision', 'char_expression']
- [ ] snapshot_merge 单元 smoke：传入 3 合法 partial dict → 返回完整
      stage_snapshot dict，顶层 keys == schema 顶层 properties 全集
- [ ] snapshot_merge 字段越界 smoke：3 lane 中 char_decision 多写一个
      `voice_state` → merge 报字段集合互斥违规
- [ ] snapshot_merge failure_modes 子键覆盖 smoke：char_expression 漏
      tone_traps → merge 报失败；char_cognition 漏 common_failures →
      merge 报失败
- [ ] snapshot_merge stage_delta 子键覆盖 smoke：S001 路径 dec / cog
      partial 均不出现 stage_delta → merge 通过且结果不含 stage_delta
- [ ] snapshot_merge (D) drop 不误判 smoke：传入的 partial 中
      `misunderstandings` / `concealments` 条目数 < prev → merge 不报错
- [ ] `jsonschema` 校验 merge 输出 dict 通过
      `schemas/character/stage_snapshot.schema.json`
- [ ] 数据契约校验：本次未改 `schemas/`，跳过 schema 自身校验；merge
      输出 schema-validate 通过即等价
- [ ] config 端到端：toml 改值 → `get_config().phase3.char_snapshot_sub_lanes`
      变化；CLI flag 覆盖 toml
- [ ] grep `_build_char_snapshot_read_list` 输出含 target_baseline.json
- [ ] grep 文档残留：`旧 / legacy / 已废弃 / 原为` 在本次新增段落
      grep 结果为空
- [ ] grep 占位符遵守：本次改动文件不引入真实书名 / 角色名（含
      docs/ / ai_context/ / prompts/ / automation/prompt_templates/）

## 执行偏差

- **`timeline_anchor` 程序注入语义**：todo body 把 `timeline_anchor` 列入"程序注入"。schema 描述是"阶段时间锚点的短描述"——LLM 在单 lane 模式下手写。本次实现按 todo 决策注入 `stage_title[:50]`（语义略偏，作为 sub-lane 程序合并的可接受妥协，#55 已写明）。
- **`target_baseline` read list 校准**：todo body 第 545-546 行声称"`target_baseline` 已通过 `_build_char_snapshot_read_list` 写入 read list（phase 3 现状）"——实际现状不是。本次随 sub-lane 改动**把 `target_baseline.json` 加进 read list**（[prompt_builder.py:706-720](automation/persona_extraction/prompt_builder.py#L706-L720)），视作同源校准；如不补，3 sub-lane LLM 看不到 baseline keys 无法 by-construction 填三方 keys，导致每 stage 100% 进 merge fail → 整 lane 重跑，与 todo intent 抵触。
- **fingerprint 仅 compute + log，不持久化**：todo §改动清单声称 merge 成功后"写入 file-level fingerprint"。盘点 repair_agent 现状后发现 lifecycle 2 没有读取 file-level fingerprint 的消费点（既有 fingerprint 体系在 issue-level，由 `notes_writer.load_existing_fingerprints` 走 `extraction_notes/{stage_id}.jsonl`，与 file-level 是两回事）。本次实现 compute fingerprint + `logger.info` 记到 extraction log，但不写盘——若将来 lifecycle 2 真要按 file-level fingerprint 跳过重抽，需独立 todo 加 sidecar 元数据 + 消费点。
- **Review Step 7 风险线 finding 1 (RateLimitHardStop with-block 隐式 wait)**：保持现状，未单独修。理由：(1) Python `ThreadPoolExecutor.__exit__()` 的 `shutdown(wait=True)` 等待行为是 stdlib 默认；(2) 现有 phase 3 主 pool 同样形态，没单独处理；(3) `run_with_retry` 内的 `extraction_timeout_s = 3600s` 提供兜底（最坏等 1h，不是死锁）。如需更激进的退出，应在整个仓库统一处理而非本 todo 局部修。
- **Review Step 7 实现线 finding 9 (`lane_output.snapshot_partial_path` docstring)** / **结构线 全部 finding** / **规范线 全部 finding**：未发现需要修复的问题；review 全过。
- **Review Step 7 实现线 finding 4 (`_build_sub_lane_regen_callback` 类型注解 `list[Any]` → `list[RepairIssue]`)** / **风险线 finding 4 (baseline 缺失时加 logger.error)** / **风险线 finding 6 (fingerprint compute + log)**：本步内已修。

## 已落地变更

新增文件：
- [automation/persona_extraction/snapshot_merge.py](automation/persona_extraction/snapshot_merge.py)（新建，476 行）— 字段归属表 `FIELD_ALLOCATION` + `SHARED_KEY_SUBKEYS` + `merge_partials` + 5 道 hard gate + `compute_fingerprint` + `derive_chapter_scope` 辅助 + `lane_field_whitelist` / `lane_shared_subkeys` getter（prompt builder 复用）

修改文件：
- [automation/persona_extraction/orchestrator.py](automation/persona_extraction/orchestrator.py)
  - import 段：从 `lane_output` 增 `lane_product_path` / `snapshot_partial_dir` / `snapshot_partial_path`；新增 `from .snapshot_merge import ...`；新增 `from ..repair_agent.protocol import Issue as RepairIssue`
  - 模块级常量：`_SNAPSHOT_SCHEMA_VERSION = "1.0"` + `_SUB_LANE_PRIOR_CONTEXT_BUDGET = 600` + `_format_prior_attempt_context_block` helper
  - `ExtractionOrchestrator.__init__` 增 `char_snapshot_sub_lanes: bool | None = None` 入参；CLI 覆盖优先于 toml
  - 新增方法 `_run_char_snapshot_sub_lanes`（核心 sub-lane 并行 + merge + 写盘 + 清理）/ `_build_sub_lane_regen_callback`（lifecycle 2 T3 callback 工厂）/ `_clear_snapshot_partials`（partials 清理）/ `_load_baseline_keys`（D4 set-equal 输入源）
  - `_extract_char_snapshot` 闭包按 `self.char_snapshot_sub_lanes` 分流：开关开 → 3 sub-lane 并行；关 → 历史单 lane 路径不变
  - `_repair_one` 闭包之前增 `sub_lane_regen_cb` 构造逻辑；`run_repair` 调用增 `sub_lane_regen=sub_lane_regen_cb` kwarg
- [automation/persona_extraction/prompt_builder.py](automation/persona_extraction/prompt_builder.py)
  - `build_char_snapshot_prompt` 增 `lane_scope: str = "ALL"` 入参；context 注入 `{lane_scope}` / `{lane_scope_block}` / `{lane_field_whitelist}` / `{output_relative_path}` 四占位
  - 新增 `_render_lane_scope_block(lane_scope) -> (block, whitelist)`：ALL 模式返回空字符串对；sub-lane 模式渲染 markdown 表 + 硬约束说明段
  - `_build_char_snapshot_read_list` 加入 `target_baseline.json`（D4 anchor，#13）
- [automation/persona_extraction/progress.py](automation/persona_extraction/progress.py)
  - `reconcile_with_disk` 在每个非 COMMITTED stage 的 lane 校验之后，新增"R3 .partial 残留清理"段：snapshot lane 未 complete 时一律删 `.partial/{stage_id}_*.json`
- [automation/persona_extraction/config.py](automation/persona_extraction/config.py)
  - `Phase3Config` 加 `char_snapshot_sub_lanes: bool = True` 字段
- [automation/persona_extraction/cli.py](automation/persona_extraction/cli.py)
  - 新增 `--char-snapshot-sub-lanes` / `--no-char-snapshot-sub-lanes` 双向 flag（dest=`char_snapshot_sub_lanes`，默认 None=继承 toml）
  - `ExtractionOrchestrator(...)` 构造增 `char_snapshot_sub_lanes=args.char_snapshot_sub_lanes`
- [automation/persona_extraction/lane_output.py](automation/persona_extraction/lane_output.py)
  - 增 `SNAPSHOT_PARTIAL_DIRNAME = ".partial"` 常量 + `snapshot_partial_dir` / `snapshot_partial_path` helper
- [automation/repair_agent/coordinator.py](automation/repair_agent/coordinator.py)
  - `_build_fixers` 增 `sub_lane_regen` 入参，透传到 `FileRegenFixer`
  - `run()` 增 `sub_lane_regen` kwarg + docstring 说明
- [automation/repair_agent/fixers/file_regen.py](automation/repair_agent/fixers/file_regen.py)
  - 模块顶部加 `SubLaneRegenCallback` 类型别名 + `_CHAR_SNAPSHOT_PATH_RE` regex + `_parse_char_snapshot_path` helper
  - `FileRegenFixer.__init__` 加 `sub_lane_regen: SubLaneRegenCallback | None = None`
  - `fix()` 中按文件路径模式分流：char_snapshot 文件 + callback 存在 → 调 callback；其他文件 / 无 callback → 默认全量 regen 路径
- [automation/prompt_templates/character_snapshot_extraction.md](automation/prompt_templates/character_snapshot_extraction.md)
  - 任务卡段加 `lane_scope` 字段 + `{lane_scope_block}` 占位（ALL 模式渲染为空，无孤立 markdown）
  - 输出段把硬编码 `characters/{character_id}/canon/stage_snapshots/{stage_id}.json` 改为 `{output_relative_path}` 占位 + sub-lane 输出契约说明
- [automation/config.toml](automation/config.toml)
  - `[phase3]` 段加 `char_snapshot_sub_lanes = true` + 15 行注释（决策号 / CLI flag / light_novel 建议 / 字段归属表引用）
- [automation/README.md](automation/README.md)
  - `[phase3]` 配置文档段加 `char_snapshot_sub_lanes` 描述
- [.gitignore](.gitignore)
  - 加 `works/*/characters/*/canon/stage_snapshots/.partial/`
- [docs/architecture/extraction_workflow.md](docs/architecture/extraction_workflow.md)
  - §6.2 加 sub-lane 拆分 + 字段归属表 + merge hard gate 5 项 + lifecycle 2 重抽 + rate-limit / hard-stop / fallback / `.partial/` 路径段
  - §6.5 lane_states 粒度澄清（`snapshot:{char_id}` 单 lane 标记，sub-lane 在闭包内闭环）
- [docs/requirements.md](docs/requirements.md)
  - §9.3 加 char_snapshot 内部 sub-lane 拆分段
- [ai_context/architecture.md](ai_context/architecture.md)
  - Phase 3 bullet 末尾补 sub-lane 拆分长段（→ 决策 #55）
- [ai_context/decisions.md](ai_context/decisions.md)
  - 新增决策 #55（位于 #54 之后、`## Repository` 之前）
- [ai_context/conventions.md](ai_context/conventions.md)
  - Cross-File Alignment 表新增一行 `stage_snapshot.schema.json` → sub-lane 字段归属表同步行
- [docs/todo_list.md](docs/todo_list.md)
  - Index `🟡 Next` (3 → 2)：删 T-CHAR-SNAPSHOT-SUB-LANES 行 + Total 12 → 11
  - 正文删 T-CHAR-SNAPSHOT-SUB-LANES 整条（约 300 行）
- [docs/todo_list_archived.md](docs/todo_list_archived.md)
  - `## Completed` 段顶部新增 T-CHAR-SNAPSHOT-SUB-LANES 归档条目 + 关联 log 链接

## 与计划的差异

PRE 计划动作清单 vs 实际落地：

| 计划项 | 实际 | 备注 |
|---|---|---|
| 新增 `snapshot_merge.py` | ✅ | 名称、路径、内容与计划完全一致 |
| prompt template 加 `{lane_scope}` / `{lane_field_whitelist}` 占位 | ✅ + 增 `{lane_scope_block}` / `{output_relative_path}` | PRE 未列后两个占位，实施中发现需要：lane_scope_block 承载 "Sub-lane 字段范围（hard gate）" 整段说明，避免在模板里硬写后 ALL 模式留孤立 markdown；output_relative_path 让 sub-lane partial 写到 `.partial/` 子目录 |
| `build_char_snapshot_prompt` 增 `lane_scope` 入参 | ✅ | 与计划一致 |
| `_build_char_snapshot_read_list` 加 `target_baseline.json` | ✅ | 与"执行偏差"段第 2 项一致 |
| orchestrator sub-lane 调度 | ✅ | 实施细化：抽出 `_run_char_snapshot_sub_lanes` / `_build_sub_lane_regen_callback` / `_clear_snapshot_partials` / `_load_baseline_keys` 4 个新方法（PRE 没列方法名）|
| `repair_agent/coordinator.py` + `fixers/file_regen.py` 加 `sub_lane_regen` callback | ✅ | 协议 `SubLaneRegenCallback` 在 file_regen.py 顶部定义；callback 返回三态 `True/False/None`（PRE 未明示三态语义，实施时定义） |
| `progress.py reconcile` 扩展清理 `.partial` | ✅ | 与计划一致 |
| `config.py` + `config.toml` + cli.py | ✅ | 与计划一致 |
| `.gitignore` | ✅ | 与计划一致 |
| 文档同步 7 件套（架构 / 决策 / 需求 / README / conventions / extraction_workflow / todo_list） | ✅ | 全数同步；ai_context/conventions.md Cross-File Alignment 表新增一行（PRE 提及） |

## 验证结果

- [x] 全部 import smoke：`automation.persona_extraction.{snapshot_merge,prompt_builder,orchestrator,progress,config,cli,lane_output}` + `automation.repair_agent.{coordinator,fixers.file_regen}` 全部 import 无报错
- [x] `FIELD_ALLOCATION` keys 返回 `['char_cognition', 'char_decision', 'char_expression']`
- [x] snapshot_merge 单元 smoke 10 个全过：happy path / 字段越界 / failure_modes 双侧子键缺失 / stage_delta 双侧 omit（S001 路径）/ stage_delta 单侧 omit（mutex 违规）/ (D) drop entry 不被误判 / baseline mismatch / 跨结构 keys 不一致 / helpers
- [x] minimal-fixture merged stage_snapshot dict 通过 `jsonschema.Draft202012Validator(load_schema(stage_snapshot.schema.json))` 校验（20 顶层字段全覆盖）
- [x] 数据契约校验：本次未改 schema，merge 输出 schema-validate 通过即等价
- [x] config 端到端：`get_config().phase3.char_snapshot_sub_lanes is True`；toml 与 dataclass 默认一致；CLI `--no-char-snapshot-sub-lanes` 出现在 `--help`
- [x] `_build_char_snapshot_read_list` 源码含 `target_baseline.json` 字面
- [x] grep `旧 / legacy / 已废弃 / 原为` 在本次新增段落（snapshot_merge.py + character_snapshot_extraction.md sub-lane 段）残留 0
- [x] grep `<work_id> / Character A / Character B`（真实书名 / 角色名）在 ai_context / docs / 新增代码段落残留 0
- [x] `_render_lane_scope_block('ALL')` 返回 `('', '')`（ALL 模式不渲染 sub-lane block，避免 prompt 孤立 markdown）
- [x] `_render_lane_scope_block('char_expression')` 渲染含 'Sub-lane' 关键字 + 'voice_state' 字段名

⚪ 未在本次范围验证（留给下次 phase 3 启动 / 独立 todo）：

- sub_lanes=true 端到端跑通 1 stage：3 sub-lane 并行 LLM call + merge + file-level repair_agent 完整 lifecycle 1/2，需要真实 work 包 + LLM backend 配额（不属代码侧验证范围）
- sub_lanes=false fallback 跑通：`lane_scope=ALL` 等价单 lane，需要同上 runtime 环境验证
- lifecycle 2 T3 触发 → sub-lane 重抽 path：需要实测触发 T3 的 stage 内容；R1/R2/R3 在 rate-limit hard-stop 场景下的行为同上

## Completed
- **Status**: DONE
- **Finished**: 2026-05-12 10:30:41 EDT
