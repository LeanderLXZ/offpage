**Review 模型**：Claude Opus 4.7（`claude-opus-4-7`）

**Scope**: `/full-review` 全仓库审计。三条并行审计线：规范线（`ai_context/` / `docs/` / `schemas/` / `prompts/`）、实现线（`automation/` / `repair_agent/`）、样例产物线（`works/` / `users/` / gitignore vs 实况）。

**审计基准**：主分支 `master` at HEAD = `05f2d0f`，以及 `extraction/我和女帝的九世孽缘` HEAD = `e140f5d`。

---

## 1. Findings

### High

#### H1 — `phase3_stages.json` 与 `pipeline.json` / `ai_context/` 三方不一致（数据与叙述严重漂移）
- **结论**：
  - [pipeline.json](works/我和女帝的九世孽缘/analysis/progress/pipeline.json) 声明 `phase_3: "pending"` / `phase_4: "done"` / `last_updated: 2026-04-18T09:00:19+00:00`
  - [phase3_stages.json](works/我和女帝的九世孽缘/analysis/progress/phase3_stages.json) 显示 S001 = `committed`（SHA `3bf25bf`，`last_updated: 2026-04-22T23:30:06+00:00`），S002 = `error`（error_message "Working tree has uncommitted changes"），S003–S049 = `pending`
  - 提取分支 HEAD 确实包含 commit `3bf25bf "S001: 分层提取完成"`（2026-04-22 19:30 -0400），含 2 个角色 + world 的完整 S001 产物（5 条 lane 全 complete）
  - [ai_context/current_status.md:5-9](ai_context/current_status.md#L5-L9) 与 [ai_context/next_steps.md:5-13](ai_context/next_steps.md#L5-L13) 仍写"Phase 3 reset to fresh start — all 49 stages pending after 2026-04-20 rollback"
- **为什么是问题**：三个不同文件对"Phase 3 当前位置"给出三个互不相容的答案。pipeline.json 仍是 2026-04-21 回滚之前的状态（日期 04-18 早于 04-21 回滚日志），phase3_stages.json 反映的是 2026-04-22 的 S001 重跑，ai_context 则停留在"回滚后全部待做"。
- **影响范围**：
  - 任何只读 pipeline.json 的代码（若存在）会错误地认为 Phase 3 完全未开始
  - 下一个 AI 会话按 ai_context/ 信任"49 阶段全 pending"，做决策时会低估已投入的提取成本（S001 已完成）
  - S002 "working tree 有未提交改动" 的 error_message 提示回滚/重跑期间 git 状态异常，未被任何 log 记录
  - `pipeline.json` 中"phase_4: done"与 S001 之后 Phase 4 是否重跑无法核验（`retrieval/scene_archive.jsonl` 有 1236 行但 mtime 无法反推是否包含新 S001 场景）
- **证据**：
  - [works/我和女帝的九世孽缘/analysis/progress/pipeline.json](works/我和女帝的九世孽缘/analysis/progress/pipeline.json)
  - [works/我和女帝的九世孽缘/analysis/progress/phase3_stages.json](works/我和女帝的九世孽缘/analysis/progress/phase3_stages.json) 行 4–35（S001 + S002）
  - [ai_context/current_status.md:5-9](ai_context/current_status.md#L5-L9)
  - [ai_context/next_steps.md:5-13](ai_context/next_steps.md#L5-L13)
  - `git log extraction/我和女帝的九世孽缘 --oneline | grep S001` → `3bf25bf S001: 分层提取完成`
  - `docs/logs/` 下没有 2026-04-22 S001 重跑的日志条目；最接近的是 2026-04-21 `rollback_phase3_to_phase_2_5.md`
- **类型**：冲突（数据漂移）。必须选一个为"真相"：`phase3_stages.json` 是权威（由 orchestrator 维护），其余两方应立即同步。

#### H2 — 缺 3 份关键 schema：`foundation.json` / `scene_archive` / `load_profiles.json`
- **结论**：
  1. `foundation.json`：文档 8 处（requirements/architecture/data_model/extraction_workflow/startup_load）都把它列为 Phase 2.5 产出 + Tier 0 运行时加载的基础设定，但 `schemas/world/` 没有 `foundation.schema.json`。已在 extraction 分支 `works/我和女帝的九世孽缘/world/foundation/foundation.json` 落盘但无任何 schema gate。
  2. `scene_archive` 条目：`data_model.md:136-141` 明确给出字段（scene_id/stage_id/chapter/time/location/characters_present/summary/full_text），`retrieval/scene_archive.jsonl` 是检索核心 + Phase 4 产出，仍无 schema。
  3. `load_profiles.json`：至少 3 处文档（[ai_context/requirements.md:239-240](ai_context/requirements.md#L239-L240)、[simulation/retrieval/load_strategy.md:69-71](simulation/retrieval/load_strategy.md#L69-L71)、[simulation/retrieval/load_strategy.md:201](simulation/retrieval/load_strategy.md#L201)）承诺 per-work 可覆盖 `scene_fulltext_window` 等参数，但无 schema、无代码加载器、无默认模板。
- **为什么是问题**：运行时加载（startup_load）、Phase 4 输出、per-work 配置三者都依赖这些结构，缺 schema 意味着 validator / consistency_checker 不能 gate，也意味着未来 AI agent 在"写"这些结构时没有契约可循。
- **影响范围**：Phase 2.5 基线验证、Phase 4 输出验证、未来 simulation 启动器实现。
- **证据**：`ls schemas/world/` 仅 5 个文件（见 §Evidence）；`ls schemas/work/` 无 `load_profiles.schema.json`。
- **类型**：缺失（承诺未兑现）。

#### H3 — 提交顺序契约存在"git commit 已落盘但 progress 未保存"窗口
- **结论**：[orchestrator.py:1795-1815](automation/persona_extraction/orchestrator.py#L1795-L1815) 先 `sha = commit_stage(...)`（行 1795，git 实际落盘），再在内存中 `stage.committed_sha = sha` / `transition(COMMITTED)`（行 1810-1814），最后 `phase3.save(self.project_root)`（行 1815）才写 `phase3_stages.json`。若进程在 1795 成功返回后、1815 执行前崩溃（SIGKILL、OOM、断电），git 已经有该提交但 `phase3_stages.json` 中该 stage 仍停在 `PASSED`、`committed_sha = ""`。
- **为什么是问题**：
  - `progress.reconcile_with_disk()` 的 `git cat-file -e committed_sha` 校验**只有当 committed_sha 非空时**才生效。此场景下 committed_sha 为空 → reconcile 走"terminal but missing → PENDING"分支 → 下一次 `--resume` 重新做 post-processing + repair_agent + 再次 `commit_stage`。
  - 若重跑产物与原提交**完全一致**（纯 post-processing 幂等），`git commit` 返回空 SHA → FAILED，后续 `--resume` 再次尝试，直到操作员手动 reconcile。
  - 若重跑产物与原提交**有微小差异**（例如 timestamp 差异、非幂等字段），会形成**重复的 Phase 3 提交**，破坏 squash-merge 的提交历史假设。
- **备注**：子 agent 最初标为 "CRITICAL" 并附"crash 在 1810-1814 之间会写入 PASSED+committed_sha 不一致状态"，经复核**该描述不成立**（`save()` 在行 1815，此前的内存赋值不会落盘）。真正的风险是"commit 已落盘但 progress 未保存"这个时间窗，严重性应降级为 MEDIUM–HIGH。
- **影响范围**：SIGKILL / OOM / 断电场景；常规运行不触发。
- **证据**：[automation/persona_extraction/orchestrator.py:1790-1815](automation/persona_extraction/orchestrator.py#L1790-L1815)；[automation/persona_extraction/progress.py:581-676](automation/persona_extraction/progress.py#L581-L676) reconcile 逻辑对 committed_sha="" 的处理。
- **类型**：原子性风险。
- **可选缓解**：`commit_stage()` 成功后先 `phase3.save()` 写入"committed but not yet transitioned"中间态，或把 commit message 中嵌入 `stage_id` 让 reconcile 能从 git log 反查 SHA。

#### H4 — 世界 stage_snapshot `stage_events` 缺 `maxItems`（硬 gate 缺一半）
- **结论**：[schemas/character/stage_snapshot.schema.json](schemas/character/stage_snapshot.schema.json) 在 `stage_events` 上有 `"maxItems": 10`（行 116 等），而 [schemas/world/world_stage_snapshot.schema.json](schemas/world/world_stage_snapshot.schema.json) 的 `stage_events` 声明中**完全没有** `maxItems` / `minItems` 约束。`relationship_shifts` 同样未加 `maxItems: 10`。
- **为什么是问题**：[docs/requirements.md:80](docs/requirements.md#L80) 与 [docs/requirements.md:991](docs/requirements.md#L991) 把 `stage_events ≤ 10` 写成硬 gate，条目长度 50–80 字也写成硬 gate；但世界侧的 schema 只能 gate 字段长度（若 pattern 已加），无法 gate 条目数量。
- **影响范围**：world stage 产物可能超过 10 条事件而不被 validator/repair_agent 拦截，污染下游 world_event_digest。
- **证据**：`grep '"maxItems"' schemas/world/world_stage_snapshot.schema.json` → 无输出；character schema 中 `maxItems: 10` 出现 4 次。

---

### Medium

#### M1 — `fail_source` 字段在 `ERROR → PENDING` 重置时不清空
- **结论**：[automation/persona_extraction/orchestrator.py:1183-1192](automation/persona_extraction/orchestrator.py#L1183-L1192) 在 `--resume` 自动重置 ERROR → PENDING 时，清空了 `error_message` 与 `last_reviewer_feedback`，但没有清空 `fail_source`。对照 [progress.py:379-392](automation/persona_extraction/progress.py#L379-L392) 的 `force_reset_to_pending()`，它清空 `error_message` 但同样不清 `fail_source`。
- **为什么是问题**：`fail_source` 旨在记录"最近一次失败来源于哪条 lane / 哪一环"（见 phase3_stages.json 结构）。若前一次失败把它设为 `support:王枫`，重置到 PENDING 后这个遗留值会在下次运行时误导观察者，也可能影响决定性 branching 逻辑（如果有 lane-level 优先级规则读它）。
- **影响范围**：运维可见性（中等），若将来代码基于 fail_source 做调度决策则会升级。
- **证据**：`grep fail_source automation/persona_extraction/progress.py automation/persona_extraction/orchestrator.py`。
- **类型**：bug（小）/ 审计可见性。

#### M2 — Triage 反作弊"字符级 substring"对短引用形同虚设
- **结论**：[automation/repair_agent/triage.py:453](automation/repair_agent/triage.py#L453) 的 `_verify_quote` 实现是 `chapter_text.find(v.quote) >= 0`，即纯字符串 `find`。无最短长度校验，无词边界，无"引用行号反查是否自洽"校验；SHA-256 anchoring 是另一套机制，不影响这里。
- **为什么是问题**：[decisions.md:§25a](ai_context/decisions.md) 承诺 "anti-cheat is program-enforced: every accepted verdict must cite chapter + line range + verbatim quote; the program verifies the quote is a literal chapter substring"。若 LLM 故意或无意返回极短引用（如单字"他"/"的"/"是"），程序会接受。`coverage_shortage` 的 0-token 合成引用从首章首行取（[triage.py:306-320](automation/repair_agent/triage.py#L306-L320)），也可能是极短字符串。
- **影响范围**：accept_with_notes 的审计可信度。实际上 triage prompt 多半会要求长引用，但程序没有兜底。
- **证据**：同上文件行号。
- **建议**：加最短长度（如 ≥10 字符）+ `find` 结果与 `line_range` 一致性交叉校验。

#### M3 — L3 Gate 的"连续两次相同阻塞集 → 不收敛"判定在 gate 偶尔不触发时可能错位
- **结论**：[automation/repair_agent/coordinator.py:298](automation/repair_agent/coordinator.py#L298) 只在 gate 实际运行时 `record_l3_gate()`；[tracker.py:91-101](automation/repair_agent/tracker.py#L91-L101) `is_l3_gate_reemerge()` 在每轮无条件检查 `history[-1] == history[-2]`。当某轮"修改文件集为空"或 `l3_gate_enabled` 临时关闭时，gate 不写入 history；下一轮写入的 history[-1] 与 history[-2] 之间并非"相邻轮次"。
- **为什么是问题**：convergence 检测的语义是"相邻两轮相同 → 卡住"。跨越未运行轮的比较会给出误收敛 / 误不收敛信号。
- **影响范围**：小概率；在 l3_gate_enabled 稳定的正常运行中不触发。
- **证据**：同上文件行号。
- **类型**：逻辑风险 / 边界情况。

#### M4 — config.toml 未知键静默丢弃（typo 无感失败）
- **结论**：[automation/persona_extraction/config.py:189-210](automation/persona_extraction/config.py#L189-L210) `_coerce_to_dataclass()` 对未知键只 `logger.warning(...)` 然后跳过，没有 raise。运维把 `t3_max_per_file` 误写为 `t3_max_per_files` 或 `t3_file_max` 时，默认值静默生效。
- **为什么是问题**：本项目的 config.toml 是单一真相源，单个 typo 可以让整个修复循环用错误阈值跑数小时。
- **影响范围**：运维体验（严重程度取决于是否以严格 CI 验证 config）。
- **证据**：同上文件行号。
- **建议**：严格模式 `strict_config = true` 时 raise；默认至少用 `logger.error` 而非 warning。

#### M5 — `memory_digest` 去重时静默丢弃同 `memory_id` 重复项
- **结论**：[automation/persona_extraction/post_processing.py:150-157](automation/persona_extraction/post_processing.py#L150-L157) 在生成 `memory_digest.jsonl` 时，用 `memory_id` 去重，发现重复只保留首条，无 log、无 warning。
- **为什么是问题**：LLM 若产出重复 `memory_id`，应当是 schema 错误（被 L1 schema check 拦截），但如果 repair agent 的 T3 regen 误产生同 ID，静默去重会掩盖 bug；运维看不到告警。
- **影响范围**：数据完整性（低概率）+ 可观测性（中等）。
- **证据**：同上文件行号。

#### M6 — `consistency_checker` 对 `aliases` 条目类型未做 `isinstance(alias, dict)` 防御
- **结论**：[automation/persona_extraction/consistency_checker.py:239-247](automation/persona_extraction/consistency_checker.py#L239-L247) 直接 `alias.get("name")`，假设 `alias` 是 dict。
- **为什么是问题**：虽然 Phase 2.5 validator 理论上 gate 住了，但如果校验器本身失效 / baseline 被手工编辑，这里会 AttributeError 崩溃而不是给出友好错误。consistency_checker 本身被 architecture 宣称是"最终防线"。
- **影响范围**：防御性编码不足；实际触发概率低。
- **证据**：同上文件行号。

#### M7 — 缺少 S001 重跑日志（docs/logs/ 空缺）+ repair 成本/重试轨迹未归档
- **结论**：从 2026-04-21 `rollback_phase3_to_phase_2_5.md` 到 2026-04-22 S001 commit `3bf25bf`，`docs/logs/` 无任何关于该次提取的叙事条目。orchestrator 目前只写 `phase3_stages.json`（状态）+ `failed_lanes/*.log`（失败诊断），不自动写 `docs/logs/` 条目。
- **为什么是问题**：`ai_context/instructions.md` Layer summary 明确 `docs/logs/` = "timestamped historical records"，且 conventions.md "每个 meaningful change → write a log"。自动化执行的 stage 完成按惯例应留一条，至少记录：提取耗时、repair 轮次、triage 接受数、T3 用量。现在这些数据只能从 failed_lanes 反推（失败者）+ git commit（成功者）。
- **影响范围**：当前阶段运维可追溯性缺一块；正常继续提取无技术阻塞。
- **证据**：`ls docs/logs/ | grep 2026-04-22` → 仅 `2026-04-22_172317_extract_next_steps_reset.md`（非提取完成日志）。

#### M8 — `target_type` 字段无 enum/pattern，运行时过滤靠字符串匹配猜
- **结论**：[schemas/character/stage_snapshot.schema.json](schemas/character/stage_snapshot.schema.json) 中 `target_voice_map[].target_type` 仅 `{"type": "string"}`，无 enum 也无 pattern。docs 示例给出"角色A（真面目）"、"角色B"、"系统"、"村民"等五花八门的格式。
- **为什么是问题**：[architecture.md:102-107](ai_context/architecture.md#L102-L107) 承诺"`target_voice_map` / `target_behavior_map` loaded only for entries matching the user's role (canon = exact, OC = closest relationship type)"。"exact match"在字符串层面不明确—— "角色A" vs "角色A（真面目）" 是否同一目标？下一步实现运行时加载器时必然踩坑。
- **影响范围**：即将开始的 simulation 层实现。
- **证据**：同上 schema；[docs/requirements.md:949](docs/requirements.md#L949) "对象类型或具体角色"。

#### M9 — 原子写缺父目录 fsync（POSIX 意义上不完整原子）
- **结论**：[progress.py:48-72](automation/persona_extraction/progress.py#L48-L72) 与 [rate_limit.py:291-305](automation/persona_extraction/rate_limit.py#L291-L305) 都是 `write tempfile → fsync(file) → rename`，但没有对父目录 `fsync`。POSIX 要求对 rename 的原子性也 fsync 目录 fd 才能保证崩溃恢复。
- **为什么是问题**：ext4 默认 `barrier=on` 情况下实际 OK；但在某些云文件系统 / NFS / 某些挂载参数下，rename 可在目录元数据落盘前被 crash 吞掉。
- **影响范围**：极端场景（电源故障 + 非 ext4 / 已关 barrier）；常规不触发。
- **证据**：同上文件行号。

#### M10 — world stage_snapshot `relationship_shifts` 数组无 `maxItems`
- **结论**：与 H4 同源问题；单独列出。[docs/requirements.md:963](docs/requirements.md#L963) 定义"relationships（≤ 10 条）"被 character schema 硬 gate，世界侧未复制该约束。
- **为什么是问题**：同 H4，但范围仅限 relationship_shifts。
- **影响范围**：world 产物可能膨胀。
- **证据**：[schemas/world/world_stage_snapshot.schema.json](schemas/world/world_stage_snapshot.schema.json) 无 `"maxItems"`。

---

### Low

#### L1 — 重复的 `jsonschema` ImportError 守卫（validator.py + checkers/schema.py）
- **结论**：[automation/persona_extraction/validator.py:25-36](automation/persona_extraction/validator.py#L25-L36) 与 [automation/repair_agent/checkers/schema.py:12-18](automation/repair_agent/checkers/schema.py#L12-L18) 两处各自 re-raise ImportError，报错消息不同。
- **影响**：维护负担；错误信息体验不一致。
- **建议**：集中到 validator。

#### L2 — Phase 4 `scene_archive` 每章重试只保留最后一条 error
- **结论**：[automation/persona_extraction/scene_archive.py:64-82](automation/persona_extraction/scene_archive.py#L64-L82) 的 `ChapterEntry.message` 是单字段，重试时覆盖。诊断退化。
- **影响**：诊断弱；不影响流程。
- **建议**：改 list 或分隔符拼接。

#### L3 — Phase 4 进度文件 `scenes_total = 0` 但 `scene_archive.jsonl` 有 1236 行
- **结论**：`phase4_scenes.json` 结构里 `scenes` 字段为空数组（以 chapter 为主维度），但最终产物 `retrieval/scene_archive.jsonl` 有 1236 行。两者统计口径不一致，令审计者需要外部核验。
- **影响**：状态文件命名/字段不直观；非 bug。

#### L4 — `post_processing.py` 宣称"幂等"，实际是"按 stage number 覆盖 upsert"
- **结论**：`post_processing.py` 对 digest 的"幂等"描述准确来说是"key 为 memory_id/stage_num 的 upsert"。非顺序敏感的 upsert 在无序重跑下会产生乱序 JSONL（FTS5 不受影响，但人工 diff 会困惑）。
- **影响**：文档措辞与实际语义稍有出入。

#### L5 — `timeline_anchor` 字段无 description
- **结论**：character / world stage_snapshot schema 都有 `"timeline_anchor": {"type": "string"}`，docs 从未解释此字段何时填、填什么格式、加载器是否使用。
- **影响**：未来实现歧义。

#### L6 — `schema_reference.md` 不交叉链接 `requirements.md §2.2.2` 阈值表
- **结论**：阈值（`knows ≤50` 等）集中在 requirements，但 schema_reference 不指向那里；schema 本身的 description 也未统一注明硬 gate 数值。
- **影响**：查找效率；非 bug。

#### L7 — 短引用兜底（`build_coverage_shortage_verdict`）取首章首行
- **结论**：[automation/repair_agent/triage.py:306-320](automation/repair_agent/triage.py#L306-L320) 找不到合适 quote 时退回首章首个非空行。若首行是章节标题（极短），M2 的 substring 弱校验问题在此兜底被放大。
- **影响**：audit 痕迹弱；实际影响小（coverage_shortage 本来就零 token 旁路）。

#### L8 — `misunderstandings` / `concealments` 已 resolved 条目的保留策略未定
- **结论**：schema 允许 `resolved_at_stage` 字段存在，docs 暗示"已解决应移除"。两种做法可共存会导致数据不一致。
- **影响**：一致性风险；目前 S001 样例未触发（stage 1 无历史）。

#### L9 — `fixed_relationships.json` schema 存在但无任何 Phase 2.5 产物 sample 验证检查是否对齐
- **结论**：已跟踪 `fixed_relationships.json` 并存在 schema；但没有在 consistency_checker 中显式 gate"relationship 描述的角色必须存在于 candidate_characters"。若 baseline LLM 产出虚构角色，无程序化拦截。
- **影响**：潜在漏检，需要后续加 check。

---

## 2. Open Questions / Ambiguities

1. **谁是 Phase 3 状态的"单一真相源"**：`pipeline.json` 还是 `phase3_stages.json`？当前代码推断前者是顶层 Phase 门控（done/pending/...），后者是 stage-level。那 pipeline.json 的 `phase_3` 字段在"部分完成"时（S001 done, 其余 pending）应该写什么？没有明确状态值。建议定 `partial` 枚举。

2. **Phase 4 产物是否需要在 S001 重跑后重新生成**：如果 world `stage_events` S001 内容被 Phase 3 重跑修改过，`scene_archive.jsonl` 的 scene → stage 映射（通过 `stage_plan.json` 查，不直接依赖 stage_events）理论上不受影响。但运维没有明确答案，留作产品决策。

3. **Triage 引用最小长度**：程序是否应强制 `len(quote) >= N`？定多少？默认建议 10 字符。需要与 triage prompt 设计者对齐。

4. **`extraction_notes/{stage_id}.jsonl` 是否需要 per-character 聚合加载器**：runtime 明确不读（audit-only），但 Phase 3.5 consistency_checker 要读来免 min_examples 报错；检查器当前是否已实现该路径？（spec 说"treats a valid SourceNote as equivalent"，但 consistency_checker.py 未见对应逻辑，需要实现侧确认 — 此处未全面核对，列为 Open Question。）

5. **`load_profiles.json` 默认值缺失时的行为**：加载器应使用 dataclass 默认还是要求 per-work 显式提供？没有规范。

6. **S002 残留 error_message 是否需要人工干预**：`"Working tree has uncommitted changes"` 暗示上一次尝试 preflight 失败，但现在 master 只有 `.claude/settings.json` 脏（scope 外）。按 `scope_paths` 新逻辑不应再拦，建议 `--resume` 直接试跑看能否自愈。

---

## 3. Alignment Summary

**对齐良好**：
- stage_id 英文化（`S###`）在 schemas / prompts / code / ai_context / committed artifacts 全链路统一（`e7e2a20` / `1573506` / `9cce39f` 系列最近完成）。
- ID 家族（`M-S###-##` / `E-S###-##` / `SC-S###-##`）在所有实例中一致（extraction 分支 S001 产物 verified）。
- gitignore vs 实况对齐：`users/` 仅 `_template` + `README.md` 跟踪；`sources/` 只有 manifest/keepers 跟踪；`works/*/retrieval/` 本地生成未跟踪；`works/*/analysis/` 仅跟踪 `world_overview.json` / `stage_plan.json` / `candidate_characters.json`。
- 数据形态硬 gate 在 S001 样例全部满足：knowledge_scope 计数、memory_timeline 长度、relationship_history ≤300 等（artifacts 子 agent 确认）。
- `build_status` 字段在所有 manifest 文件中确实不存在（decision 27a 落实）。
- placeholder 规则：spec 层无真实书名/人名/地名泄漏。

**对齐最差**：
- **phase3/pipeline/ai_context 三方对 Phase 3 进度的叙述**（H1）—— 当前仓库最大的真实性空洞。
- **world 侧 schema 硬 gate 完整度**（H4 + M10）—— 与 character schema 不对称。
- **spec 承诺的 schema 缺失**（H2）—— 3 份文件的 validation 目前无效。
- **spec 承诺的审计能力 vs 实现**（M2 + M5 + M6）—— 若干"会拦截 / 会防御"的点实际是静默通过。
- **docs/logs/ 节奏**（M7）—— 自动化产出不入 log，只能从 git + failed_lanes 反推。

---

## 4. Residual Risks

1. **Extraction 分支大量 merge commits（`Merge branch 'master' into extraction/...` 连续 20+ 次）**：每次 master 修改都 merge 进来。目前没问题，但 squash-merge 到 master 的时候，若 extraction 分支上有"master 合过来、extraction 上重写同一文件"的历史，squash 结果可能"再次应用"已经在 master 存在的改动。建议 squash 前 review 一次 `git log extraction/... --not master` 的净差。

2. **`scene_archive.jsonl` 为 4.1 MB 本地产物且无 schema 验证**：若 Phase 4 一旦产出格式微漂（某章缺字段），下游检索会沉默失败。建议 H2 中添加 scene_archive schema 并在 Phase 4 完成时跑一遍验证。

3. **`rate_limit_pause.json.lock` 已在 progress/ 目录残留**：本身不破坏，但若正常退出未清理 lock 文件，可能造成下次启动误判"还有其他 leader 在 probe"。未在本轮细查。

4. **prompt templates 与 schema 字段的细粒度对齐**：extraction_workflow 中 extraction prompt 的字段命名是否都能反查到 schema（例如 character_snapshot_extraction.md 是否引用已废弃字段）本轮未逐行对比，作为残余风险保留给下一轮专项 prompt 审计。

5. **无 simulation 层 Python 代码**：runtime 尚未实现，目前所有 runtime 设计只是 markdown。spec 承诺的 "filtered loading" / "backward scan fallback" / "两级检索漏斗" 的实际可行性未被任何执行层验证；H2/M8 是将来 implement 时的明确风险点。

6. **`automation/repair_agent/_smoke_l3_gate.py` 与 `_smoke_triage.py` 是否真的被 CI 跑**：这两个下划线前缀文件存在于仓库，说明曾作为 smoke test，但没看到它们被 import/引用。未确认是否死代码。

---

## 5. 建议落地顺序

**立即（<1 天）**：
1. **H1**：更新 `pipeline.json` 的 `phase_3 / last_updated` 使之与 `phase3_stages.json` 对齐（最简单：把 `phase_3` 改成 `partial`，`last_updated` 同步到 S001 commit time）。同步更新 `ai_context/current_status.md` 第 5-9 行与 `next_steps.md` 第 5-13 行——写清"S001 已 committed at SHA 3bf25bf，S002 在 error 待 resume，S003-S049 pending"。
2. **H4 / M10**：在 `world_stage_snapshot.schema.json` 的 `stage_events` 加 `"maxItems": 10`，`relationship_shifts` 同步。
3. **M1**：`orchestrator.py:1189-1192` 追加 `b.fail_source = ""`；`progress.py:force_reset_to_pending` 同步。

**短期（本周）**：
4. **H2**：创建 `schemas/world/foundation.schema.json`（从现有 `works/.../world/foundation/foundation.json` 反推结构），`schemas/runtime/scene_archive_entry.schema.json`，`schemas/work/load_profiles.schema.json`。
5. **M2 + L7**：给 `triage._verify_quote` 加最小长度校验 + 选配 line_range 一致性。
6. **M4**：config.py 对未知键改为 logger.error，可选增 `strict_config` raise。
7. **H3**：为 commit-state 窗口加兜底——要么先写 "committed, awaiting transition" 中间态；要么在 reconcile 中按 commit message 搜索 SHA。

**中期**：
8. **M7**：自动化完成一个 stage 后落地 `docs/logs/` 条目（可由 orchestrator 在 `phase3.save()` 之前 / `finish_stage()` 时写入）。
9. **M8**：为 `target_type` 定义 enum / pattern，明确 `角色A（真面目）` 的形式。
10. **L1**：集中 jsonschema import guard。
11. **M5 + M6**：加 warning 日志 + 防御性 isinstance。
12. **M3 + M9**：L3 gate 历史带轮次；原子写补目录 fsync。

**旁路（未来）**：
L4 / L5 / L6 / L8 / L9 作为下一轮"/after-check coverage_shortage 回补"的候选条目登记到 `docs/todo_list.md`。

---

## 6. False Positives（记录以免再纠缠）

- 子 agent 最初把 H3 标为"CRITICAL: crash 在 1810-1814 之间会写入 PASSED+committed_sha 不一致状态到 phase3_stages.json"。经复核该场景不成立：`phase3.save()` 在行 1815，1810-1814 的内存赋值在 save 之前崩溃不会落盘。真正的残余风险是"git commit 已写但 phase3.save 未执行"窗口，已在 H3 记录，且严重性降为 MEDIUM–HIGH。
- 子 agent 提出的"post-processing 的 memory_digest 去重乱序 = 非幂等"严格意义上是正确描述但与 idempotent 的常规语义未必冲突（FTS5 / 读端不在意顺序）。列为 L4 低优。
- "rate-limit 按 resume_at 去重存在时钟抖动 race"在理论上存在，但 `_accounted_resume_at` 受锁保护 + resume_at 由同一 controller 派发，多 lane 共享同一时刻的概率极高，非边界时钟抖动。实际影响极低，不单独列 finding。
- 子 agent 的 `LLM_backend --effort` 未核实（未读 `llm_backend.py`），为避免误报未列 finding。
- spec agent 关于"spec 层 legacy 措辞"的结论经复核可信：`grep -rn '旧\|legacy\|renamed from\|原为' ai_context/ docs/requirements.md docs/architecture/ schemas/ prompts/` 未出现于规范层；仅 `docs/logs/` 与 `docs/review_reports/` 里出现，符合豁免。
