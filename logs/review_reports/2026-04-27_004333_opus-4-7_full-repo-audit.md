**Review 模型**：Claude Opus 4.7（`claude-opus-4-7[1m]`）

# /full-review — 全仓库对齐审计

时间：2026-04-27 00:43:33 (America/New_York)
范围：整个 Offpage 仓库；当前分支 `main`，HEAD `f4a68e8`。
方法：三条并行审计线（spec / 实现 / 样例产物）+ 主审手动复核高优先级 finding。

---

## Findings

### High

#### H-1. `stage_title` maxLength 在 schema 间不一致（14 vs 15 vs 无）

**结论**：同一字段在五份 schema 中出现三种 bound：
- [schemas/analysis/stage_plan.schema.json:47](schemas/analysis/stage_plan.schema.json#L47) — `maxLength: 14`，描述 "<15 字"
- [schemas/character/stage_snapshot.schema.json:49](schemas/character/stage_snapshot.schema.json#L49) — `maxLength: 15`，描述 "≤15 字"
- [schemas/world/world_stage_snapshot.schema.json:38](schemas/world/world_stage_snapshot.schema.json#L38) — `maxLength: 15`
- [schemas/character/stage_catalog.schema.json:48](schemas/character/stage_catalog.schema.json#L48) — **无 `maxLength`**
- [schemas/world/world_stage_catalog.schema.json:43](schemas/world/world_stage_catalog.schema.json#L43) — **无 `maxLength`**

**为什么是问题**：违反 decision #27b "bounds-only-in-schema, single source of truth"。Phase 1 产出的 `stage_plan.json` 中 `stage_title` 限定 14 字，但下游 `stage_snapshot` 允许 15 字，而 `stage_catalog`（bootstrap 阶段选择器！）完全无 bound——长标题可能从某些来源进入 catalog，而 plan 又会拒绝，导致跨阶段一致性裂缝。description 文本与 schema 数字也不同步（"<15 字" 实为 "≤14 字"）。

**影响范围**：Phase 1 schema gate（schema-gate-as-retry-trigger，#27i）；运行时 bootstrap 阶段选择器（catalog 直接驱动 UI）。

**建议**：统一为 14 或 15（任一），并更新所有五份 schema + description。如选 14，需让 `stage_catalog` 强制 14；如选 15，需把 `stage_plan` 的 14 改 15 并更正描述。

---

#### H-2. Decision #26 承诺的"squash 后自动删分支 + `git gc --prune=now`"未实现

**结论**：三处 ai_context / 架构文档明确承诺 squash 后删分支并 gc：
- [ai_context/decisions.md:81](ai_context/decisions.md#L81) — "After squash, delete the source `extraction/{work_id}` branch (`git branch -D`) and run `git gc --prune=now`"
- [ai_context/architecture.md:143](ai_context/architecture.md#L143) — 同样的措辞
- [ai_context/conventions.md:102](ai_context/conventions.md#L102) — 同样的措辞

而代码 [automation/persona_extraction/orchestrator.py:2113-2114](automation/persona_extraction/orchestrator.py#L2113-L2114) 只 print 了一条提示：
```
print(f"  Extraction branch '{branch}' preserved. "
      f"Delete with: git branch -d {branch}")
```
- 没有调用 `git branch -D`（甚至打印的也是小写 `-d`，会拒绝删除未合并的分支）
- 没有调用 `git gc --prune=now`
- `git_utils.py:307` 注释明确 "The source branch is **not** deleted — caller decides"，但 caller 也没做

**为什么是问题**：
1. **承诺与现实裂缝**——文档把它写成自动化契约的一部分（"so accumulated regen commits become unreachable and are reclaimed"），但没人执行。
2. **磁盘累积**——extraction 分支无限累积；"library squash 是唯一保留记录" 这一前置假设悄悄失效。
3. 即使把打印的指令照抄执行，因为是 `-d` 而不是 `-D`，对 squash-merged 分支会被 git 拒绝（"not fully merged"），用户只能手动 `-D`。

**影响范围**：分支生命周期 / 仓库磁盘 / 三分支模型的"disposable scratchpad"承诺。

**建议**：要么实现 auto-delete + gc（最严格地遵循 decisions），要么 downgrade 文档措辞为"用户手动执行"，并把打印中的 `-d` 改 `-D`、补 `git gc --prune=now`。

---

#### H-3. Phase 3.5 一致性检查数量漂移：docs 说 10、代码跑 9

**结论**：
- [ai_context/architecture.md:160](ai_context/architecture.md#L160) — "10 programmatic cross-stage consistency checks (0 token)"
- [docs/requirements.md:1266](docs/requirements.md#L1266) — "10 项程序化检查 (0 token)"
- [automation/persona_extraction/consistency_checker.py:110-121](automation/persona_extraction/consistency_checker.py#L110-L121) — 实际只调用 9 个 `_check_*` 函数：
  1. `_check_alias_consistency`
  2. `_check_field_completeness`
  3. `_check_relationship_continuity`
  4. `_check_memory_id_correspondence`
  5. `_check_memory_digest_summary_equality`
  6. `_check_target_map_counts`
  7. `_check_stage_id_alignment`
  8. `_check_world_event_digest`
  9. `_check_world_event_digest_summary_equality`

**为什么是问题**：要么文档夸大、要么有一项检查在历次重构中被悄悄删掉而没人补回。任一情况下，文档与实现都不再对齐——两份 ai_context / 架构权威源同时漂移，未来 review 会反复踩同一个坑。

**影响范围**：Phase 3.5 实际质量保护强度未知；外部读者据 docs 估算覆盖度会高估 10/9 ≈ 11%。

**建议**：要么把缺失的第 10 项补回（最可能丢的候选：`stage_events` 字数 / `boundary_state` 完整性 / `core_wounds` 跨阶段连续性 / `failure_modes` 一致性），要么把所有文档改为 "9 项"。后者更稳妥（证据一致才改）。

---

### Medium

#### M-1. `automation/prompt_templates/character_snapshot_extraction.md` 仍在表格里展示"旧字段名 → 新字段名"映射

**结论**：[automation/prompt_templates/character_snapshot_extraction.md:128](automation/prompt_templates/character_snapshot_extraction.md#L128) 表格里有一行：
```
| stage_snapshot.behavior_state | `relationship_behavior_map` | 统一使用 `target_behavior_map`（baseline 与 stage 快照同名）|
```

**为什么是问题**：
- conventions.md §Generic Placeholders 明确规定 `automation/prompt_templates/` 是 canonical 目录，"No history narration ('legacy', 'deprecated', 'formerly', 'renamed from')"。
- 此条记录的恰恰是"曾经叫 `relationship_behavior_map`，现在叫 `target_behavior_map`"——形式上的"renamed from"。
- 用户的 memory rule 也明确禁止 docs / prompts / ai_context 出现"renamed from / 旧 / 已废弃 / legacy"等。

**辩护视角**：表格目的是防止 LLM 因训练数据偏好而默写旧名，技术效果上是有用的。

**建议**：把表格里的 "错误字段名" 列改为简单提示（如"曾被错写为 X"），或改写成"必须使用 `target_behavior_map`"的肯定句，剥离 history 暗示；同步 [docs/architecture/schema_reference.md:80] 等若有类似表述。

---

#### M-2. 没有 `works/_template/` 脚手架

**结论**：`works/` 仅 tracked `README.md`，没有 `_template/` 子目录；而 `users/_template/` 是存在的（[users/_template/](users/_template/) 含 `profile.json` / `role_binding.json` / `long_term_profile.json` / `relationship_core/` / `contexts/` / `conversation_library/`）。`works/README.md` 描述了完整目录树（[works/README.md](works/README.md)），但没有可直接复制的骨架。

**为什么是问题**：
- 三分支模型规定 `main` 携带 framework + scaffolding only。`_template/` 就是 scaffolding 范式（`users/_template/` 已经这么做）。
- conventions.md §Git 表格也提到 `_template/` 是 main 上唯一被允许的 work-id 风格目录。
- 未来再加新作品要么手抄 README、要么 `git checkout extraction/{work_id} -- works/{work_id}/` 后再清空，DX 不一致。

**影响范围**：未来作品 onboarding；与 `users/_template/` 的设计对称破缺。

**建议**：建一个 `works/_template/` 含空骨架（占位 `<work_id>` / `<character_id>` / `S001`）；或在 `works/README.md` 顶部明确声明"未提供 `_template/`，按 README 手动建目录"，至少让缺失变成显式契约。

---

#### M-3. `ai_context/handoff.md` "extraction-branch artifact drift" 段落是历史叙事

**结论**：[ai_context/handoff.md:51-86](ai_context/handoff.md#L51-L86) 列出 "Files likely broken by newer schema gates" 清单，明确描述 "schema tightening over the 2026-04 cleanup series invalidates earlier products"，并枚举 `evidence_refs` / `scene_refs` / `character_status_changes` 等被移除字段。

**为什么是问题**：
- conventions.md §Generic Placeholders 禁止 ai_context 出现 "legacy / deprecated / formerly / renamed from"。
- 这段是 8 行 `evidence_refs removed` / `scene_refs removed` / `character_arc 是 short string (was object)` / `relationship_behavior_map → target_behavior_map` 的"renamed from"清单。
- 用户的 feedback memory `feedback_docs_describe_current_only.md` 也明确反对此模式。

**辩护视角**：handoff 是为下一次 `--resume` 服务的操作清单，删除会丢失关键的"现存 S001/S002 产物已不合规"信息。

**影响范围**：仅 ai_context/handoff.md 段。

**建议**：把这段移到 `docs/todo_list.md`（实际上 [docs/todo_list.md:104+](docs/todo_list.md#L104) 已经有相同内容！重复）；或留在 handoff，但措辞改为"current schemas require X / Y / Z"，剔除"renamed from / removed"的历史动词。一旦 S001/S002 重跑后，整段可全删。

---

### Low

#### L-1. `.gitignore` 第 26 行根级 `analysis/evidence/*` 是死规则

**结论**：[.gitignore:25-29](.gitignore#L25-L29)：
```
# Evidence artifacts (large intermediate outputs)
analysis/evidence/*
!analysis/evidence/.gitkeep
works/*/analysis/evidence/*
!works/*/analysis/evidence/.gitkeep
```
当前架构里没有 root-level `analysis/` 目录；只有 `works/*/analysis/`。前两行是历史遗留。

**为什么是问题**：让读 `.gitignore` 的人误以为有两套 evidence 路径。功能无实际影响，仅清晰度问题。

**建议**：删第 26、27 行；保留 `works/*/analysis/evidence/*` 即可。

---

#### L-2. `schema_reference.md` 把 `StageEntry`（Python dataclass）当 schema 文件索引

**结论**：[docs/architecture/schema_reference.md] 列出 "StageEntry（Phase 3 阶段状态，序列化到 `phase3_stages.json`）" 作为 schema 引用条目，但 `schemas/` 下并无 `stage_entry.schema.json`——这是 Python dataclass（[automation/persona_extraction/progress.py]）。

**为什么是问题**：schema_reference.md 文件的命名暗示"枚举所有 schema 文件"。把 dataclass 列进去会让读者误期望去 `schemas/` 找文件。

**建议**：要么单列一节"Python dataclass / 序列化产物"，要么删除这条；或为 `phase3_stages.json` 建立真 schema 并加 jsonschema gate（同时也补 #27i 的 schema-gate-as-retry-trigger 队列）。

---

#### L-3. Phase 3.5 没消费 `_check_alias_consistency` / `_check_field_completeness` 的 importance_map

**结论**：[automation/persona_extraction/consistency_checker.py:96-117](automation/persona_extraction/consistency_checker.py#L96-L117) 读 `candidate_characters.json` 构造 `importance_map`，仅 `_check_target_map_counts` 用到。其他 8 个 check 不知道角色是主角/重要配角/次要配角——`field_completeness` / `relationship_continuity` 对所有角色一刀切。

**为什么是问题**：decision #15 明确 "main / important chars (≥3–5 examples); generic types brief or omitted"——bound 本就因 importance 而异。一致性检查不区分 importance，可能对次要配角过度报错或对主角过宽。

**影响范围**：Phase 3.5 命中率精度。

**建议**：把 `importance_map` 透传到 `_check_field_completeness` 与 `_check_target_map_counts` 协同，按 importance 调整最低门槛。

---

## False Positives（审计中暂报后已排除）

- **`docs/requirements.md:95` 提到 `evidence_refs`** — 是"schema 不再保留独立的 `evidence_refs` 字段"的移除说明，不是 stale 引用。✅
- **`docs/architecture/data_model.md:99` 与 `schema_reference.md:80` 的 `source_types`** — 是 work_manifest.schema.json 的 plural 字段，与被移除的 singular `source_type`（per-item evidence anchor）是两码事。✅
- **`schemas/work/work_manifest.schema.json:11,30` 的 `source_types`** — 同上，合法字段。✅
- **`.claude/settings.local.json` 中真实 work_id 出现 15+ 次** — `.gitignore:54` 已正确忽略；不会污染 main，本地工具配置不算 finding。✅
- **subagent 报告"Bonus #1 rate_limit / --max-runtime 解耦"** — 实际 `rate_limit.py:648-663` 已用 `resume_at` 去重；架构契约满足。✅

---

## Open Questions / Ambiguities

1. **`stage_title` 应统一到 14 还是 15？** stage_plan 选 14（说"<15 字"），其他选 15。哪个是 source of truth？
2. **`_offer_squash_merge` 应该 auto-delete + gc，还是依旧让用户手动？** 三处 ai_context 文档措辞像自动契约，但代码与 git_utils 注释像"caller decides"。需要决策方落定。
3. **Phase 3.5 第 10 项 check 是被丢了还是从未存在？** 需要回查重构历史决定补/删。
4. **`works/_template/` 是有意省略，还是漏建？** 与 `users/_template/` 不对称——建议提决策记录。
5. **`automation/prompt_templates/` 表格里"错误字段名 → 正确字段名"映射，对 LLM 防回退是否够 valuable 到值得违反 §Generic Placeholders？** 这是"防训练数据偏好"vs."不写历史"的取舍，需要明面拍板。

---

## Alignment Summary

**对齐度高的层**：
- schemas ↔ post_processing / repair_agent 的 bound 不重复定义（#27b 实施到位，仅 `StructuralChecker.relationship_history_summary_max_chars` 一处合规例外）。
- `jsonschema` HARD dep 落地（pyproject.toml 中 `dependencies` 而非 extras）。
- schema-gate-as-retry-trigger 模式（#27i）在 5 份 schema 上闭环：chunk / scene_split / world_overview / stage_plan / candidate_characters 全部接入了 `prior_error` / `correction_feedback` retry 通道。
- 三分支 git 模型：orchestrator 的 `try / finally: checkout_main(scope_paths=[works/{work_id}/])` + `session_branch_check.sh` 闭环。
- Phase 3 commit-ordering 契约（commit-first / SHA → COMMITTED / empty → FAILED）严格按文档实现。
- Phase 3 lane resume + ERROR→PENDING reset 与文档一致。
- `users/_template/` 占位符纯粹（无真实人名 / work_id）。
- main 分支非常干净（除 README，无任何真实 work_id-named tracked 文件）。

**对齐度最差的层**：
1. **ai_context / docs 与代码在"分支清理"环节脱节**（H-2）——三份文档同步漂移，代码不实施。
2. **schema 内部对同字段 bound 不一致**（H-1，stage_title）。
3. **数量级文档承诺与代码实现脱节**（H-3，10 vs 9）。

---

## Residual Risks

1. **`extraction/我和女帝的九世孽缘` 分支上的 S001 / S002 产物，按当前 schema 全部已过期**（[handoff.md:51](ai_context/handoff.md#L51) 的清单与 [docs/todo_list.md:104+](docs/todo_list.md#L104) 重复确认）。`--resume` 前若不重跑这两阶段，repair_agent L1 gate 会在每个旧文件上爆。这本身是已知约束，但风险在于：用户记忆里 "S001 / S002 已 committed" 与"已合规"是两个不同概念，handoff 里说得已够清楚，但代码未在 `--resume` 启动时主动复检并阻断；只能依赖 repair_agent 后置失败。**建议**：`--resume` 启动时对所有 COMMITTED stage 跑一次 schema 全量校验，过期则强制提示重跑。
2. **`works/我和女帝的九世孽缘/analysis/progress/rate_limit_pause.json.lock`** 落在 main 工作树（已被 `.gitignore` 命中 `works/*/analysis/progress/`，不会污染 main）但 `.lock` 文件本身在 main 上属于"非主分支泄漏到 main 工作树"——属正常（同一 working tree 跨分支检出会留），无 finding。
3. **`auto_squash_merge=true` 配合 H-2** ：若用户开启 auto，extraction 分支会立即被 squash 进 library，但永远不删——磁盘累积更快、用户更难察觉。
4. **prompt template 里硬编码的 50–80 / 50–100 数字**（[character_snapshot_extraction.md, world_extraction.md] 的 stage_events 长度提示）当前与 schema 一致，但属"在 prompt 里复述 bound"而非引用 schema——若以后 schema 改，prompt 不会自动跟随。这与 #27b "bounds-only-in-schema" 在严格意义上有摩擦，但 prompt 复述目的是给 LLM 看，spec-line 上属灰色地带。**建议**：在 prompt 顶部加一句"bound 以 schema 为准；若数字与 schema 不一致，schema 优先"。
5. **`automation/prompt_templates/` 提示反复出现"≤N 字"硬数字**——这是 LLM 提示策略需要，但与 conventions §Data Separation "Bounds only in schema. No duplicates anywhere else" 的字面要求冲突。已通过 #27b 第二段"Bounds are caps, not targets" 的存在被默认豁免，但仍值得周期复盘。
6. **`docs/todo_list.md` 与 `ai_context/handoff.md` 重复**：两文件都列出了"S001 / S002 schema 过期"清单。任一边更新而另一边不跟随，就漂移。考虑只保留 `docs/todo_list.md`，handoff 里只放一句指针。

---

## 建议落地顺序

1. **H-2** — 决定是 auto 还是 manual，把 docs / 代码对齐；最低成本：把打印的 `-d` 改 `-D` 并补 `git gc --prune=now` 提示。
2. **H-3** — 数清楚是 9 还是 10；改 docs 比改代码更稳。
3. **H-1** — 统一 `stage_title` bound（建议 ≤15）；同步五份 schema + descriptions。
4. **M-3** — 从 handoff 移到 todo_list（已重复），handoff 改为指针。
5. **M-2** — 决定是否建 `works/_template/`；不建也要在 README 显式声明。
6. **M-1** — `relationship_behavior_map → target_behavior_map` 表格行改写为肯定句。
7. **L-1** — 删 `.gitignore` 死规则。
8. **L-3** — `consistency_checker` 接 `importance_map` 给 field_completeness。
9. **L-2** — `schema_reference.md` 单列"Python dataclass / 序列化产物"。

---

## 未覆盖区域

- 未实跑 orchestrator / Phase 1–4 端到端；所有"代码满足契约"判断基于静态阅读。
- 未切到 `extraction/我和女帝的九世孽缘` 分支查 S001 / S002 实际产物；`--resume` schema gate 风险只能据 handoff 文字推断。
- `simulation/` 目录是设计文档（无实现），未做"代码符合 contracts" 校验，因此尚无可校验之物。
- `interfaces/` 未读（README 显示空）。
- `sources/` 未读（按 read_scope 默认排除）。
- `.claude/commands/*.md` 仅做了 `/full-review` 镜像约束的 spot-check，没全量比对其他 skill 与 `.agents/skills/` 的镜像。
