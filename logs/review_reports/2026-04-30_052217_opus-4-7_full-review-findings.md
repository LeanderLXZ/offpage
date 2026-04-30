**Review 模型**：Claude Opus 4.7（`claude-opus-4-7[1m]`）

# /full-review — 全仓库对齐审计

时间：2026-04-30 05:22:17 (America/New_York)
分支：`main` @ `9519ea4` (clean, in sync with `origin/main`)
触发：用户 `/full-review`，无 ``。

---

## Findings

### High

#### H1. `works/README.md` 仍把 4-piece deprecated baseline 当作现行结构

- **位置**：[works/README.md:47-50](works/README.md#L47-L50)（目录树）+ [works/README.md:130-154](works/README.md#L130-L154)（逐文件描述带 schema 路径）。
- **结论**：README 在 "推荐目录结构" 与 "characters/ 子目录说明" 两处仍把 `voice_rules.json` / `behavior_rules.json` / `boundaries.json` / `failure_modes.json` 列为角色 canon 子文件，并标注 `schema: schemas/character/{voice_rules,behavior_rules,boundaries,failure_modes}.schema.json` —— 这四个 schema 文件已不存在（`ls schemas/character/` 实际只有 `character_manifest / identity / memory_digest_entry / memory_timeline_entry / stage_catalog / stage_snapshot / target_baseline / targets_cap`）。
- **为什么是问题**：`ai_context/decisions.md` §11d 与 `ai_context/current_status.md` §Project Stage 都明确：4-piece baseline 已于 2026-04-29 弃用，`failure_modes` 内联进 `stage_snapshot`，voice / behavior / boundary 状态原本就在 `stage_snapshot.{voice_state,behavior_state,boundary_state}`。schema 也已删除。但 `works/README.md` 是面向新协作者 / 未来 AI 的入口式说明文件（位于 `## Example artifact directories` 配置的根 README），它现在描述的是被弃用结构。
- **影响**：高。任何按 README 创建作品包的人会去找根本不存在的 schema、写无效的文件；任何按 README 校对产物的人会判断错"哪些文件应该存在"；未来 AI 读 README 也会形成错误 mental model。
- **证据**：
  - `grep -n "voice_rules\|behavior_rules\|boundaries\|failure_modes" works/README.md` → 命中 47–50 + 130–154
  - `ls schemas/character/` → 没有那四份 schema
  - `ai_context/decisions.md:44-58` 明确弃用
- **建议**：删 47–50 的目录树条目；把 130–154 那 5 段（含 stage_catalog 之前的部分）整体替换为指向 `stage_snapshot.{voice_state,behavior_state,boundary_state,failure_modes}` 内联结构 + identity 的 `core_wounds` / `key_relationships` + `target_baseline` 的简短描述；并在 §设计规则 增补一条 "voice / behavior / boundary / failure_modes 在 `stage_snapshot` 内逐 stage 演化，无独立 baseline 文件"。

---

### Medium

#### M1. `schemas/_shared/` 是被引用的占位目录，但磁盘上不存在

- **位置**：
  - [schemas/README.md:16-27](schemas/README.md#L16-L27) —— 表格里把 `_shared/` 列为子目录，并花专段说明 "`_shared/` 与 `shared/` 的区分"
  - [ai_context/conventions.md:82](ai_context/conventions.md#L82) —— "cross-domain shares live under `schemas/_shared/`"
  - [ai_context/decisions.md:169](ai_context/decisions.md#L169) —— 同上
- **结论**：`ls schemas/` 实际为 `analysis / character / runtime / shared / user / work / world` —— 没有 `_shared/`。`schemas/README.md` 自己说"当前为空——之前放过 `targets_cap`，但它只被 character 域内部共享，按'域内独享 → 放对应域目录'回滚到 `schemas/character/`"，所以 `_shared/` 的当前状态是"空目录占位"，但实际目录都没建。
- **为什么是问题**：spec 三处把 `_shared/` 当作现存路径在引用（甚至带与 `shared/` 的区分说明）；实际目录不存在，会让人怀疑文档是不是漏更，或者反过来误以为目录被无意删了。
- **影响**：中。不影响运行（目前没有跨域共享片段需要它），但对希望"cross-domain bound 共享时往哪放"的协作者是死链。
- **证据**：`ls schemas/` 输出无 `_shared/`；`ls schemas/_shared/` → "No such file or directory"。
- **建议**：二选一。(a) 实建 `schemas/_shared/.gitkeep`，与 README 描述对齐；(b) 把三处 spec 语句改为 "若出现跨域共享片段，按约定建 `schemas/_shared/`"，并把 `schemas/README.md` 那一段从"当前为空"降级为"按需创建"。倾向 (b)，因为 (a) 等于把"未发生的需求"先建空目录占位。

#### M2. `docs/architecture/schema_reference.md` schema-count 表对不上磁盘

- **位置**：[docs/architecture/schema_reference.md:11-19](docs/architecture/schema_reference.md#L11-L19)。
- **结论**：表格 `文件数` 列：
  - `schemas/work/` 标 6，实际 5（`book_metadata / chapter_index / load_profiles / work_manifest / works_manifest`）
  - `schemas/character/` 标 6，实际 8（多了 `target_baseline.schema.json` + `targets_cap.schema.json`，与 decisions §13 / §27b 的演进同步）
  - 其他子目录数字一致
- **为什么是问题**：`schema_reference.md` 在 conventions.md §Cross-File Alignment 里被点名是 schema 索引；它和实际 schema 数量漂移意味着 (i) `work/` 缺一份还是 README 计数过期？(ii) `character/` 加了 `target_baseline` + `targets_cap` 但索引头表没刷。
- **影响**：中。表格本身只是 navigation 索引，但作为 schema 唯一索引文档，它的口径错位会让审计或 AI 复审时"以为 work 还有一份没看"。
- **证据**：本轮 `ls schemas/{analysis,work,world,character,user,runtime,shared}/` 实测；表格未被同步刷新（schema_reference.md 第 19 行 shared/ = 1 倒是对的）。
- **建议**：把 `work/` 改 5、`character/` 改 8（或 7，看是否把 `targets_cap.schema.json` 计入；按 README §`_shared/` 说明它是 "cross-schema sharing 片段" 但既然它就在 `character/` 目录下，按文件数实计算 8 比较一致）。顺手把 schema_reference.md 正文里 `schemas/character/` 一节核对 `target_baseline` / `targets_cap` 是否都有专节。

---

### Low

#### L1. `current_status.md` §Rules In Effect 没说明"哪些规则只在 extraction/library 分支生效"

- **位置**：[ai_context/current_status.md:64-65](ai_context/current_status.md#L64-L65)：
  > `works/*/analysis/`: only `world_overview`, `stage_plan`, `candidate_characters`, `consistency_report` tracked; `progress/`, `chapter_summaries/`, `scene_splits/`, `evidence/*` local
  > `works/*/world/`, `works/*/characters/`, `works/*/indexes/` tracked; `works/*/retrieval/` local
- **结论**：这两条描述的是"作品包内哪些子路径会进 git" —— 但 `main` 分支本身规定为 framework-only，根本没有任何 `works/{work_id}/` 实物目录（只有 `works/README.md`）。所以这两条只在 `extraction/{work_id}` 与 `library` 分支才有意义。文件没标这个限定，读起来像是 main 上也该见到 world / characters / indexes 进 git。
- **为什么是问题**：低。规则在语义上仍然成立（main 上空，规则空成立），但缺一个"(on extraction/{work_id} and library branches)"的限定容易让读者误以为 main 上漏跟踪了一堆文件。
- **影响**：低。语义没错，只是表述含糊；不会触发误操作。
- **建议**：在该小节最前面加一句："以下 `works/*` 跟踪规则仅适用于 `extraction/{work_id}` 与 `library` 分支；`main` 分支按 framework-only 政策，不存在任何 `works/{work_id}/` 实物目录（仅 `works/README.md`）。"

#### L2. 仓库 root 没有 `README.md`（被 conventions §扫描里隐含期待）

- **位置**：仓库根。
- **结论**：`ls /home/leander/Leander/offpage/` 看不到顶层 `README.md`；本 skill `/full-review` 的扫描清单里点名了 "`README.md`、`.gitignore`"。子目录 (`works/`、`automation/`、`simulation/`、`schemas/`) 各有自己的 README，但仓库根没有。
- **为什么是问题**：低。项目入口靠 `CLAUDE.md` / `AGENTS.md` + `ai_context/` 接管，对 AI 来说够了；但对人来说仓库根缺一个 1–2 屏的 README 解释项目是什么、入口在哪、如何启动 extraction，是个小缺口。
- **影响**：低。
- **建议**：可选。等项目对外曝光时再补；现阶段不补也行。这条不算 bug，归为残留风险。

---

## Open Questions / Ambiguities

1. **H1 的修复范围**：`works/README.md` 是按"推荐目录结构"组织的对外文档，正文还有"schema 硬门控"等措辞依赖描述里的字段名 / 限制。修订时需要先确认：runtime 加载 / extraction prompt 真的还会接触哪些字段是"以 stage_snapshot 内联为准"，避免改 README 时把目录树写得过简，丢掉 `stage_snapshot` 内嵌的关键 sub-key 提示。建议改之前先翻 `automation/prompt_templates/character_snapshot_extraction.md` + `schemas/character/stage_snapshot.schema.json` 的 required / 顶层结构。

2. **M1 选 (a) 还是 (b)**：从洁癖看 (b) 更合理（"按需创建"），从规则的字面执行看 (a) 更安全（README 说"当前为空"就该真有个空目录）。需要用户拍板，决定 spec 里的"当前为空"是否要保留这个语义。

3. **M2 计数口径**：`targets_cap.schema.json` 算"独立 schema 文件"还是"$ref 共享片段"？schema_reference.md 在 §`schemas/character/` 内文里如果没有为它专门列一节，则口径上似乎把它当作"片段"——那计数就该是 7；如果列了专节就是 8。需要先看 schema_reference.md 后段的 character 小节再定。本轮没读到那一段。

---

## Alignment Summary

**对齐良好**：
- `automation/persona_extraction/` 实现层与 `decisions.md` §11–§34 + `architecture.md` §Automated Extraction Pipeline 高度一致：phase 顺序、squash-merge 目标、`try/finally: checkout_main`、L1/L2/L3 repair、`prior_error` retry、Phase 4 schema gate、`migrate_baseline_to_stage_snapshot.py` / `rate_limit.py` / `schema_loader.py` / `validator.py` 都到位。
- D4 `targets_keys_eq_baseline` 校验从 phase 3.5 搬到 phase 3 single-stage validate 层这一项执行干净：`automation/repair_agent/checkers/targets_keys_eq_baseline.py` 存在，`automation/persona_extraction/consistency_checker.py` 头注释明确说"this phase 3.5 module no longer owns that rule"。
- `simulation/` 仍是设计文档（contracts / flows / retrieval / prompt_templates），无 stub 代码，与 `current_status.md` 声明的"design only"一致。
- `users/_template/` 11 个文件 + 占位 `{context_id}` / `{session_id}` 与 `docs/architecture/data_model.md` 用户包契约结构一致。
- `schemas/character/` 已干净删除四份 deprecated baseline schema。
- `.gitignore` 与 `current_status.md` §Rules 关于 retrieval / progress / chapter_summaries / scene_splits / sources 的"不进 git"规则一致。

**对齐最弱**：
- 面向作品包的"门面文档" `works/README.md`（H1）—— 它没跟上 4-piece deprecation 与 `target_baseline` 的引入。
- 跨多文件引用的"schemas/_shared/"占位（M1）—— 三处文档里描述存在的目录磁盘上没有。
- 数字索引类文档 `docs/architecture/schema_reference.md` 头表（M2）—— schema 数量与磁盘不符，是文件加减后未同步的轻量漂移。

---

## Residual Risks

1. **`works/README.md` 改完之后，需要 grep 验证仓库其他 README / docs / prompts 是否还残留 `voice_rules.json` / `behavior_rules.json` / `boundaries.json` / `failure_modes.json`（作为独立文件名）的字面引用**。本轮未做全仓 grep；implementation track agent 自查报"automation/ 内已干净"，但未覆盖 `prompts/` / `simulation/prompt_templates/` / `docs/`。

2. **`current_status.md` §Project Stage 把 framework 状态与 first-work 的 Phase 3 进度混写在同一份文件**（`L13-L26` + `L38-L46`）。这份文件在 `main` 上，但描述的进度 (S001 sha / S002 sha / S003 ERROR) 实际只在 `extraction/{work_id}` 分支可见。语义上是 "记下当前活跃工作包的状态"——可工作；但作为 main 文件，它把 main 不可见的产物当作可见状态在描述。低风险但值得未来重新切分（或者明确"§Project Stage 的进度部分仅反映本地 extraction 分支状态"）。

3. **`schemas/_shared/` 不存在**（M1）的衍生：如果未来真出现跨域共享片段，按 `schemas/README.md` 当前文字引导，可能直接 `mkdir _shared/` + 放 schema 而不更新 README "当前为空" 那段—— 文档与磁盘的二元状态可能再漂移一次。建议在改 (a)/(b) 时一并锁住描述。

4. **`docs/architecture/schema_reference.md` 的 character / world / runtime 各小节具体字段说明未抽样核对**。本轮只查了头表数字 + analysis 节首段；如果 `target_baseline.schema.json` 在 character 节没有专门描述段，会构成更深层的索引漂移。下一轮 review 可定向查这一节。

5. **`works/我和女帝的九世孽缘/` 在本地存在但未跟踪**（artifact track agent 报告）：与 `.gitignore` `works/{!_}*/manifest.json` + `works/{work_id}/world,characters,indexes` 选择性放行的策略一致，没违规；但说明本机当前正在做 extraction，与 `current_status.md` Phase 3 in-progress 的叙述对应。提醒未来 `/go` 操作 main 时，preflight 会按 scope_paths 限制不阻塞这个本地目录，但 `extraction/{work_id}` 分支才是它的归属——若误在 main 上 `git add works/我和女帝的九世孽缘/` 会破坏 framework-only 政策。这是流程性残留风险，不是 bug。

---

## 建议落地顺序

1. **先 H1**：`works/README.md` 是入口文档，影响范围最广，改后大量歧义直接消失。改完 grep `voice_rules\|behavior_rules\|boundaries\.json\|failure_modes\.json` 全仓核对（涵盖 Residual Risk #1）。
2. **再 M2**：`docs/architecture/schema_reference.md` 头表 + character 节同步刷数；这是"几乎纯查表 / 改字"的工作，开销低。
3. **再 M1**：`schemas/_shared/` 走 (b) 路线（按需创建），同步刷 `schemas/README.md` + `ai_context/conventions.md` + `ai_context/decisions.md` 三处文字。
4. **最后 L1 / L2**：清理表述含糊与残留风险，可作为一个"文档清理"小 PR 合并。
