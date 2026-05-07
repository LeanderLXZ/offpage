**Review 模型**：Claude Opus 4.7 1M context（`claude-opus-4-7[1m]`）

# /full-review — 全仓库对齐审计 findings

扫描范围：`ai_context/` + `docs/` + `schemas/` + `prompts/` +
`automation/prompt_templates/` + `automation/persona_extraction/` +
`automation/repair_agent/` + `automation/ingestion/` + `simulation/` +
`works/` + `users/_template/` + `.gitignore` + `.claude/hooks/`。
配合 4 个 In Progress 待办（`T-BASELINE-DEPRECATE` /
`T-PHASE2-TARGET-BASELINE` / `T-INGEST-STRUCTURE-MODE` /
`T-PHASE0-CHUNK-SCHEMA-EXPAND`）的"代码完成、runtime 验证待跑"基线判定。

整体结论：**未发现 High 级问题**——四层（ai_context / docs /
schemas / 实现）的核心契约高度对齐。Medium 级 4 条偏脆弱点 / 半迁移残留 /
轻度文档失真；Low 级 4 条偏代码注释 / 死角 case。

---

## Findings

### High

无。最近 4 项 In Progress 待办的代码侧落地（dual-mode dispatch、
chunk-level secondary fields、target_baseline set-equal、length-tolerance
gate、recovery sweep）契约对齐良好——`structure_mode` 在
`work_manifest` / `works_manifest` schema 都强制 required + 无默认；
[chapter_summary_chunk.schema.json](schemas/analysis/chapter_summary_chunk.schema.json)
五个 chunk 二级字段就位且
[summarization.md](automation/prompt_templates/summarization.md) /
[analysis.md](automation/prompt_templates/analysis.md) /
[baseline_production.md](automation/prompt_templates/baseline_production.md)
LLM 教学完备；`targets_keys_eq_baseline` checker 在
[checkers/targets_keys_eq_baseline.py](automation/repair_agent/checkers/targets_keys_eq_baseline.py)
存在并接入 [coordinator.py](automation/repair_agent/coordinator.py) 第 2 层；
`validator.validate_with_length_tolerance`
（[validator.py:464](automation/persona_extraction/validator.py#L464)）
在 5 个 LLM 终点（`_summarize_chunk` / `run_analysis` /
`run_baseline_production` / `scene_archive._handle_validation_failure` /
coordinator T3_EXHAUSTED）全部接入；`_run_recovery_sweep`
（[orchestrator.py:477](automation/persona_extraction/orchestrator.py#L477)）
+ `ChunkEntry.recovery_attempted` + `LLMBackend.run(effort=...)` 链路完备。

### Medium

**M1. `Phase0Progress.chunk_size` 默认值仍是 25，与项目 default 20 漂移。**
[automation/persona_extraction/progress.py:250](automation/persona_extraction/progress.py#L250)
dataclass default `chunk_size: int = 25`，[progress.py:294](automation/persona_extraction/progress.py#L294)
`from_dict` fallback 同样 `chunk_size=data.get("chunk_size", 25)`。
而 decision #48（`ai_context/decisions.md:339`）已把项目默认从 25→20，
对应改动落到 [cli.py](automation/persona_extraction/cli.py) argparse +
[config.toml](automation/config.toml) +
[orchestrator.py](automation/persona_extraction/orchestrator.py) 的
`chunk_size: int = 20`，`progress.py` 漏改。
- **影响**：实际危险窗口小——`Phase0Progress` 实例由 orchestrator 构造
  时显式传入 `args.chunk_size`，已有的旧 progress JSON 也都把 `chunk_size`
  写在文件里，`get` fallback 走不到。但纯静态构造 `Phase0Progress()`
  + 后续序列化的代码路径会得到 25。属于半迁移状态——不致命，但违反
  "single-source default" 设计。
- **建议**：dataclass default + from_dict fallback 都改 25→20。

**M2. `migrate_baseline_to_stage_snapshot.py` 是孤立死代码。**
[automation/persona_extraction/migrate_baseline_to_stage_snapshot.py](automation/persona_extraction/migrate_baseline_to_stage_snapshot.py)
（215 行）只在 git change_logs / 自身 docstring 出现（`grep` 全仓库 `-r`
结果），无任何 import / CLI 子命令 / orchestrator 调用。T-BASELINE-DEPRECATE
已标 "代码完成"——4 piece 文件已从 schemas/ 删除，stage_snapshot 已内联
失效模式。脚本作为一次性手工修复工具仍可手动跑（`python -m
automation.persona_extraction.migrate_baseline_to_stage_snapshot --apply`），
但仓库无任何位置说明"这是一次性 utility，本仓库 main 上无作品需要迁移，
保留只为给老作品 extraction 分支提供"。
- **影响**：违反项目 "no legacy" 风格约束——
  [conventions.md §Generic Placeholders](ai_context/conventions.md)
  禁 "legacy / deprecated / formerly / renamed from" 历史叙述，
  脚本中文 docstring 处明写 "deprecated baseline files"。新 AI agent
  阅读仓库时容易把它当"在用代码"误读，搞不清是死代码还是 in-flight。
- **建议**：要么显式删除（main 无作品需要迁移），要么在文件顶部加
  "这是一次性 utility，main 上无作品；只在新加入的旧
  extraction/<work_id> 分支上手动跑过一次"声明。

**M3. `repair_agent/checkers/schema.py` 用 `Draft7Validator`，但 schemas
声明 `$schema: draft/2020-12/schema`。**
[automation/repair_agent/checkers/schema.py:51](automation/repair_agent/checkers/schema.py#L51)
`validator = _jsonschema.Draft7Validator(schema)`；其它所有 validation
点（[orchestrator.py:80-144](automation/persona_extraction/orchestrator.py#L80-L144)
+ [validator.py:488,508](automation/persona_extraction/validator.py#L488)
+ [scene_archive.py:49](automation/persona_extraction/scene_archive.py#L49)）
都用 `Draft202012Validator`。
[schema_loader.py](automation/persona_extraction/schema_loader.py) 第 10–22
行 docstring 显式承认"keep both paths working without forking"——通过 inline
$ref 让任何 draft validator 都能消费。设计初衷是兼容，但合约脆弱：
- 当前 `schemas/` 全仓库 grep `unevaluatedProperties` /
  `prefixItems` / `dependentRequired` / `dependentSchemas` / `$defs` 全部
  无命中，所以**实际现状无 bug**。
- 但任何未来 schema 作者引入 2020-12-only 关键字（例如用
  `unevaluatedProperties: false` 做严格约束）就会**静默**丢失在
  repair_agent 的 L1 schema 检查里——orchestrator 端拒绝、repair_agent
  端通过，两个 gate 分歧。
- **影响**：latent fragility，今天无即时危害。
- **建议**：要么把 repair_agent 升到 `Draft202012Validator`（schema_loader
  inline 已让 $ref 解析无需 `referencing`），要么加单测断言"所有 schemas
  通过两种 validator 检查行为等价"。前者更彻底。

**M4. `ai_context/current_status.md:36` 关于 world schemas 的状态描述失真。**
原文：「World schemas partially formal: `foundation` schema exists at
`schemas/world/foundation.schema.json` (permissive); timeline / events /
locations / maps still need directly writable schemas」。
`ls schemas/world/` 实际有 6 个 schema：foundation /
fixed_relationships / world_stage_snapshot / world_stage_catalog /
world_event_digest_entry / world_manifest——`world_stage_snapshot`
已带 stage_events / character_status_changes 等正式字段
（decision #27h）；`world_event_digest_entry` 即"events"的合法
schema；timeline 信息走 `timeline_anchor` 内联（decision #27c
"No schema carries `evidence_refs`/`source_type`/`scene_refs`. Chapter
back-tracing lives outside the schemas; runtime anchoring uses
`timeline_anchor`"）已是当前设计，不再有"独立 timeline schema"
的需求。
- **影响**：误导后续 agent 误以为 timeline / events / locations / maps
  schema 仍是 next_steps 高优先级——而 `next_steps.md:17-19` 也复述了
  类似内容。两份 ai_context 同时滞后于 schemas/world 的实际状态。
- **建议**：current_status.md L36 改成 "World schemas formal:
  foundation / fixed_relationships / world_stage_snapshot /
  world_stage_catalog / world_event_digest_entry / world_manifest 均有
  正式 schema；timeline / locations 信息内联于 stage_snapshot 与
  foundation 而非独立 schema（详见 decision #27c）"；
  `next_steps.md:17-19` 同步删除"timeline/events/locations/maps
  schema"高优先级条目（或换成更具体的下一步，如运行时 retrieval 实装）。

### Low

**L1. `automation/prompt_templates/character_support_extraction.md:112`
使用 "已废弃" 历史叙述措辞。**
原文：「不要重新创建已废弃的 voice_rules / behavior_rules / boundaries /
…」。同文件 [character_snapshot_extraction.md:30](automation/prompt_templates/character_snapshot_extraction.md#L30)
"没有独立的 voice_rules / …" 描述当前现状，OK；但 "已废弃"
属于 [conventions.md §Generic Placeholders](ai_context/conventions.md)
明禁的 "deprecated / formerly" 历史叙述，且约束适用范围
**包含 `automation/prompt_templates/`**。
- **建议**：改成"不要新建独立的 voice_rules / behavior_rules /
  boundaries / failure_modes 文件，写到 stage_snapshot 内联即可"。

**L2. `_run_recovery_sweep` 沿用同一 1800s subprocess 墙时预算，effort
降级不能救墙时类失败。**
[orchestrator.py:477-560](automation/persona_extraction/orchestrator.py#L477)
recovery sweep 把 `effort='high'` 透传给 `_summarize_chunk`，
但 `_summarize_chunk` 的 subprocess wall budget 取自
`[phase0].summarize_timeout_s = 1800s`，未在 sweep 路径覆写。
decision #49 经验数据 "effort=high 实测 ~14 min"——但若新作品出现
非 effort 引发的 1800s 真实挂死（agent loop 卡死、tool hang），
sweep 会再撞同一墙。属于 design tradeoff（#49 只承诺"effort 抖动"
类救火，未承诺墙时类），不是 bug。
- **建议**：要么文档中显式写明"recovery sweep 不解决墙时挂死"
  （读者预期管理），要么 `[phase0].recovery_timeout_s` 单独配
  （例如 2400s 给 sweep），把 effort 降级 + 时间放宽两条手段
  组合。

**L3. `_run_recovery_sweep` 中 `recovery_attempted=True` 设定与磁盘持
久化非原子。**
[orchestrator.py:556-560](automation/persona_extraction/orchestrator.py#L556)
`entry.recovery_attempted = True` 在 `phase0.save()` 之前。SIGKILL
落在两者之间会让内存对象 dirty 但磁盘没刷——当然 SIGKILL 后
内存丢，下次 resume 从磁盘读 `recovery_attempted=False`，所以
其实**反而更安全**：sweep 会再跑一次（不 skip）。但若是 process
crash 后内存 still 反映到了某个共享 future 而 progress JSON
没更新（_summarize_chunk 直接修改 entry 引用），可能出现"日志看到 sweep
跑过但磁盘说没跑过"的诊断混乱。
- **建议**：sweep 完后统一一次 `phase0.save()`（已是当前行为）；
  风险窗口小，可不修，但工程上明确 `mark + save` 同步性更鲁棒。

**L4. `_build_light_novel_stage_plan` 缺空 `chapter_index` 防御。**
[orchestrator.py:1109-1150](automation/persona_extraction/orchestrator.py#L1109)
对 `chapter_index` 为空数组的退化输入未在源头早抛——后续 Phase 1
schema gate（`stage_plan.minItems`）会把它兜下来，但报错落在 LLM
retry 路径，浪费一次 retry slot 才得到清楚的失败原因。
- **建议**：函数入口 assert `len(chapter_index) > 0`，明确"原始资料
  规范化阶段已该拒绝空 ToC 的输入"——或在
  `automation/ingestion/validator.py` 兜下游。

---

## Open Questions / Ambiguities

**Q1. Repair 发生在 commit 之后的回滚契约。**
Decision #11.4 + architecture.md "commit-ordering contract (commit first;
non-empty SHA → COMMITTED; empty → FAILED)" 锁了正向流程，但若 phase
3.5 cross-stage consistency 在 commit 之后才发现违规，`consistency_report`
会写入但 stage 已 COMMITTED——文档说 "errors block Phase 4"
（不 rollback 已 commit 的 stage）。这是设计意图还是漏覆盖？仓库无
明确文字说"已 committed stage 的违规手动回滚"，
建议 ai_context/decisions.md 加一条 ADR 锁定语义。

**Q2. Length-tolerance gate 与 strict 下游消费之间的"宽进严出"耦合。**
Phase 0 chunk 通过 tolerance gate 但实际字数离 minLength 还差几个字符
（合法 ×0.9 floor）→ Phase 1 LLM 读这个 chunk 合成 world_overview，
合成结果严格走 `Draft202012Validator`。若 Phase 1 LLM 输出某个字段
近 schema bound 抖动恰好被 Phase 0 tolerance pass 的"短"信号拉低，
是否存在级联放大？无法仅静态判断，需要 runtime 数据。当前
4 项 In Progress "代码完成、runtime 验证待跑"全靠这次 runtime 才能
回答。

**Q3. `migrate_baseline_to_stage_snapshot.py` 的归宿。**
保留还是删除——本审计无法独自决定（涉及"是否还有非
main 上的旧作品需要迁移"）。建议用户决定，记录到 ai_context。

---

## Alignment Summary

| 层 | 对齐度 | 备注 |
|---|---|---|
| `ai_context/` ↔ `docs/` ↔ `schemas/` ↔ 实现 | 强 | 4 项 In Progress 待办的核心契约（dual-mode、target_baseline set-equal、chunk-level fields、length tolerance、recovery sweep）四层一致 |
| `ai_context/conventions.md §Cross-File Alignment` 表 | 强 | 表内每行点名的文件实际 grep 都能找到对应 anchor |
| 文档 vs 当前 schemas/world/ 实际状态 | 中 | M4——current_status.md + next_steps.md 还在说 "world schemas 缺 timeline/events/locations" |
| 提示模板 vs 当前 schema 字段 | 强 | 5 个 chunk 二级字段在 summarization/analysis/baseline_production prompt 全教学 |
| `works/` main 治理 | 强 | git ls-files 只命中 `works/README.md`，本地工作产物 ignored |
| `users/_template/` vs schemas/user | 强 | 无 4-piece 残留，profile.json + role_binding.json + relationship_core/ 与当前 schema 一致 |
| schema validator 一致性 | 中 | M3——repair_agent Draft7 vs 其它 Draft 2020-12，靠 schema_loader inline $ref 兜，latent fragility |
| 死代码治理 | 中 | M2——`migrate_baseline_to_stage_snapshot.py` 孤立 |
| Default 值单源 | 中 | M1——`Phase0Progress.chunk_size` 25→20 漂移 |
| Prompt 历史叙述合规 | 弱-中 | L1——"已废弃" 一处 |

---

## Residual Risks

1. **M3 (Draft7 vs 2020-12) 是 latent regression risk。** 今天无 schema
   用 2020-12-only 关键字，所以无 bug；但下次 schema tightening 写
   `unevaluatedProperties: false` 一刻就静默回归——repair_agent gate
   不报错、orchestrator gate 拒绝、`/post-check` 也不一定逮到。
2. **4 项 In Progress 的"代码完成、runtime 验证待跑"未解封。** 静态
   gate（schema metaschema、unit case、smoke test、import 检查）已全
   过，但 LLM 输出的真实端到端耦合（chunk 二级字段被 Phase 1 LLM 实际
   消费、target_baseline 被 Phase 3 LLM 实际严守 keys、length-tolerance
   在真实抖动场景的频率）只能 runtime 复现。无法仅静态判定四项是否
   全部就绪。
3. **`extraction_worker_mode` 旁路在 [llm_backend.py:281](automation/persona_extraction/llm_backend.py#L281)
   通过 `--append-system-prompt` 注入；该机制依赖 Claude CLI 的具体
   行为**（CLAUDE.md 顶部"Worker-Mode Short-Circuit"约定一旦标记出现
   就跳过 ai_context 加载）。Codex backend 本机无 CLI 实测
   （T-CODEX-STDIN / T-CODEX-RATE-LIMIT 在 Discussing 段），切到
   codex 端时此契约是否一致未知。
4. **Recovery sweep + max_turns=80 + length-tolerance 三件套是较激进
   的 leniency 组合。** 设计意图是"strict 跑到 exhaustion 再兜底"，
   但 audit 视角看：若上游 LLM 输出有系统性瑕疵（不是抖动），这套组
   合会"看起来通过"但产物质量下降。runtime 验证后回头看
   `_validation_tolerance_applied` 频率非常关键（目前刻意不留
   metadata marker，决策 #48 已说明），但建议至少把 tolerance pass
   的次数 / 文件 ID 写到 logs/extraction_logs/ 便于事后审计——目前
   静态读代码没看到这个 logging。

---

## 建议落地顺序

1. **M1 5 分钟 fix**：`progress.py` 两处 25→20。
2. **M4 5 分钟 fix**：`current_status.md:36` + `next_steps.md:17-19`
   关于 world schemas 的描述同步到当前 schemas/world 实际状态。
3. **L1 5 分钟 fix**：`character_support_extraction.md:112` "已废弃"
   改为现状描述。
4. **M2**：用户决定 `migrate_baseline_to_stage_snapshot.py` 留 / 删；
   留则在文件顶部加"一次性 utility，main 无作品需要迁移"声明。
5. **M3**：升 repair_agent 到 `Draft202012Validator`，做一次回归
   smoke（_smoke_l3_gate 4 场景 + _smoke_recovery_sweep 4 场景 +
   _smoke_triage 全过）；或加跨 validator 等价单测。
6. **L4 / L2 / L3 / Q1 / Q2 / Q3** 等 runtime 验证之后联动判断
   （runtime gate 跑出真实数据后再回头评 priority）。

---

**重点检查项过审**（无 finding 但已检查的项目）：
`works/` main 上仅 `README.md` tracked（`git ls-files works/`）；
`users/_template/` 无 4-piece 残留；`.claude/hooks/session_branch_check.sh`
存在；`simulation/` 0 个 `.py` 文件（current_status.md 第 33 行
"No simulation-engine service implementation" 准确）；`schemas/` 33 个
`.schema.json` 全部 valid；`schemas/character/target_baseline.schema.json:31`
正确通过 `$ref: targets_cap.schema.json` 共享 maxItems；
`automation/repair_agent/checkers/targets_keys_eq_baseline.py` 实现
完整且接入 coordinator.py 第 2 层；prompt template 五个 chunk 二级
字段教学完整；schema-gate-as-retry-trigger 5 schema 全接入；
length-tolerance 5 终点全接入；recovery sweep 全链路完整。
