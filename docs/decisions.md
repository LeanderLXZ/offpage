# 决策 —— 完整条目 <!-- holo:heading -->

<!-- holo:section start -->
长文、权威的决策日志。这里是每条决策理据的单一事实来源；
`ai_context/decisions.md` 是它的 1–2 行索引。

两层分离：

- **本文件**（`docs/decisions.md`）—— 完整条目：决策陈述、理据、
  范围边界、指向权威来源（代码路径、文档段、change log）的指针。
  只按需读取 —— 永不进入会话开始的阅读清单。
- **`ai_context/decisions.md`** —— 每条决策 1–2 行的索引，用
  `→ docs/decisions.md #N` 指回这里。

这一对保持 lockstep —— 同全局编号、同主题分节；改其一必须在同一
趟内同步改另一个（追加 / 就地替换 / 删除永远落到两个文件）。若
项目在 `ai_context/conventions.md` §Cross-File Alignment 维护行，
可把这一对登记为一行。

条目格式 —— 编号块，通常 ≤ 5 行（永不为精简牺牲准确性；原始讨论
推到 `logs/change_logs/`）：

```
N. <决策陈述>。
   <理据 —— 为什么选它而不是备选>。
   <范围边界 / 实测事实，当其承重时>。
   → <指向权威来源的指针>
```

就地替换 / 删除遵循 `ai_context/decisions.md` §格式 —— 编号永不
移动；曾实际尝试后退回的被替换方案，条目里保留半行
`（曾试 X，退回，见 log）` 痕迹。
<!-- holo:section end -->

## 段（按主题组织） <!-- holo:heading -->

<!-- holo:section start -->
与 `ai_context/decisions.md` 的节标题完全一致；一条决策的归档条目
与其索引行位于相同的节下。
<!-- holo:section end -->

## Roleplay Philosophy

1. 优先级 = 深层行为 / 决策一致性，而非语气模仿。
   链条：记忆 + 关系 → 心理反应 → 行为 → 语言。

2. 客观事实与主观认知必须分离 —— 角色可能误解、隐瞒、扭曲。

3. 保留阶段差异；不压平成一份无时间维度的静态档案。
   → `project_background.md`、`simulation/prompt_templates/`。

## Data Separation

4. 用户数据与角色 canon 数据分离。用户侧永不漂移进 canon。

5. 世界是一等层级，不放在角色笔记内部。

6. 世界 canon 只凭源文证据修订 —— 永不因用户对话改动。

7. 冲突 / 修订显式记录，不静默覆写。
   → `conventions.md` §Data Separation + `docs/architecture/data_model.md`。

## Work Scope

8. 每部小说 = 独立命名空间（`work_id`）。用户流程先选作品、再选角色。

9. 中文作品：中文 `work_id`、实体名、标识符取值、路径段。

10. `ai_context/` 与 `docs/` 的书面语言跟随 `ai_context/skills_config.md` §Language 的 `content_language`（单源；当前 zh，2026-07-12 /holo:init 设定——曾为 English-only，随语言轴引入就地替换本条）。代码标识符与 JSON 字段名保持英文；内容文本 = 作品语言。
    → `conventions.md` §Naming + `ai_context/skills_config.md` §Language。
10a. `chapter_id` = `^C[0-9]{4}$`（4 位），`volume_id` = `^V[0-9]{3}$`（3 位，仅 light_novel source 使用）。位宽差异 = 预期基数（每作品章节 ≤ 9999，卷 ≤ 999）；字母前缀与 `S###` / `M-S###-##` ID 家族对齐。`chapter_index.schema.json` 的 `items` 是覆盖两个 profile 的 `oneOf`：**monolithic** profile（单卷非结构化作品 —— 禁止 6 个 light_novel 专属字段）与 **light_novel** profile（多卷结构化作品 —— required `volume_id` + `volume_seq` + `original_chapter_seq` + `original_sub_chapter_seq` 三层 seq，optional `volume_title` + `original_chapter_title`）。Profile 由 `manifest.structure_mode` 分派。**没有独立的 `volume_index.json`** —— `chapter_index` 承载全部交叉积信息。每个 `C####` 是一个 ingestion 单元（light_novel 下是 sub-section；monolithic 下是章）。**Phase 0 / 1 / 3 / 4 的 schema + prompt + 代码端到端消费 `C####`**（`chapter_summary_chunk.chapter`、`stage_plan.chapters` 为 `C####-C####`；light_novel 使用 start == end 的退化区间 `C####-C####`，phase 2/3/4 消费方按同一方式解析）；`extraction/persona_extraction/prompt_builder.py` + `extraction/persona_extraction/phases/scene_archive.py` 用 `C` 前缀构建路径与章 → stage 映射。卷 / 原书章的展示信息挂在 `chapter_index` profile-B 字段上、经派生的 `title` 呈现，不在 `stage_plan.chapters` 上。标识符改名审计用 `conventions.md` §Cross-File Alignment 的 4-form 清单。
    → `conventions.md` §Naming + §Cross-File Alignment、`schemas/work/chapter_index.schema.json`、`schemas/analysis/{chapter_summary_chunk,stage_plan}.schema.json`。

## Character Depth

11a. `identity.json` 承载 `core_wounds`（根源创伤 + 行为影响）+ `key_relationships`（含初始状态 / 演化 / 转折点的关系弧线）。与 stage snapshot 一起加载。**与 `target_baseline.json`（#13）并列的角色级常量文件** —— voice / behavior / boundary / failure_modes 内联进 stage_snapshot（#11d）。

11b. `behavior_state` 把 `core_goals`（理性、可重排优先级）与 `obsessions`（非理性、创伤 / 情绪绑定、不做成本收益计算）分开。`emotional_baseline` 以 `active_goals` + `active_obsessions` 呼应。

11c. `stage_snapshot` 内的 `character_arc` = 从 stage 1 → 当前的鸟瞰。与 `stage_delta`（仅上一步）互补。

11d. **角色 voice / behavior / boundary / failure_modes 内联在
     stage_snapshot 中。** Voice / behavior / boundary 状态位于
     `stage_snapshot.{voice_state,behavior_state,boundary_state}`；
     `failure_modes` 是 `stage_snapshot` 的顶层字段
     （4 个子类 `common_failures` / `tone_traps` / `relationship_traps`
     / `knowledge_leaks`；子类 maxItems 沿用历史 baseline schema 的
     取值）。每个 stage 记录完整的活跃失败模式集合
     （承接的 + 新激活的；已解除的移除），runtime 只读当前
     snapshot。S001 从源文 + identity 派生 baseline 种子；S002+ 从
     上一 snapshot 演化。
     `stage_delta` 顶层是 6-key structured object（per #55 —
     `trigger_events` / `personality_changes` / `relationship_changes` /
     `status_changes` / `mood_shift` / `voice_shift`），每个 sub-field
     的内容是叙述性 text（不是顶层 free-text 字符串）。
     `identity` 与 `target_baseline` 是角色级常量
     （两者都在 phase 2 产出）；runtime 加载
     identity + target_baseline + 当前 stage_snapshot。

11e. **maxItems 感知的裁剪规则（通用）。** 所有抽取
     prompt 必须指示 LLM 在抽取时就按 `maxItems` 上限
     排序 + 截断（而不是溢出后 schema fail），优先级锚点：
     当前 stage 相关性 → identity 锚点关系（core_wounds /
     key_relationships）→ 覆盖广度 → 跨 stage 稳定性（针对
     `failure_modes` 这类全量演化字段）。子类各自独立计
     maxItems；无跨字段全局上限。Spec →
     `extraction/persona_extraction/prompts/character_snapshot_extraction.md`
     §maxItems 触顶时的裁剪规则。

11f. **prev_stage 四态抽取规则。** 角色 snapshot prompt
     强制在抽取时对 prev_snapshot 显式区分四种状态：
     (A) 缺失 → 逐字继承；(B) 存在 + 有变化 →
     依当前源文重写，关键变化记入 stage_delta；
     (C) 存在 + 无变化 → 保留 prev（required 字段仍必须填，
     "无变化" ≠ "跳过"）；(D) 已解除 / 已揭示 / 已克服
     （针对 misunderstandings / concealments / failure_modes 等）→
     删除该条目并把解除原因写入 stage_delta。
     与 maxItems 裁剪不同：裁剪是"装不下"
     （不进 stage_delta）；解除是"语义闭合"（必须进
     stage_delta）。`stage_delta` 是 6-key structured object（per
     #11d / #55），(B) 关键变化与 (D) 消除原因写入对应 sub-field 的
     叙述性 text；"无明显变化" cop-out 显式禁止。Spec →
     `extraction/persona_extraction/prompts/character_snapshot_extraction.md`
     §核心规则 #2 (B/C/D 三态规则 + per-stage 推演原则)。
     → `schemas/character/` + `docs/architecture/schema_reference.md`。

## Extraction Model

12. stage（抽取）= stage（runtime），1:1。按自然故事边界
    （目标 10，最少 8，最多 15）。累积 1..N。`stage_id` = `S###`；
    同级 `stage_title`（短标签；上限在 schema 内）。

13. Phase 2 从全书上下文产出世界 foundation + per-character `identity.json`
    + per-character `target_baseline.json` 草稿
    （没有独立的 voice / behavior / boundary / failure_modes baseline
    文件 —— 那些住在 `stage_snapshot` 里）。`target_baseline.json`
    列出全部目标角色（`tier` ∈ {核心 / 重要 / 次要 /
    普通} + `relationship_type` 中文短 token，**灵活字符串
    （无 enum 门控）**，14 个默认候选 至亲 / 恋人 / 挚友 / 师长 /
    弟子 / 朋友 / 同僚 / 主人 / 下属 / 宠物 / 武器 / 对手 / 敌人 / 路人,
    当 14 个都不合适时允许兜底为更精确的表外词 ——
    必须在 `description` 里解释偏离原因；`tier` 与
    `relationship_type` 是正交轴 —— tier 普通 ≠ relationship
    路人）+ ≤100 字 description。`targets` 数组容量由
    `schemas/character/targets_cap.schema.json` 约束（单源 $ref；
    下游 stage_snapshot.{target_voice_map, target_behavior_map,
    relationships} 共享同一 fragment，调上限只动
    一个文件）。baseline 自 phase 3 起不可变。
    **Phase 3 硬约束（双向）**：三个结构
    `stage_snapshot.{voice_state.target_voice_map,
    behavior_state.target_behavior_map, relationships}` 的 keys 必须与
    `target_baseline.targets[].target_character_id` **集合相等** ——
    缺失或多出都硬性 fail。三个结构都以
    `target_character_id` 为 key（voice_map / behavior_map 从先前的
    `target_type` keying 迁移而来；`target_type` 保留为同级 metadata）。
    三态编码在**内容空满**上，不在 key 存在性上：
    已出场（累积）→ key 存在、字段正常填写；
    出现过但本 stage 未出现 → key 存在、继承 prev；从未
    出场 → key 存在、字段留空。**fixed_relationship
    例外**：`relationships[]` 中目标被
    `world/foundation/fixed_relationships.json` 条目绑定的 entry，即使
    目标从未出场也可预填关系字段（voice_map / behavior_map 等
    其他结构仍留空）。校验
    跑在 **phase 3 单 stage validate 层**（schema validate 的
    同级）；违规进入 file-level repair
    lifecycle（L1 json_repair → L2 repair cross-file checker
    `targets_keys_eq_baseline` → L3 re-extract）。Phase 3.5
    `consistency_checker.py` 不再承载这条规则。没有逃生
    舱；phase 2 漏了目标就手工修 baseline 并
    重跑受影响 stage。Phase 3
    每 stage 做 1+2N 拆分抽取（1 world + N char_snapshot +
    N char_support）；任何 stage 都可（经 char_support）修正 identity，
    但**永不**写 target_baseline。

14. 没有 per-stage 报告文件；进度就地记录。

15. `target_voice_map` / `target_behavior_map` 条目全部以
    `target_character_id` 为 key（与 `baseline.targets[].target_character_id`
    集合相等，见 #13）；详略随 `tier` 变化 —— 核心 / 重要目标
    ≥3–5 个示例，次要 / 普通目标保持简短，从未出场的
    baseline 目标保留空 entry（D4 状态 3）以维持跨文档
    集合相等。Runtime 只加载与用户角色匹配的条目：
    canon 角色 → 按 `target_character_id` 精确匹配；OC 角色 →
    按 role_binding 亲和度经条目的 `target_type` 同级标签
    （保留为 metadata）兜底匹配。当前 snapshot 无匹配
    条目时，向前扫描历史 snapshot
    （纯代码 I/O）。
    → `architecture.md` §Automated Extraction Pipeline + `extraction/README.md`。

## User Model

16. 一个 `user_id` = 一个锁定的 作品-目标-对手方 绑定。Setup 时锁定；变更需要新 package 或显式迁移。

17. 有 canon 依据的用户角色默认继承目标 stage。

18. 会话 / 上下文状态持续更新。长期档案 + 关系内核只在显式 merge 确认后更新。

19. Per-context 的 `character_state.json` 实时跟踪情绪、性格、语气、约定、关系增量、事件、记忆 —— 仅在 merge 时晋升为长期。

20. Merge 是 append 优先。事件 / 记忆只添加，永不覆写。

21. 会话关闭是显式动作。系统询问是否 merge。

22. 完整逐字稿留在本地；启动只加载摘要层。
22a. `relationship_core/` 拆分 —— `manifest.json`（单对象状态）+ `pinned_memories.jsonl`（append-only）。Merge 只写 append。Schema：`schemas/user/pinned_memory_entry.schema.json`。
22b. Append-only 流用 `.jsonl`；单对象状态用 `.json`。权威扩展名列表 → `docs/architecture/data_model.md`。

## Automated Extraction (non-obvious)

23. 每次 phase 调用都是全新的 `claude -p` / `codex` —— 无共享会话
    记忆。步骤间上下文基于文件。

24. 抽取 prompt 不读 `memory_digest.jsonl`、`world_event_digest.jsonl`、`stage_catalog.json`。自包含的 snapshot 契约内嵌在 prompt 中；digest / catalog 由 `post_processing.py` 程序化维护（0 token，幂等）。

25. Per-stage 质量门 = `repair`（统一的 check + fix + verify）。Checker L0–L3 × fixer T0–T3，正交；field-level json_path patch。Phase B L3 gate 抓假 "fixed" 声明。每文件最多 `max_lifecycles_per_file=2` 个完整 check→fix→verify lifecycle：lifecycle 1 可调 T3（带 `prior_attempt_context`，概括上一 lifecycle 修了什么、还有什么没过）；T3 一触发 lifecycle 即返回、状态机 reset 进入 lifecycle 2；lifecycle 2 禁用 T3 —— 任何将调 T3 的升级以 `T3_EXHAUSTED` 结束。**repair 接入点 = phase 3 stage loop + phase 2 baseline lanes**（phase 3：`orchestrator.py` stage loop 的 per-file `run_repair(...)`，完整 L0–L3 × T0–T3；phase 2：`run_baseline_production` per-lane 缩水版接入——T0/T1 + schema/程序 checker，L3 / T2 / triage 不开，T3 = lane 重跑，见 #59；phase 0 / 1 / 3.5 / 4 各自走原生 retry 路径，不经 repair）。Phase 3 按文件并行分发（默认并发 10）；跨文档一致性放在 Phase 3.5。**Disambiguation**：本条 L0–L3 × T0–T3 是 phase 3 stage 抽取产物的 per-file repair lifecycle（checker × fixer 二维矩阵 + Phase A→B→C lifecycle）；与 #40 (phase 0 JSON repair L1/L2/L3) 同名不同物——后者是 JSON 格式修复三档阶梯（L1 regex 0 token / L2 LLM 修破碎 JSON / L3 整 prompt full re-run），互不依赖。同字面 "L1/L2/L3" 在两处语义完全不同。 → `extraction/repair/` + `docs/requirements.md` §11.4。
    > **经 #62 收紧**：fixer 收为 T0–T2；删 T3 `file_regen` 全文重跑、
    > `max_lifecycles_per_file` 与 `T3_EXHAUSTED`——单轮 Phase A→B→C，不再有
    > lifecycle 2；phase 2 侧 "T3 = lane 重跑"（`lane_regen`）亦已删（见 #59）。
    > `route_tiers` 按 issue rule 分配 `(start_tier, max_tier)`，每 tier 封顶 2 次
    > 尝试；`coverage_shortage` → T2 + 0-token SourceNote 接受；未决残留按
    > `DEFERRABLE_CATEGORIES` defer（见 #60）。
25a. 源文差异分诊（`triage_enabled=True`）—— 两条 accept 路径共享每轮 `accept_cap_per_file=5`：(A) L3 `source_inherent`（LLM）凭逐字引用证据（字面子串 + SHA-256 锚定）接受作者笔误残留；(B) L2 `coverage_shortage`（0 token）在一次 T2 尝试后经程序选定的 SourceNote 接受 `min_examples` 不足。两者都以 append-only 持久化到 `{entity}/canon/extraction_notes/{stage_id}.jsonl`（或 `world/extraction_notes/`）。Runtime 不消费（仅审计）。Phase 3.5 把有效 SourceNote 视同满足 `min_examples`。→ `extraction/repair/` + `docs/requirements.md` §11.4。
    > **经 #62 收紧**：单轮 Phase A→B→C，无 lifecycle 2 —— 原「每 lifecycle
    > 共享 accept_cap」改为每轮共享；原「Lifecycle 2 从磁盘读回已接受的指纹」
    > 与「T3 输出直接流入 lifecycle 2、之后不设即时损坏门」两条随 lifecycle 2
    > 与 T3 一并删除。triage 现在的两个调用点是 tier 封顶后的 residual
    > （round 1）与 L3 gate 之后（round 2）。

26. 抽取跑在 `extraction/{work_id}` 分支上。每个通过的 stage 都提交。回滚 = `git reset`。**完成后 squash-merge 到 `library`**（永不进 `main`）。三分支模型：`main` = 仅框架，推送远端；`extraction/{work_id}` = 单作品进行中，本地；`library` = 完结作品归档，本地。`library` 通过周期性 `git merge main` 吸收框架更新；没有任何东西回流 main，保持对外分支无产物。Squash 目标由 `[git].squash_merge_target` 控制（默认 `library`）。**squash 成功后 orchestrator 交互式询问（`[y/N]`，默认 N）是否删除源 `extraction/{work_id}` 分支（`git branch -D`）并运行 `git gc --prune=now`**，让累积的 regen commit 变为不可达并被回收。Dispose 永远是交互式的 —— 即使 `[git].auto_squash_merge=true`，dispose prompt 仍会询问，因为删除分支不可逆。用户一旦选择删除，`library` 的 squash 就是唯一保留的记录。这使 `extraction/{work_id}` 成为可丢弃的 scratchpad：失败的 regen 可以随意提交，而不污染 `library` 历史或长期磁盘占用。

27. Orchestrator 预先计算每次调用的读取清单（仅最新 snapshot + memory_timeline）。Agent 不自由探索。
27a. Manifest 按 writer 拆分：`sources/*/manifest.json` 手写（validator 门控）；`works/*/manifest.json` + `works/*/world/manifest.json` 程序化。活跃 phase 状态在 `analysis/progress/`，不在 manifest。
27b. **Bounds-only-in-schema。** 所有 `maxLength` / `minLength` / `maxItems` 只存在于 `schemas/**.schema.json` —— `config.toml`、L2、docs、ai_context、prompt 里不留副本。L2 只保留 schema 表达不了的检查。唯一的程序兜底（`StructuralChecker.relationship_history_summary_max_chars`）必须跟踪 `stage_snapshot.schema.json`。跨 schema 共享同一个 bound 数值用 `$ref` 指向共享 fragment，fragment 放在使用它的领域目录下（例如 `schemas/character/targets_cap.schema.json` 由 `target_baseline.targets` + stage_snapshot 的三个 target 结构共享 —— 两个文件都在 `schemas/character/`，fragment 就放那里）。`extraction/persona_extraction/core/schema_loader.py` 的内联 loader 在加载时解析这些引用，让任何 draft validator 看到自包含的 schema（当前所有调用点 —— orchestrator、validator、scene_archive、repair —— 都用 `Draft202012Validator`，匹配 schema 文件里的 `$schema: draft/2020-12/schema`）。这**不是**副本 —— 仍然单源。
27c. 任何 schema（world / character baselines / `stage_snapshot` / `memory_timeline`）都不携带 `evidence_refs` / `source_type` / `scene_refs`。章节回溯放在 schema 之外；runtime 锚定用 `timeline_anchor`（world 上另有 `location_anchor`）与 `memory_timeline`。
27d. Digest + memory 的时间地点：required 短锚点从 world snapshot 的 `timeline_anchor` / `location_anchor` 拷贝。`memory_timeline.scene_refs` 已移除（`scene_archive` 上有 FTS5）。
27e. `foundation` / `fixed_relationships` / `stage_catalog` 已做 bound 收缩。`fixed_relationships.{source_type,evidence_refs}` 移除；`stage_catalog.order` 移除（按 `stage_id` 字典序排序）；角色 catalog 在 `schemas/character/stage_catalog.schema.json`；占位的 `*_summary` 字段删除。
27f. 角色 `stage_snapshot` 全体 bound 收缩：新增 required `timeline_anchor` + `snapshot_summary`；新增 `boundary_state.hard_boundaries`（与 baseline 同级）。
27g. `stage_snapshot` 结构裁剪：`character_arc` 是短字符串（原为对象）；顶层 `memory_refs` / `evidence_refs` 移除；每条 `dialogue_examples` / `action_examples` 的 per-item `evidence_ref` 移除。
27h. `world_stage_snapshot` 结构裁剪：`character_status_changes` 移除（per-character 状态变化属于角色 `stage_snapshot` / `memory_timeline`；world snapshot 只保留公共世界层）；`evidence_refs` 移除（没有 schema 保留章节锚点）。schema 内字段级 `maxItems` / `maxLength` 收紧；`stage_events` 由 50–80 放宽到 50–100 CJK 字。
27i. **schema-gate-as-retry-trigger 模式。** L1 `jsonschema` 校验充当 LLM 输出失败的又一重试触发器（与 JSON 解析失败、stage 上限违规等同级）；首个失败注入下一次重试的 prompt：Phase 0 / Phase 1 / Phase 4 经 `{retry_note}` 占位符 + `prior_error` 参数（Phase 1 把该模式 fan-out 到 3 条独立 lane，每 lane 有自己的重试预算 —— 见 #52）。覆盖 5 个 schema：`schemas/analysis/{chapter_summary_chunk,scene_split,stage_plan,candidate_characters}.schema.json` + `schemas/world/foundation.schema.json`（decision #54 — foundation 前移到 phase 1 后 schema 归位 `schemas/world/` 域；原 `schemas/analysis/world_overview.schema.json` 已删除）。Plumbing → `extraction/persona_extraction/orchestrator.py:_summarize_chunk + run_analysis`、`scene_archive.py:validate_scene_split`、`prompt_builder.py:build_summarization_prompt(prior_error) + build_scene_split_prompt(prior_error) + build_foundation_prompt(prior_error) + build_stage_plan_prompt(prior_error) + build_candidate_characters_prompt(prior_error)`。与 #27b（Bounds-only-in-schema）配对：bound 定义在 schema 里，执行经既有重试路径落在 pipeline 中。
27j. **Phase 0/1 双模式经 `structure_mode` 分派。** Source manifest
     携带 `structure_mode: "monolithic" | "light_novel"`（**required** ——
     `work_manifest` / `works_manifest` 两个 schema 都列入 `required`，缺值
     过不了 schema gate；无隐式默认填充）；works manifest
     在 Phase 1.5 拷贝它。Source
     manifest 是单一真源 —— `extraction/ingestion/
     validator.py` 把 `structure_mode` 与
     `chapter_index` profile 交叉校验（见 #27k）；`manifests.write_works_manifest`
     前向拷贝该值并断言相等。**`monolithic`** =
     既有的 token 预算分 chunk（Phase 0）+ LLM stage 边界
     发现（Phase 1）。**`light_novel`** = `1 sub-section = 1 C-id =
     1 Phase 0 chunk = 1 Phase 1 stage`；Phase 0 设
     `chunks = [[c] for c in chapter_index]` 并跳过 token 预算
     分批；Phase 1 从 `chapter_index` 1:1 派生 `stage_plan`
     （无边界发现 LLM 调用）并绕过 STAGE_MIN /
     STAGE_MAX `chapter_count` 校验。Phase 2+ 不分叉 ——
     统一消费 `stage_plan`；卷 / 印刷章
     语义挂在 `chapter_index` profile-B 字段上，character /
     world schema 不动。**`structure_mode` 的判定**由
     规范化 prompt 内的 LLM 驱动（`prompts/ingestion/
     原始资料规范化.md` 任务步骤 2）：扫描 source 目录 / 文件名 /
     卷标记 + 章节抽样，产出 `判定 + 依据 + 置信度`，
     然后门控 —— 置信度 ≥ 0.8 直接填 `manifest.structure_mode`；
     < 0.8 停下询问用户；任一信号被标
     "不确定" 时置信度封顶 0.7（强制走人工确认路径）。
     `light_novel` 要求三个信号齐备（卷分隔符 +
     卷数 ≥ 2 + 可识别的章内 sub-section）——
     单卷情形兜底到 `monolithic`。
     → `schemas/work/{work_manifest,works_manifest,chapter_index}.schema.json`
     （source 侧 `work_manifest` 与 canon 侧 `works_manifest`
     都声明该字段；canon 侧由 `manifests.write_works_manifest` 拷贝），
     `extraction/ingestion/validator.py`、`extraction/persona_extraction/
     {manifests,orchestrator}.py`。
27k. **`chapter_index.schema.json` `items` = 两个 profile 的 `oneOf`。**
     **monolithic profile**：`additionalProperties: false`，禁止
     `volume_id` / `volume_title` / `volume_seq` /
     `original_chapter_seq` / `original_sub_chapter_seq` /
     `original_chapter_title`。**light_novel profile**：required 的
     三层 seq 三元组 `volume_id`（`^V[0-9]{3}$`）+ `volume_seq`
     （≥1）+ `original_chapter_seq`（≥1）+ `original_sub_chapter_seq`
     （≥1），optional `volume_title` + `original_chapter_title`。
     三层映射：`volume_seq` = 书内 1-based 卷序号；
     `original_chapter_seq` = 卷内 1-based 原书印刷章序号
     （每卷重置）；`original_sub_chapter_seq` =
     原书印刷章内 1-based sub-section 序号（每
     原书章重置）。`title` 无论哪个 profile 一律 required（minLength 1）；
     `chapter_id`（`^C[0-9]{4}$`）/ `sequence`
     / `normalized_path` 两个 profile 都 required。下游 Phase 0 /
     3 / 4 只消费 `chapter_id` —— `stage_plan.chapters` 两种模式下都保持
     `C####-C####`（light_novel 用 start == end 的退化区间
     `C####-C####`，既有解析器无需改动）；
     卷 / 原书章展示信息挂在
     `chapter_index` profile-B 字段上、经派生的
     `title` 呈现。
     → `schemas/work/chapter_index.schema.json`、`prompts/ingestion/
     原始资料规范化.md`。
27l. **`light_novel` 的 `title` 由规范化派生。** 公式：
     `f"{volume_title or '第N卷'} {original_chapter_title or '第M章'}
     {original_sub_chapter_seq}"`，其中 `N = volume_seq`、
     `M = original_chapter_seq`。optional 字段带占位符
     兜底，保证 `title`（schema required，minLength 1）总能
     纯靠 required 字段填出。示例：`volume_seq=1`、
     `volume_title=None`、`original_chapter_seq=2`、
     `original_chapter_title=None`、`original_sub_chapter_seq=3` →
     `title = "第1卷 第2章 3"`。规则住在规范化侧（prompt +
     下游最终代码路径），不在抽取代码里，所以 Phase
     1 / Phase 3 消费方看到的是已填充的 `title` 字段。Monolithic
     模式：`title` 继续是从 source 目录拷贝的人类可读
     章节标题。**代码侧软截断保障**：
     `_build_light_novel_stage_plan` 在公式完整输出会超上限时把产出的
     `stage_title` 截断到 schema 上限（启动时经
     `_stage_title_max_length()` 从
     `stage_plan.schema.json::stages.items.properties.stage_title.maxLength`
     动态读取，保持 §27b 单源）并加
     `…` 省略号，使对抗性的超长 volume_title × original_chapter_title
     组合不会在 `stage_title.maxLength` schema fail 上
     触发无限 Phase 1 重试循环。
     → `schemas/work/chapter_index.schema.json`、`schemas/analysis/
     stage_plan.schema.json`（`stage_title.maxLength`）、`prompts/
     ingestion/原始资料规范化.md`、`extraction/persona_extraction/
     orchestrator.py::_build_light_novel_stage_plan`。
27m. **`chapter_summary_chunk` 上的 chunk 级二级字段。** Phase 0
     chunk schema 在 per-summary 事件事实之外，携带 5 个聚合
     每个 chunk 的世界 / 力量 / 势力 / 地域 / 弧光信号的
     chunk 级二级字段：`chunk_arc_summary`
     （required，≤200 字）、`chunk_world_rules[]`（maxItems 5，items
     `{rule, description, observed_impact}`，`required: [rule]`）、
     `chunk_power_levels[]`（maxItems 20，items `{name, description}`，
     `required: [name]`）、`chunk_factions[]`（maxItems 20，items
     `{name, description, members_present[]}`，其中 `members_present`
     存 **raw** 的 chunk-LLM 可见名 —— 化名 / 真名 / 称呼
     任一 —— 而非 `character_id`，因为身份合并在 Phase
     1.5 之后；`required: [name]`）、`chunk_regions[]`（maxItems 20，items
     `{name, description}`，`required: [name]`）。所有子对象
     `additionalProperties: false`。Per-summary 侧：`location` 移除
     （由 `chunk_regions` 覆盖）；`summary` 150–200 CJK 字（须装下
     事件描述 + 设定上下文）；`key_events` 移除（#52 fan-out 后
     没有 Phase 1 lane 投影它，Phase 2 baseline 也不读
     它 —— stage 边界信号现在来自 per-summary `summary`
     加宽 + chunk 级 `chunk_arc_summary`）。`chunk_world_rules.observed_impact` 由 prompt 要求
     在无观察时兜底为字面字符串 "未在本 chunk 直接观察"，
     而非静默留空（历史 anchor，原服务 phase 2 foundation 产出
     时的 `core_rules.impact` 综合；foundation 现由 phase 1 foundation
     lane 直接产，`core_rules` 保留为 `string[]` 形态——见 #54）。
     **Phase 1 foundation lane 映射**（决策 #52 + #54）：
     `chunk_world_rules → foundation.core_rules`（string[] 形态，跨
     chunk 合并去重） / `chunk_power_levels → power_system.levels` /
     `chunk_factions → major_factions`（含 `key_figures` raw 名——
     `members_present[]` 跨 chunk 合并去重直接写入，**双阶段语义**：
     phase 1 写 raw 名 / phase 2 LLM 替换能匹配 candidate_characters.aliases
     的为 character_id，匹配不上保留 raw 名；决策 #54 修订段） /
     `chunk_regions → world_structure.major_regions` /
     `chunk_arc_summary → world_lines.core_conflict`。**Phase 2 不再
     产出 foundation** —— foundation 完全由 phase 1
     foundation lane 落盘到 `works/{work_id}/world/foundation/foundation.json`，
     phase 2 只在 baseline 阶段做"替换"工作：把 `foundation.major_factions[].key_figures`
     内 raw 名（phase 1 写入）替换为 character_id（能匹配 candidate_characters.aliases
     的换，匹配不上保留 raw 名；决策 #54 修订段）。显式
     **未新增**：`chunk_fixed_relationships[]`（chunk 视野 ≤25
     章无法判断"贯穿全书"，会污染
     `world/foundation/fixed_relationships.json`）；
     `chunk_setting_features`（与 `chunk_world_rules` /
     `chunk_power_levels` / `chunk_factions` / `chunk_regions` 重叠 ——
     `world_structure.summary` / `world_lines.setting_features` 由
     Phase 1 LLM 从这四个字段综合）。`members_present`
     **双管道进 `foundation.major_factions.key_figures`**：
     phase 1 foundation lane 把 `members_present[]` 跨 chunk 合并去重
     直接写入 `key_figures`（raw 名形态，不做身份合并）；phase 2 baseline
     LLM 把能匹配 `candidate_characters.aliases` 的 raw 名替换为
     `character_id`，匹配不上保留 raw 名（决策 #54 修订段）。`members_present`
     同时也由 phase 1 candidate_characters lane 用做跨 chunk 身份合并
     （并行 lane，foundation lane 不依赖 candidate_characters lane 结果）。
     → `schemas/analysis/chapter_summary_chunk.schema.json`,
     `schemas/world/foundation.schema.json`,
     `extraction/persona_extraction/prompts/{summarization,analysis_foundation,baseline_key_figures}.md`（phase 2 侧 lane 拓扑见 #59）,
     `docs/architecture/{extraction_workflow,schema_reference}.md`.
27n. （2026-07-13 由重复的 "27m" 改号，语义不变）**stage_plan 切分语义 = 拐点先行，章数硬范围；prompt 反锚定 +
     `default_stage_size` 字段下线。** 旧设计在 `analysis.md` §步骤 2 +
     JSON 示例 + schema 字段三处同时锚定 "10 章"，LLM 实际产出落入
     "先按 10 章等分、再给每段挑剧情节点写 boundary_reason" 的偷懒
     模式（实证：537 章 / 53 stage 中前 38 个全是恰好 10 章）。新设计：
     (1) 程序式三子步流程——2.1 通览 chunk 输出列出全书所有剧情拐点
     候选（章号 + 类型 + 一句话事件）；2.2 沿章序把相邻拐点合并成
     stage（章数 8-15 hard，schema `chapter_count.minimum=8` /
     `maximum=15` 双向硬挡 LLM 输出（monolithic 路径走 schema-gate-as-
     retry-trigger 决策 #27i 注入 prior_error）+ orchestrator
     `_check_stage_plan_limits` 作 belt-and-suspenders 二次兜底；
     light_novel 派生路径事实上不走 schema validate（既不在 phase 1
     `lanes` 列表也无主动 validate 调用），程序产出可信，`chapter_count=1`
     在新 schema 下 schema-invalid 是已知 trade-off——若未来某外部工具
     加入对 light_novel 产物的 schema 校验需切到 schema oneOf + structure_mode
     dispatch 形态，当前没有此调用点）；2.3 反锚定自检（≥3 连等章数视为
     机械等分必须重审 +
     `boundary_reason` 必须对应 2.1 拐点章号）。(2) JSON 示例改为非
     整数倍混合（8 章 + 13 章），打破 "10 是甜区" 暗示。(3) schema
     字段 `default_stage_size` 整体删除——单一真源 = `chapter_count`
     bounds；连带删 `Phase3Progress.stage_size` dead metadata 字段
     与 orchestrator 三处读写位、`work_manifest.schema.json::extraction.default_stage_size`
     孤立字段。Plumbing → `schemas/analysis/stage_plan.schema.json`、
     `schemas/work/work_manifest.schema.json`、
     `extraction/persona_extraction/prompts/analysis_stage_plan.md` §步骤 2（步骤 2.1/2.2/2.3 三子步反锚定自检；详见 #52 Phase 1 三 lane 拆分）、
     `extraction/persona_extraction/orchestrator.py` + `extraction/persona_extraction/lifecycle/progress.py`、
     `docs/architecture/schema_reference.md`。

## Memory System

28. 三层记忆（`stage_snapshot` / `memory_timeline` / `scene_archive`）。没有独立的对话语料库。

29. ID 约定 `{TYPE}-S{stage:03d}-{seq:02d}`，用于 `M-` / `E-` / `SC-`。3 位 stage ≤999，每 stage 2 位 seq ≤99。stage 编码在 ID 内。**Digest 条目**（`memory_digest.jsonl` / `world_event_digest.jsonl`）不携带独立的 `stage_id` 字段 —— stage 从 ID 前缀解析。**`scene_archive` 条目确实携带 `stage_id`**（来源 `stage_plan.json`，见 §11.x scene_archive 段），与 stage 编码的 `scene_id` 并存，因为 runtime 检索按 stage 建索引、每次查询都重新解析太浪费。三层的故事时间字段统一为 `time`。

30. 模拟角色 A 时只加载 `characters_present` 含 A 的场景与 A 自己的 `memory_timeline`。

31. `stage_events` 仅限世界公开层（50–100 CJK 字，硬门）。个人 / 内在条目属于角色 `memory_timeline`，永不进 world。

32. `world_event_digest.summary` = 源 `stage_events` 的 1:1 拷贝（写入时由 prompt + repair agent 强制）。5 级重要度按关键词推断；默认 significant。

33. `memory_digest.summary` = `digest_summary` 的 1:1 拷贝（30–50 CJK 字，硬门）。

34. 角色 `stage_snapshot.stage_events` = 仅本 stage（50–80 CJK 字，硬门），不累积。跨 stage 历史在 `memory_timeline` + `memory_digest` + `world_event_digest`。

35. `fixed_relationships.json`（血缘 / 宗族 / 阵营）不依赖 stage。Phase 2 出骨架；后续 stage 可修正。Runtime Tier 0。

## Retrieval

36. 两级漏斗：Level 1 jieba + 词表 dict + FTS5（<20ms，默认）；Level 2 经 LLM tool use 的 embedding（罕用）。单一 SQLite —— 无独立向量库。

37. 主动式上下文状态联想：引擎每轮抽取地点 / 近期事件 / 情绪 / 对话对象做 jieba 匹配 —— 不只匹配用户输入。

38. 词表 dict（作品级，jieba 自定义格式）由抽取产物自动生成。`works/{work_id}/indexes/vocab_dict.txt`（提交）。

39. 检索产物放在 `works/{work_id}/retrieval/`（不提交）。Phase 4 中间产物 `works/{work_id}/analysis/scene_splits/` 必须不被 git 跟踪（否则回滚 `git checkout --` 会静默销毁它们）。`scene_archive.jsonl` 在 merge 时全量重新生成。
39a. Phase 4 章级同轮重试 —— FAILED 章在同一 pass 内重新排队并注入 `prior_error`。预算 `[phase4].max_retries_per_chapter`（默认 2；总尝试 = 1 + 预算）。耗尽 → ERROR，推迟到 `--resume`。熔断只统计终态失败章。
     → `architecture.md` §Automated Extraction Pipeline → Phase 4。

## JSON Repair

40. LLM 产出的 JSON 常有格式错误（未转义引号、
    尾逗号、截断）而内容完好。Phase 0 三级
    修复：L1 regex（0 token）→ L2 LLM 只修破碎 JSON
    （最小化）→ L3 全量重跑（最后手段）。**Disambiguation**：本条
    L1/L2/L3 是 phase 0 chunk-level JSON 格式修复三档阶梯（仅 phase 0
    `_summarize_chunk` 使用）；与 #25 (repair L0–L3 × T0–T3)
    同名不同物——后者是 phase 3 stage 抽取产物的 checker × fixer
    二维矩阵 + Phase A→B→C lifecycle。同字面 "L1/L2/L3" 在两处语义
    完全不同；互不依赖。
    → `extraction/persona_extraction/core/json_repair.py`。

## Configuration & Runtime Resilience

45. 单源 TOML 配置在 `extraction/config.toml`（loader
    `extraction/persona_extraction/core/config.py`）。覆盖优先级：
    CLI > `config.local.toml` > `config.toml` > dataclass 默认值。
    Section：`stage / phase0 / phase1 / phase3 / phase4 / repair
    / backoff / rate_limit / runtime / logging / git`。

46. Token 限额自动暂停（订阅模型，§11.13）—— `RateLimitController` 解析 DST 感知的 reset，写 flock 合并的 `rate_limit_pause.json`，在预启动 + 每次 `run_with_retry` 处阻塞，reset 后重跑失败的 prompt 且不消耗重试槽。无法解析的 reset → probe 循环（单一选举 leader）。硬停（weekly ≥ `weekly_max_wait_h` 默认 12h；probe ≥ `probe_max_wait_h` 默认 6h）→ exit 2 + `rate_limit_exit.log`。暂停不计入 `--max-runtime`（按 `resume_at` 去重）。→ `docs/requirements.md` §11.13 + `extraction/persona_extraction/core/rate_limit.py`。

47. Phase 0 摘要子进程超时 = `[phase0].summarize_timeout_s`（默认 1800s），而不是历史上借用的 `[phase3].review_timeout_s`（600s）。原因：一个 Phase 0 chunk 读 `chunk_size` 章（默认 20），并在 opus-4-7 effort=max 下产出 N× per-summary（100–150 字）+ 5 个 chunk 级二级聚合（`chunk_arc_summary` / `chunk_world_rules` / `chunk_power_levels` / `chunk_factions` / `chunk_regions`）；运行时证据表明 wall > 600s 属正常。`phase3.review_timeout_s` 保持 600s，服务它真正对应的 phase 3 reviewer 短链。→ `extraction/config.toml` `[phase0]`、`extraction/persona_extraction/core/config.py::Phase0Config`、`extraction/persona_extraction/orchestrator.py:_summarize_chunk`。

48. **长度 bound 容差门（B 方案）。** 当一个 LLM 驱动的 phase 已耗尽其严格重试预算——各 phase 的耗尽点：Phase 0 `_summarize_chunk` L1+L2+L3 全跑完 / Phase 1 per-lane `exit_validation_max_retry` 耗尽 / Phase 2 per-lane repair 走完后的终点 `validate_baseline` 失败（lane 内的 `LENGTH_TOLERANCE_PASS` 分支同样适用，#59） / Phase 4 scene-split `max_retries_per_chapter` 耗尽 / **Phase 3 repair framework 的 tier 封顶之后**（每 tier ≤2 次，`max_tier` 用尽即触发；#62 删 T3 后由 `T3_EXHAUSTED` 改为封顶触发）（**phase 3 + phase 2 经 repair 路径**，接入形态见 #25 / #59；phase 0 / 1 / 3.5 / 4 不接入 repair）——最后一遍调用 `validate_with_length_tolerance`（helper 在 `extraction/validation/shared/schema_tolerance.py`）：若严格失败列表**只**含 `minLength`/`maxLength` 违规，且放宽后的 schema（每个 `minLength` × 0.9 下限、每个 `maxLength` × 1.1 上限）通过，则把产物接受为 PASS；否则保留原失败。其他所有约束（`required` / `type` / `enum` / `pattern` / `minimum` / `maximum` / `minItems` / `maxItems`）保持严格。**不适用**于 `post_processing.py` 纯程序产出的 digest/catalog——那些没有 LLM 边缘抖动，容差会掩盖代码 bug。容差通过的产物**不打 metadata 标记**（下游消费方不区分 strict-pass 与 tolerance-pass）。与 #27i（schema-gate-as-retry-trigger）配对：严格重试路径先跑到耗尽；容差是最终安全阀，不是重试的替代品。与全局 `[phase3].max_turns = 80`（原为 50）和 `--chunk-size` 默认 `20`（原为 25）配对——两者都降低边界抖动撞上耗尽的频率。Plumbing → `extraction/validation/gates/phase2_baseline.py` (helpers)、`orchestrator.py:_summarize_chunk + run_analysis + run_baseline_production`、`scene_archive.py:_handle_validation_failure`、`extraction/repair/coordinator.py`（`_run_fixer_with_escalation` 的 tier-封顶后分支 → `LENGTH_TOLERANCE_PASS`；phase 2 + phase 3）。

49. **Phase 0 降档 effort 的恢复扫尾（per-chunk 定向救火）。** opus-4-7 effort=max 在 phase 0 的多字段 chunk 综合（读 `chunk_size` 章 → 写 N× per-summary + 5 个 chunk 级二级聚合）上随机触发超出 1800s 子进程 wall 预算的服务端超长 thinking。实证观察到 `<work_id>` 的 chunk 8 在两个不同章节范围（v2: C0176-C0200、v3: C0141-C0160）均出现——都在 effort=max ×2 重试下超时，都在 effort=high 下 ~14 分钟 wall 完成（schema 合法输出，质量等同）。与其把 phase 0 整体降档到 effort=high（会轻微拉低 95%+ 不触发长 thinking 边缘情况的 chunk 的质量），orchestrator 在 phase 0 主 ThreadPool 结束后跑一次**恢复扫尾**：任何 `state == 'failed'` 且 `error_message` 含 `'timed out'` 或 `'error_max_turns'` 且 `recovery_attempted == False` 的 chunk 用 `effort='high'` 重跑一次（经 `LLMBackend.run` 的 per-call kwarg，不换 backend 实例），复用 `phase0.concurrency`（ThreadPoolExecutor max_workers）。无论结果如何都标记 `recovery_attempted=True`；后续 `--resume` 跳过已尝试过的 chunk（无无限救火 loop）。完整重试管线（L1/L2/L3 JSON repair + jsonschema gate + 长度 bound 容差 #48）按既有契约在 `_summarize_chunk` 内运行——扫尾只改 effort，不改重试语义。Plumbing → `extraction/persona_extraction/core/llm_backend.py::LLMBackend.run`（新增 `effort: str | None = None` kwarg）、`orchestrator.py::_run_recovery_sweep`（新方法，`run_summarization` 主池结束后调用）、`progress.py::ChunkEntry`（新增 `recovery_attempted: bool = False`）、`config.py::Phase0Config.recovery_effort` + `extraction/config.toml [phase0] recovery_effort`。

50. **Post-processing 对 derived digests 永远走 replace-slice 语义。** `generate_memory_digest` 与 `generate_world_event_digest` 把当前 stage 的派生条目写入 `memory_digest.jsonl` / `world_event_digest.jsonl`：当前 stage 旧条目被新条目替换，其它 stage 条目保留。**当前 stage 派生数组为空（`memory_timeline` 0 条 / `stage_events` 0 条 — schema 合法）也必须落盘 replace-slice**——读 existing → drop `_stage_from_id(...) == current_stage_num` 的旧条目 → write 剩余条目。否则 repair 删空一个 stage 的源数组、再跑 post-processing 时旧 digest slice 留在 JSONL 里，与 #32 / #33 的 1:1 拷贝契约 + Phase 3.5 #27i schema-gate 一致性检查（见 `consistency_checker._check_memory_id_correspondence` / `_check_world_event_digest`）撞车。空源数组仍 emit warning issue 让 caller 收（信息提示，方便人工核查"这阶段是不是真的没事件"），但实际 IO 必须发生。Plumbing → `extraction/persona_extraction/phases/post_processing.py::generate_memory_digest` + `generate_world_event_digest`。

51. **CLI `--resume` 阶段无关续跑契约。** `extraction/persona_extraction/cli.py` 的 `--resume` 是 `run_full` 的 auto-yes 信号——`run_full` 是 resume entry point，按 phase 顺序自检 + skip + self-heal（Phase 0 schema-gated chunk skip / Phase 1 产物存在则跳过 / Phase 1.5 用 `--characters` 旁路 / Phase 3 reconcile_with_disk + 从 `stage_plan.json` rebuild `phase3_stages.json`）。`--resume` 标志只 silent run_full 内 `input("Resume from existing progress? [Y/n]: ")` 这条交互确认；与磁盘上具体哪个 phase 已落盘无关。`--background` 与 `--resume` 正交：`--background` 校验阶段感知双分支，读 `pipeline.json::phases.phase_1_5`——未 done 则强制要求 `--characters`（跳过 `confirm_with_user` 第一个 character 选择 input；end_stage prompt 兜底由 `confirm_with_user` 内 EOFError → `preset_end_stage = None` = 全跑 = 合法 daemon 行为，**不强制 `--end-stage`**，决策 #56 修订）；已 done 则强制要求 `--resume` 或 `--characters` 二选一（避免 daemon 撞 run_full 内 `'Resume from existing progress?'` 的 stdin 死锁）。两分支共同保证 daemon 路径上**没有任何**可触发 traceback 的 stdin prompt——所有 stdin 站点（character 选择 input + end_stage 选择 input + run_full `Resume from existing progress?` input）走 `try/except EOFError` 兜底 + 安全 default（character 选择 = `recommended_ids`、end_stage = None=全跑、resume = Y）。`--end-stage` argparse `type` 是 `_nonneg_int` 自定义函数，负数在 argparse 阶段直接 reject（exit 2 + 友好错误信息），避免 `--end-stage -1` 通过 `args.end_stage is None` 检查后让 `run_extraction_loop(max_stages=-1)` 在 line 1853 `tracker.completed >= max_stages` 立即 True 造成无声逻辑错误。Plumbing → `extraction/persona_extraction/cli.py`（无条件走 run_full + 加 `_load_pipeline_status` helper + 阶段感知双分支 background 校验，phase_1_5 not done 单约束 `--characters` + `_nonneg_int` argparse type）+ `extraction/persona_extraction/orchestrator.py::run_full(auto_resume: bool = False)` + `confirm_with_user` 内两 input 加 `try/except EOFError`（end_stage 兜底 = None = 全跑，对齐 prompt 文案 + flag "omit = all" 设计——决策 #56） + `extraction/persona_extraction/tests/_smoke_cli_resume_background_validation.py`（场景：phase_1_5 done/pending × {--resume, --characters, --end-stage, 都无} 的 background 校验真值表 + scenario I 验证 `--end-stage -1` argparse reject）。

52. **Phase 1 三 lane 并行 + 字段裁剪 + light_novel stage_plan 跳过 LLM。** 旧设计单次 `claude -p` 串行产出三件分析产物，schema gate 失败时整 lane 重跑且共享一个 `[phase1].exit_validation_max_retry` 池——实证 537 章 monolithic 单 LLM 调用 26min 仍未落盘，wall time 是后续 phase 启动前的硬瓶颈。新设计把 phase 1 内部拆成独立 lane：(1) **monolithic 模式 = 3 lane 并行**（foundation / stage_plan / candidate_characters，每 lane 独立 prompt template + 独立裁剪 chunks 输入 + 独立 schema gate）；**light_novel 模式 = 2 lane 并行**（foundation + candidate_characters）+ orchestrator 程序化 `_build_light_novel_stage_plan()` 直接落盘（zero LLM call，stage_plan lane 整体跳过 LLM）。(2) **字段裁剪**：每 lane 只接收自己需要的 chunk 字段，预先 project 后写到 `works/{work_id}/analysis/.phase1_lane_inputs/{lane}/chunk_NNN.json` 并 `.gitignore` 屏蔽——foundation lane = **仅** chunk-level 二级字段（`chunk_arc_summary` / `chunk_world_rules` / `chunk_power_levels` / `chunk_factions` **含 `members_present`**——决策 #54 修订段，foundation lane 写 `key_figures` raw 名直接来自 chunk_factions[].members_present[] 跨 chunk 合并去重 / `chunk_regions`），**`summaries` 整段删除**（全书设定不依赖逐章锚点）；stage_plan lane = `chunk_arc_summary` + `chunk_regions` + per-summary `chapter` + `summary`（**`characters_present` / `emotional_tone` / `identity_notes` 删除**——拐点合并依据是 `chunk_arc_summary` chunk 弧光 + `summary` 事件描述，与身份 / 角色 / 情绪粒度正交，裁掉减 token + 减 LLM thinking 长尾；`key_events` 已从 chunk schema 整体删除，见 #53）；candidate_characters lane = per-summary `chapter` + `summary` + `characters_present` + `identity_notes` + `chunk_factions[].{name,members_present}`（**新增 `summary`**——跨 chunk 身份合并需要事件上下文判断隐含身份链，光看 `identity_notes` 短句不够）。(3) **foundation lane 落盘路径** = `works/{work_id}/world/foundation/foundation.json`（与 phase 2 后续补齐的 `key_figures` 同文件；phase 2 `fixed_relationships.json` 同目录），**不再走 `works/{work_id}/analysis/world_overview.json`** 路径——decision #54 把 foundation 前移到 phase 1 直接产，phase 2 不再二次综合 foundation。(4) **per-lane retry = schema gate + correction_feedback（per-lane 独立预算）**：每 lane 完成抽取后落盘文件即跑 jsonschema gate（含 stage_plan lane 的 8–15 章 limit 检查由 schema `chapter_count.minimum=8 / maximum=15` 直接硬挡，决策 #27i schema-gate-as-retry-trigger 注入 prior_error；代码层 `_check_stage_plan_limits` 作 belt-and-suspenders 二次兜底）；首条违规作为 `prior_error` 注入下一次重试 prompt（与 phase 0 chunk-level / phase 4 chapter-level prior_error 注入同形态）。`[phase1].exit_validation_max_retry` 语义改为 per-lane 独立预算（不再共享池）。**不集成 `extraction.repair.run`**——phase 1 输出是 chunk-level 派生的全书分析，不是 stage-anchored 源文抽取，repair 的 SourceContext + T2 source_patch 假设 stage scoped chapter range 可读，对 phase 1 不成立。(5) **失败语义** = lane 隔离：单 lane fail 不影响其他 lane 已落盘产物，`--resume` 时 `reconcile_with_disk` 检测到 schema-valid 产物即跳过对应 lane 重跑（与 phase 0 chunk-level skip / phase 3 lane-level skip 同形态）。(6) **prompt template 三件套替换 `analysis.md`**：`analysis_foundation.md` / `analysis_stage_plan.md`（含 #27n 步骤 2.1/2.2/2.3 反锚定自检三子步） / `analysis_candidate_characters.md`（含步骤 1.5 跨 chunk 身份合并）；旧 `analysis.md` + `analysis_world_overview.md` 删除，no legacy fallback。(7) **tmpdir 清理**：run_analysis 在 `try/finally` 内 cleanup `.phase1_lane_inputs/`（成功 / 失败 / SIGTERM 均清）。Plumbing → `extraction/persona_extraction/prompts/analysis_{foundation,stage_plan,candidate_characters}.md`、`extraction/persona_extraction/prompt_builder.py`（`build_foundation_prompt` / `build_stage_plan_prompt` / `build_candidate_characters_prompt` + 三个 `_project_chunk_for_*` 内部裁剪函数 + `prepare_phase1_lane_inputs`）、`extraction/persona_extraction/orchestrator.py::run_analysis`（fan-out 重写 + foundation lane 输出到 `world/foundation/`）、`extraction/config.toml [phase1]` + `extraction/persona_extraction/core/config.py::Phase1Config`（增 `lane_concurrency`，注释更新 `exit_validation_max_retry` per-lane 语义）、`.gitignore`（`works/*/analysis/.phase1_lane_inputs/`）。

53. **Analysis schema 收紧 v2 + Phase 1.5 推荐规则化。** 2026-05-08 跑完一次端到端 phase 0 + 1 + 1.5 + phase 2 部分（被 SIGTERM 中止），看实际产物决定收紧三组 analysis schema。(1) **chunk schema** — 删 `summaries.items.key_events`（经 #52 三 lane 投影后无消费方，Phase 2 baseline 也不读，是死字段）；`summaries.items.summary` 100-150 → 150-200 CJK chars（需要装下事件 + 设定上下文，原范围在实际产出里频繁触底）。决策 #27m 内描述同步修订（key_events 段删除、summary 长度更新）。(2) **candidate_characters schema** — 删 `candidates.items.recommended` boolean（LLM 自报推荐拍脑袋打 boolean，不可靠）；删 `candidates.items.aliases.items.first_appearance` 字符串（如"约第 0042 章"，无下游消费且不可程序检索）。Phase 1.5 默认勾选改为基于 `importance == "主角"` 程序判定（用户仍可手选追加 / 取消），`recommended` 字段在 candidate 级消失但 `RECOMMENDED` 标签字符串保留——展示逻辑改读 `importance`。(3) **foundation schema（原 world_overview schema，决策 #54 改名 + 前移到 phase 1 落 `world/foundation/foundation.json`）** — `world_structure.major_regions.items` 由 `string` 升 `{name (≤15), description (≤30)}` 对象（对齐 `chunk_regions.items` 形态，phase 1 foundation lane 直接读 chunk 综合，不再 mid-step 拼对象）；`power_system.levels.items` 同上对齐 `chunk_power_levels.items`；`core_rules.maxItems` 20→30（N chunk × ≤5 条原始规则去重后 30 比 20 合理），`items.maxLength` 100→150（保留字符串数组形态，强制 LLM 重新整理而非照搬 chunk 行）。Plumbing → `schemas/analysis/{chapter_summary_chunk,candidate_characters}.schema.json` + `schemas/world/foundation.schema.json`（决策 #54 把 `world_overview.schema.json` 内容合并入 foundation schema，删 analysis 副本）、`extraction/persona_extraction/prompts/{summarization,analysis_foundation,analysis_stage_plan,analysis_candidate_characters,baseline_production}.md`、`extraction/persona_extraction/{prompt_builder,orchestrator}.py`、`docs/architecture/{schema_reference,extraction_workflow}.md`、`ai_context/{architecture,decisions}.md`（修订 #27m 描述 + 本条新增）。

54. **Foundation 前移 phase 1 + phase 2 仅补 `key_figures` + target_baseline 准入门槛收紧（dialogue/action 交互）。** 2026-05-09 端到端跑完 phase 2 后比对 [analysis/world_overview.json](works/<work_id>/analysis/world_overview.json) vs [world/foundation/foundation.json](works/<work_id>/world/foundation/foundation.json)，发现两份 95% 字段重叠（`work_id` / `genre` / `tone` / `world_structure` / `power_system` / `world_lines` 几乎 1:1 拷贝）；真增量只有 `core_rules` 升 object[] 含 `impact` + `major_factions.key_figures[]` 两项。同步发现 target_baseline 15 条全 `核心 / 重要` tier，含末章才出生且无 dialogue / action 的双胞胎角色——baseline prompt 当前"宁可多列、不可漏列、被点名提及即纳入"导致前 12 stage × 2 角色 × 3 结构 = 72 条纯空 entry 噪声。改造三件合一：(1) **foundation 前移 phase 1**：原 phase 1 `world_overview` lane → 改名 `foundation` lane，输出路径 `works/{work_id}/analysis/world_overview.json` → `works/{work_id}/world/foundation/foundation.json`。`schemas/analysis/world_overview.schema.json` 删除，内容**逐字搬到** `schemas/world/foundation.schema.json` 替换旧 foundation schema（旧 foundation 字段 / bound 形态废弃，新 foundation = 旧 world_overview 形态）；`$id` / `title` / `description` 改写为 foundation 语义，**字段 / bound 一字不改**（含 `core_rules` 保持 `string[] ≤30 条 / 每条 ≤150 字` 形态——user 决策 1 明确不改 core_rules 结构）。`major_factions.items` 新增 `key_figures[]` optional 字段（items: string maxLength 30 / maxItems 10 / 注释说明双阶段语义），**phase 1 lane 写 raw 名**（chunk_factions[].members_present[] 跨 chunk 合并去重直接写入，化名 / 真名 / 称呼任一）。`analysis_world_overview.md` → 改名 `analysis_foundation.md`。(2) **phase 2 缩水到 LLM "替换" 工作**（决策 #54 修订段，2026-05-11 user 反馈 phase 1 不应丢信息——chunk_factions.members_present 已有 raw 名）：删 `baseline_production.md`「产出 1：世界 Foundation」整段（≈100 行）；新增「产出 1：替换 foundation.major_factions[].key_figures 内 raw 名为 character_id」段：单次 LLM call 整合到 build_baseline_prompt（与 fixed_relationships / identity / target_baseline / manifest 同一次调用），输入 phase 1 落盘 foundation（含 raw 名 key_figures）+ `analysis/candidate_characters.json`（含 character_id + aliases） + 已确认目标清单；LLM 对 key_figures 每个 raw 名 lookup candidates[*].aliases，能匹配的换为对应 character_id，**匹配不上保留 raw 名**（不报错、不删除）；schema 不抓 character_id 合法性，key_figures 最终是 character_id + 未合并 raw 名混合。phase 2 保留产出：`fixed_relationships.json` + per-character `identity.json` + `target_baseline.json` + `manifest.json` 四件 + foundation key_figures 替换。失败处理：本条落地时为单次 `run_with_retry` → `validate_baseline` schema gate → length-bound tolerance gate (#48) → fail 则 `sys.exit(1)` 不接入 repair（拆作 todo `T-PHASE2-REPAIR-AGENT`）；该 todo 已由 #59 落地——phase 2 拆 2+2N lane 并行 + per-lane repair 缩水版接入，call 拓扑与兜底形态以 #59 为准。(3) **target_baseline 准入门槛收紧**：删 prompt 中「宁可多列、不可漏列、被点名提及即纳入」原则；改为 **准入门槛 = 本角色与目标角色在 chapter_summaries 摘要描述中被反映为有过 dialogue / action 交互**（如"X 对 Y 说……" / "X 救/打/教 Y" / "X 与 Y 联手……"等动作或对话描述）；血亲不再默认核心 tier——按准入门槛 + 实际剧情驱动力分级。tier 4 档 (核心 / 重要 / 次要 / 普通) 不动，准入门槛与 tier 分级正交。Phase 3 stage_snapshot 三结构双向 set-equal 约束（#13）不动——准入门槛只影响 baseline 收录范围，对 phase 3 keys == baseline 的执行不变。**显式不做**：不动 [target_baseline.schema.json](schemas/character/target_baseline.schema.json) 与 [targets_cap.schema.json](schemas/character/targets_cap.schema.json)（schema 不变，仅 prompt 加严）；不引入 `_validation_tolerance_applied` 类元数据；不本次接入 repair 到 phase 2（拆出来作 `T-PHASE2-REPAIR-AGENT`）；本 /go 不执行 `git reset` 重跑 phase 2 数据迁移——user 自决何时操作。Plumbing → `schemas/world/foundation.schema.json`（重写）+ `schemas/analysis/world_overview.schema.json`（删除）、`extraction/persona_extraction/prompts/analysis_foundation.md`（改名 + 内容更新）+ `extraction/persona_extraction/prompts/baseline_production.md`（删 foundation 段 + 加 key_figures 补齐段 + target_baseline 加严）、`extraction/persona_extraction/prompt_builder.py`（`build_world_overview_prompt` → `build_foundation_prompt`、`_project_chunk_for_world_overview` → `_project_chunk_for_foundation`、phase 2 `key_figures` 替换段整合到 `build_baseline_prompt` 单次 LLM call 内，与 identity + target_baseline + fixed_relationships + manifest 五件合一（决策 #54 修订段 2026-05-11 落地形态）、lane 名常量 `world_overview` → `foundation`）、`extraction/persona_extraction/orchestrator.py`（`run_analysis` foundation lane 输出路径改 + `run_baseline_production` 新增 key_figures 补齐 LLM call）、`schemas/README.md` + `extraction/README.md`（schema 索引 + lane 列表更新）、`ai_context/{architecture,decisions,conventions}.md`（本条 + #25 / #40 disambiguation + #48 措辞修正 + #27m + #52 + #53 同步）、`docs/architecture/{schema_reference,extraction_workflow}.md` + `docs/requirements.md` §9 / §11、`docs/todo_list.md`（新立 `T-PHASE2-REPAIR-AGENT`）。

55. **char_snapshot lane 拆 4 sub-lane 并行 + prev snapshot 按 lane 切片喂入
    + 程序 merge。**
    > **经 #62 收紧**：`lifecycle 2 sub-lane 重抽`（`sub_lane_regen`）已随 T3
    > `file_regen` 一并删除——repair 单轮 Phase A→B→C，不再有 lifecycle 2，
    > 也没有任何形态的重抽。下方「Repair lifecycle 2 T3 重抽」整段描述的是
    > 已移除的机制，保留仅为记录当时的设计理据。

    Phase 3 单 stage 的
    `char_snapshot` lane 内部拆 **4** 个并行 sub-lane（`char_expression` /
    `char_decision` / `char_internal` / `char_social`）压 wall-time；每个
    sub-lane 只读 prev snapshot 中自己需要的字段切片，**不读完整 prev**。
    字段归属表（同源给 prompt + merge 用，
    定义在 `extraction/persona_extraction/phases/snapshot_merge.py::FIELD_ALLOCATION`）：
    `char_expression` = `voice_state` / `active_aliases` / `current_mood` /
    `failure_modes.tone_traps`；`char_decision` = `behavior_state`
    （仅 7 个自身行为子键 `{core_goals, obsessions, decision_making_style,
    emotional_triggers, emotional_reaction_map, habitual_behaviors,
    stress_response}`，**不含** `target_behavior_map`）/ `boundary_state` /
    `emotional_baseline` / `current_personality` / `current_status` /
    `stage_delta.{status_changes, mood_shift, personality_changes}`；
    **`char_internal`** = `knowledge_scope` / `misunderstandings` /
    `concealments` / `snapshot_summary` / `failure_modes.{knowledge_leaks,
    common_failures}`；**`char_social`** = `relationships` /
    `relationship_state_summary` / `stage_events` / `character_arc` /
    `behavior_state.target_behavior_map` / `failure_modes.relationship_traps` /
    `stage_delta.{trigger_events, relationship_changes, voice_shift}`；
    程序注入 = `schema_version` / `work_id` /
    `character_id` / `stage_id` / `stage_title` / `timeline_anchor` /
    `chapter_scope`. **拆分依据**（S001 振荡定位 + S002 cognition lane
    60min hard timeout）：原 `char_cognition` 10 top-level / ~12 KB 输出
    是 stage 内单点瓶颈；按"内省 vs 关系/事件"切，`char_internal` 集中
    知识/隐瞒/失败模式形成 `knowledge_state_self_contradiction` 自洽闭包
    （避免跨 lane 振荡 — S001 修复一处 `knowledge_leaks` 引入新
    `does_not_know` 矛盾的根因），`char_social` 集中关系/事件/弧线/对
    target 的行为模式。`target_behavior_map` 从 `char_decision` 移到
    `char_social`：它是 N×M 对 target 的行为映射，与 `relationships` 同
    结构、应同 lane 印证；`char_decision` 保留 `behavior_state` 的 7 个
    自身行为子键（`core_goals` / `obsessions` / `decision_making_style` /
    `emotional_triggers` / `emotional_reaction_map` / `habitual_behaviors`
    / `stress_response`）。
    **Merge hard gate**（5 gate；4 positive + 1 anti-rule）：(1) 每
    partial 顶层字段集合 == 分配；(2) `failure_modes` 4 子键互斥 across
    3 sub-lane（`tone_traps`→expression /
    `{knowledge_leaks, common_failures}`→internal /
    `relationship_traps`→social）+ 全 4 子键覆盖；(3) `stage_delta` 6 子键
    互斥 across 2 sub-lane（decision 半
    `{status_changes, mood_shift, personality_changes}` / cognition 半
    `{trigger_events, relationship_changes, voice_shift}` 按新拓扑 cognition
    半归 `char_social`）+ 全 6 子键覆盖（S001 允许 contributing 两 lane
    都不写 `stage_delta` 顶层 key）；(4) **`behavior_state` 8 子键互斥**
    across 2 sub-lane（7 self-behavior 子键 `{core_goals, obsessions,
    decision_making_style, emotional_triggers, emotional_reaction_map,
    habitual_behaviors, stress_response}`→decision /
    `target_behavior_map`→social）+ 全 8 子键覆盖；三方 keys（
    `voice_state.target_voice_map` / `behavior_state.target_behavior_map` /
    `relationships`）keys 集合相互相等且 == `target_baseline.targets[].target_character_id`
    — 复用 `extraction/repair/checkers/targets_keys_eq_baseline.py`
    做 merge 前置预检；(5) **(D) drop entry 不被误判**：merge 仅查字段集合
    互斥 + 全覆盖，**不查** partial entry 数 ≥ prev（per #11f / #13）。
    **Prev snapshot 4-way slice**（避免 sub-lane 都读 ~30 KB 完整 prev
    snapshot）：`snapshot_merge.slice_snapshot_for_lane(full, lane)` 按
    `FIELD_ALLOCATION` + `SHARED_KEY_SUBKEYS` 反向投影；orchestrator stage
    启动前调 `_write_prev_snapshot_slices(work_root, char, prev_stage_id)`
    切 4 个 slice 写盘到 `works/{wid}/analysis/progress/.partial_prev/{char_id}/{prev_stage_id}_{lane}.json`，
    prompt_builder 按 `lane_scope` 选 slice 路径塞进 prompt：
    `char_expression` / `char_decision` 各拼**自身 slice**，`char_internal`
    / `char_social` 各拼**两个 slice**（internal + social，互读对方，
    覆盖"知识 ↔ 关系"的耦合 — 角色对甲知道什么 vs 角色与甲的关系演变
    属于同一状态空间）。每 lane prev 部分体量从 ~30 KB 降到 ~7–13 KB
    （-50% 到 -70%）；**不读** prev world stage_snapshot、**不读**
    `memory_digest.jsonl`（章节原文 + baseline 已够，加这些既无法防住
    具体失败模式，又会重新膨胀上下文）。slice lifecycle 照搬
    `.partial/`（决策 #55 同段）：stage 启动前 R3 残留清理（先
    `_clear_prev_snapshot_slices` 再 `_write_prev_snapshot_slices`
    unconditional overwrite，保证 fresh 且与 repair 中可能改过的 prev
    snapshot 同步）+ repair 完成后 `[5/5] Git commit` 前清当 stage 用的
    prev slice + sub-lane / merge 失败时清。**不保留 slice 调试**：prev
    snapshot 已 committed 在 git history + slice 是 `FIELD_ALLOCATION` 的
    确定性投影，留盘无任何调试收益（要看 LLM 当时读到啥，
    `git show {prev_stage}:.../stage_snapshots/{prev}.json` + 翻
    `FIELD_ALLOCATION` 即可）。
    **Lane 级 resume 粒度仍是 `snapshot:{char_id}`**——sub-lane 拆分对
    `StageEntry.lane_states` 不可见；任一 sub-lane 或 merge 失败即整 lane
    重跑，PENDING / ERROR 状态下的 `.partial/{stage_id}_*.json` 由
    `progress.reconcile_with_disk` 一律删，不复用。**Repair lifecycle 2 T3
    重抽**：file-level lifecycle 1 末端 T3 触发后，若开关开 + 文件是
    `characters/<cid>/canon/stage_snapshots/<sid>.json` → T3 fixer 走 4
    sub-lane 并行重新 extract + merge 路径（每 sub-lane prompt 注入
    `prior_attempt_context` resolved+remaining ≤600 char 摘要 + 错误信息），
    替代默认 `FileRegenFixer` 全文 regen；lifecycle 计数（`max_lifecycles_per_file = 2`）
    与 `T3_EXHAUSTED` 终止语义不变（lifecycle +1 仅在 T3 真正触发并 reset 进入
    下一轮时计入，rate-limit pause 重跑不消耗 lifecycle 槽 — R1）。
    **Rate-limit / hard-stop**：sub-lane 走现有 `run_with_retry` 继承
    `RateLimitController` pause / resume；hard-stop 时 sub-lane sub-executor
    `shutdown(wait=False, cancel_futures=True)` 并立即 raise，磁盘 partial
    保留供下次 `--resume` 启动前的 `_clear_snapshot_partials` 兜底清理覆盖
    （R2 — 不在 hard-stop 路径删 partial，避免 sleep 中的同伴 future 被
    隐式 `with` 退出阻塞数小时；R3 — 启动前清理仍是单源真理）。**Outer pool
    全并发**：phase 3 主 ThreadPoolExecutor `n_workers = max(1, len(lanes_to_run))`，
    外层 lane (`world` / `snapshot:*` / `support:*`) 全并发提交；sub-lane fan-out
    仅在 `snapshot:*` lane 内部展开 **4** inner LLM 调用，`world` /
    `support:*` 无 fan-out。**2 角色场景峰值 = 1 world + 2×4 snapshot
    sub-lane + 2 support = 11** LLM 并发；sub-lane 关闭时降为
    1 + 2 + 2 = **5**——均 ≤ `[phase3].concurrency=12` cap
    （`extraction/persona_extraction/core/config.py` + `extraction/config.toml`，
    由 3 sub-lane 时代的 10 上调到 12 覆盖新峰值）。N≥3 角色场景峰值
    `1 + 4N + N` 仍超 cap（N=3 → 16，N=4 → 21），留给另一个 todo
    `T-PHASE3-PEAK-CAP-N-CHARS` 讨论，本次保持 RateLimitController pause
    兜底现状不引入新分支。原 H1 "÷3 与 inner 相消" 算法把 `world` /
    `support` 错按 sub-lane 折扣，外层无故缩到 1 等效串行，单 stage 时长由
    理论 max(world, snapshot, support) ~15 min 拉到 ~60 min，已撤回。**Toml 开关 +
    CLI 双向 flag**：`[phase3].char_snapshot_sub_lanes`（缺省 `true`）+
    `--char-snapshot-sub-lanes` / `--no-char-snapshot-sub-lanes`；
    light_novel 模式单 stage 字符数小，4 sub-lane 启动开销可能 > 抽取
    耗时收益，**不引入** mode-aware 默认值，由用户按 work 手切。
    **Fallback** `false` → 单 lane 等价 `lane_scope=ALL`，phase 3 现状不变
    （prev slice 机制仅 sub-lane 模式生效；fallback 单 lane 直接读完整 prev
    snapshot；baseline 锚点 + #11f 四态 + #13 keys == baseline 校验均为
    phase 3 通用现状，已落地，本决策不引入新强制规则）。**`.partial/`
    路径**：`works/{wid}/characters/{cid}/canon/stage_snapshots/.partial/`
    被 `.gitignore` 屏蔽；**`.partial_prev/` 路径**：
    `works/{wid}/analysis/progress/.partial_prev/` 跟随 `progress/` 整目录
    被 `.gitignore` 屏蔽（已有 `works/*/analysis/progress/` 通配 + 新增
    `works/*/analysis/progress/.partial_prev/` 显式条目防误提）。Plumbing →
    `extraction/persona_extraction/phases/snapshot_merge.py` + `extraction/persona_extraction/prompt_builder.py` + `extraction/persona_extraction/orchestrator.py` + `extraction/persona_extraction/lifecycle/progress.py` + `extraction/persona_extraction/core/config.py` + `extraction/persona_extraction/cli.py` + `extraction/persona_extraction/lifecycle/lane_output.py`、
    `extraction/persona_extraction/prompts/character_snapshot_extraction.md`（加
    `{lane_scope}` / `{lane_field_whitelist}` 占位，不动 §核心规则 #2 与
    §maxItems 裁剪段，保持 sub-lane / 单 lane 全 inherits）、
    `extraction/repair/{coordinator.py,fixers/file_regen.py}`（
    `FileRegenFixer` 加可选 `sub_lane_regen` 回调，`coordinator.run` 新增
    kwarg 透传到 `_build_fixers`）、`extraction/config.toml`（
    `[phase3].concurrency` 10→12）、`.gitignore`、
    `docs/architecture/extraction_workflow.md` §6.2、`docs/requirements.md` §9.3、
    `extraction/README.md` Phase 3 段、`ai_context/{architecture,decisions,conventions}.md`、
    `docs/todo_list_archived.md`。

56. **Pipeline-resume alignment 三处修复 — `pipeline.json` schema_version
    启动、phase 2 recovery 阻 phase 3 committed 产物、`--end-stage` daemon
    路径"empty = 全跑"语义贯通。** 2026-05-12 codex `gpt-5` 复审报告（
    `logs/review_reports/2026-05-12_113619_gpt-5_pipeline-resume-alignment-audit.md`）
    指出 3 个 H/M finding，全部确认真实。
    (1) **`PipelineProgress.load()` 误把当前 `phase_2` 当 legacy remap**：
    `_LEGACY_PHASE_KEY_MAP` 把 `phase_2 → phase_1_5` 原本是为兼容旧 progress
    文件（老命名 `phase_2 = 用户确认` / `phase_2_5 = baseline`）；当前命名
    `phase_1_5 = 用户确认` / `phase_2 = baseline` 后，当前文件被 `load()`
    无差别 remap，`phase_2=done` 经"DONE wins"守卫跳过、未在 dict 内立项，
    `__post_init__` 再补 `phase_2 = pending` → 续跑 baseline 完成状态丢失，
    放大 phase 2 recovery 触发面。修复 = `save()` 写 `schema_version: 2`
    顶层字段；`load()` 优先 `schema_version >= 2` 整体跳 legacy remap；缺
    `schema_version` 字段时退到 shape-based 兜底（raw_phases 含 `phase_1_5`
    或 `phase_3_5` 任一即视为 current shape）。**两层守卫并行**：version
    优先、shape-based 兜底——单层 version 短期对存量未写 version 的当前
    文件不安全，shape-based 短期止血 + version 长期权威。`_LEGACY_PHASE_KEY_MAP`
    保留以兼容 `migrate_legacy_progress` 的真 legacy 路径。
    (2) **Phase 2 validation-triggered recovery 不阻已有 phase 3 committed
    产物**：`run_extraction_loop` existing baseline validation 失败时直调
    `run_baseline_production` + `commit_stage("Phase 2 baseline (validation-
    triggered recovery)")` 重写 `target_baseline.json`；`run_baseline_production`
    docstring 已明写 baseline 改写后 phase 3 stage_snapshot 必须配套清空（#13
    双向 set-equal 约束），但本函数声明"不自动清理"——所以调用点必须前置
    guard。修复 = 新增 `_phase3_committed_artifacts_present()` helper（读
    `phase3_stages.json` 任一 stage state == `COMMITTED` 或扫磁盘
    `world/stage_snapshots/*.json` + `characters/*/canon/stage_snapshots/*.json`
    非空即返回 True），插入到两条路径前：(a) validation-triggered recovery
    分支；(b) `--start-phase 2` `force_baseline` 分支。**Daemon vs 前台
    双模交互**：daemon (`--background`，stdin=`/dev/null`) → 打印清理清单
    + `sys.exit(1)`；前台 → 同清理清单 + `input("Continue and overwrite
    phase 3 artifacts? [y/N]: ")` 非 y 即退出。**默认 hard stop**，不实现
    `--reset-phase3-after-baseline-change` 自动清理 flag——破坏性动作走显式
    人工执行（撞 hard stop 后用户手动跑清理命令再重启或切前台走 `[y/N]`）。
    (3) **`--end-stage` daemon 路径"empty = 全跑"语义贯通**：(3a)
    `confirm_with_user` 内 `Extract up to stage N` prompt 文案写 `"0 or
    empty = all"`，但代码 `int(raw) if raw else 0` 把 empty 折成 0（baseline
    only）——文案 / 代码矛盾。daemon stdin=DEVNULL EOFError 走 raw="" 路径，
    被悄悄折成 baseline-only。(3b) `--background` validator 因(3a)折坏才
    硬性要求 `--end-stage`——本来 `argparse default=None` + `run_extraction_loop
    max_stages=None` 已是合法"no limit"语义（决策 #51）。修复 = `preset_end_stage
    = int(raw) if raw else None`（empty → None = 全跑，对齐 prompt 文案 +
    flag "omit = all" + `run_extraction_loop` None 语义）+ prompt 文案改
    `"Extract up to stage N (total {N}; empty = all (no limit), 0 = baseline
    only): "` + 删除 cli.py phase_1_5 未 done 时对 `--end-stage` 必填的
    硬挡（仅保留 `--characters` 必填，决策 #51 daemon prompt 防 deadlock
    口径相应放宽：empty 走"安全 default = 全跑"是合法 daemon 行为）。
    `_smoke_cli_resume_background_validation.py` C / D 翻转为 accept；G / H
    显式传 `--end-stage` 仍 accept；I (`--end-stage -1` argparse reject) 不动。
    **决策 #51 措辞同步**：双约束 `--characters AND --end-stage` 改为单约束
    `--characters`，end_stage prompt 兜底从"daemon validator 强制提供"
    改为"EOFError → None = 全跑"。**显式不做**：不动 `_LEGACY_PHASE_KEY_MAP`
    内容（仍保留 `phase_2 → phase_1_5` / `phase_2_5 → phase_2`）；不动
    `migrate_legacy_progress` 的 `extraction_progress.json` 路径；不实现
    `--reset-phase3-after-baseline-change` flag（破坏性动作走人工执行更稳）；
    不动 light_novel `chapter_count=1` schema 例外（决策 #27n 现状保留，
    外部 validator 消费方未出现 → todo `T-LIGHTNOVEL-SCHEMA-ONEOF`）。Plumbing →
    `extraction/persona_extraction/lifecycle/progress.py`（`PipelineProgress.save/load`
    + `_LEGACY_REMAP_GUARD` 内部辅助）、`extraction/persona_extraction/orchestrator.py`
    （`_phase3_committed_artifacts_present` helper + `run_extraction_loop`
    validation-triggered & force_baseline 两调用点前置 guard + `confirm_with_user`
    line 2125 兜底改 None + line 2116-2117 prompt 文案改写）、
    `extraction/persona_extraction/cli.py`（删 phase_1_5 未 done 时 `--end-stage`
    必填硬挡 + 长注释同步）、
    `extraction/persona_extraction/tests/_smoke_cli_resume_background_validation.py`
    （C / D 翻转）、`extraction/README.md` + `docs/architecture/extraction_workflow.md`
    + `ai_context/architecture.md`（四处 `--background` 文案同步）、
    `ai_context/decisions.md`（本条 + #51 措辞同步）、`docs/todo_list.md`
    （登记 `T-LIGHTNOVEL-SCHEMA-ONEOF`）。

58. **Foundation schema 收紧（核心字段 required）+ `key_figures` required allow-empty
    + Phase 2 不再让 LLM 写空 stage_catalog。** 2026-05-14 /check-review codex 复审
    （`logs/review_reports/2026-05-14_004356_gpt-5_full-review-alignment-audit.md`）
    报出三处契约漏洞（H4 + OQ1 + OQ2 + OQ5）。本条把三件合一落地，作为 #54 的
    收尾收紧条款。(1) **OQ1 — foundation.schema.json 核心字段 required**：原
    `required: ["work_id"]` 太弱——`{"work_id": "demo"}` 通过 schema 会让 phase 1
    foundation lane 的 `_lane_passes_skip` 静默跳过（`orchestrator.py:1854-1867`
    用 `validator.iter_errors(existing)` 空即 skip）+ phase 2 `validate_baseline`
    line 152 仅 `data.get("work_id")` 非空 + schema pass 即放行；连锁后果是 runtime
    Tier 0 的 `genre / tone / world_structure / power_system / major_factions /
    world_lines / core_rules` 可全空缺，从根上让 simulation 拿到空世界。改为
    `required` 含上述 7 个核心字段（与 phase 1 foundation lane prompt 实际产出对齐）。
    代价：main 上 `works/` 只 README，无历史 foundation.json 受影响；新跑的
    extraction 在 `validate_baseline` 阶段被这个 schema gate 收紧。(2) **OQ2 —
    `major_factions[].key_figures` items required allow-empty `[]`**：原 schema
    `items.required = ["name", "description"]`，`key_figures` 是 optional 字段；
    phase 1 prompt 明确"必须写"但 schema 不卡，导致 phase 2 替换 LLM 看到的
    `key_figures` 字段可能缺失（需要 init vs 替换分支判断）。改为 items.required
    含 `key_figures`，允许 `[]`——给 phase 2 替换 LLM 稳定的"key 一定存在"前提，
    替换工作变成纯 in-place map 操作而非 conditional init+map。foundation.schema.json
    的 `major_factions.items.key_figures.description` 同步收紧为"必须存在，无成员
    势力写 `[]`"。(3) **OQ5 — Phase 2 不再让 LLM 写空 stage_catalog**：原
    `baseline_production.md:13 / 253-256 / 279 / 292` 多处要 LLM 写空数组
    `world/stage_catalog.json` + `characters/{char}/canon/stage_catalog.json`；但
    `phase2_baseline.validate_baseline` 不校验空 stage_catalog（不在文件存在性必查
    列表里），而 Phase 3 第一个 stage 的 `post_processing.upsert_stage_catalog`
    （`post_processing.py:550`）会自动 init 文件（带 mkdir parents=True 走
    `_atomic_write_json`，父目录不存在也 OK）。LLM 写空 = 无用功 + 引入第 6 个
    无 validator 兜底的产物面 + 让 baseline prompt 多 ~40 行说明文本。删除
    `baseline_production.md` 内 stage_catalog 初始化段（第 5 件「世界与角色
    stage_catalog 初始化」整段 + 「产出清单」内 stage_catalog 行 + 末尾 "5 件
    baseline" → "4 件 baseline" 描述），由 Phase 3 post_processing 自动 init
    承担文件创建。代价：`works/{work_id}/world/stage_catalog.json` +
    `works/{work_id}/characters/{char}/canon/stage_catalog.json` 在 phase 2 结束后
    **不存在**，直到 phase 3 第一个 stage 跑完 post_processing 才落盘——下游消费方
    （bootstrap stage 选择、记录展示）必须容忍"phase 2 done but stage_catalog
    not yet present"。`works/README.md` + `extraction/README.md` 描述同步。
    **不在本条 scope**：foundation.json 的 `additionalProperties` 仍保持 `true`（
    允许 per-work 扩展字段，#54 现状）；`major_factions.items` 的
    `additionalProperties` 保持 `false`（结构性收紧不放松）；不动 phase 2 repair
    接入（当时由 `T-PHASE2-REPAIR-AGENT` 跟踪，已由 #59 落地）。Plumbing → `schemas/world/foundation.schema.json`
    （`required` 加 7 字段 + `items.required` 加 `key_figures`） +
    `extraction/persona_extraction/prompts/baseline_production.md`（删 stage_catalog
    初始化段 + 产物清单段 + 产物数字 5→4） + `extraction/persona_extraction/prompts/analysis_foundation.md`
    （key_figures "必须存在 ≥ []"重申） + `works/README.md` + `extraction/README.md` +
    `docs/architecture/{schema_reference,extraction_workflow}.md` +
    `docs/requirements.md` §9 / §11 + `ai_context/{architecture,conventions}.md`
    同步表更新。

59. **Phase 2 baseline 拆 2+2N lane 并行 + per-lane repair 缩水版接入（T0/T1 +
    程序 checker；T3 = lane 重跑）。** 2026-07-13 /plan 讨论收敛 + 4 项决策拍板后
    > **经 #62 收紧**：T3 `lane_regen` / 全文重跑已删——phase 2 per-lane repair
    > 现只有 T0/T1 + 程序 checker，无 lane 重生成；`validate_baseline` 仍是最后
    > 安全阀。
    落地（`T-PHASE2-REPAIR-AGENT`）。动机：phase 2 原为单次组合 LLM call 产 4 件
    强耦合产物 + 终点 `validate_baseline` 硬失败（#54 形态），格式错只能整体手动
    重跑；同时单文件 T3 重抽在组合 call 拓扑下会跨文件漂移，堵死 repair 接入。
    关键事实：4 件产物互相之间**没有产出依赖**（共同依赖 phase 1 三件 + chunk
    summaries 不可变输入），拆 lane 后 T3 语义自然变为"只重跑自己 lane"。
    (1) **Call 拓扑 = 2+2N lane**：lane A `key_figures`（foundation 就地替换，
    **先行串行**——与其余 lane 对 foundation.json 有同文件读写并发，必须错开；
    读 foundation + candidate_characters，**不读 chunk summaries**）→ lane B
    `fixed_relationships` + 每目标角色 identity lane（identity.json +
    manifest.json）+ target_baseline lane 并行（`[phase2].lane_concurrency`，
    默认 5 = N=2 时 lane 数）。per-lane 输入投影裁剪照搬 #52 projector 模式
    （`.phase2_lane_inputs/{lane}/`，gitignored，run 后清理）；resume 语义 =
    产物在盘 + schema-valid 即 skip（lane A 例外——替换幂等且"已替换"无法从
    schema 判定，phase 2 未 done 时总是跑）。输出文件缺失（repair 无从修起的
    生成失败）走 `output_missing_max_retry` prior_error 重跑。
    (2) **Repair 缩水版**：per-lane 产物过 file-level lifecycle——T0 程序修 +
    T1 局部 patch + schema checker + phase 2 引用 checker；**L3 语义 checker /
    T2 source_patch / triage 全关**（`run_semantic=False` + `t2_max=0` +
    `source_context=None`——无失败样本不预建贵机器；且 phase 2 输入契约是摘要
    初稿，T2 拿原文修会越过 phase 2/3 分工边界）。T3 经 `lane_regen` 回调 =
    重跑本 lane 自己的 LLM call（issues 注入 prior_error；一个 repair run 内
    只重跑一次，2 文件 lane 第二次回调只复验）。lifecycle 2 的
    `LENGTH_TOLERANCE_PASS` 分支（#48）对 phase 2 同样生效；终点
    `validate_baseline`（strict → ±10% tolerance）保留为最后安全阀。
    `[phase2].repair_enabled=false` 可整体退回"lane 并行 + 仅终点 gate"。
    (3) **程序 checker（纯集合运算，构造函数注入 hint——不走 `_repair_hints`
    内容注入，fixer 写回不剥离 hint 会污染落盘文件）**：
    `FoundationKeyFiguresChecker`（势力集合稳定 / 条目溯源 ∈ 合法 id ∪
    pre-lane raw 名 / 去重——"匹配不上保留 raw 名"合法，纯 ∈ candidates 检查
    会误报）+ `FixedRelationshipsPartiesChecker`（relationship_id 去重 error；
    parties ∉ 合法 id 集仅 **warning**——schema 契约允许 raw 角色名）+
    `TargetBaselineKeysChecker`（character_id 一致 / target ∈ 合法 id 集 /
    去重 / 自引用，全 error）。**不做 merge 点跨产物 checker**——
    fixed_relationships ↔ target_baseline 分叉合法（血亲等 fixed 关系无
    dialogue/action 交互时不入 baseline，#54 准入门槛），各 checker 只对照
    candidate_characters 这组不可变共享输入，lane 间完全独立。
    (4) **框架增量（通用 hook，不特化 phase 2）**：`coordinator.run` /
    `validate_only` 加 `extra_checkers`（附加 BaseChecker 注册）+ `run` 加
    `lane_regen`（通用 T3 回调，`sub_lane_regen` path-specific 优先）；
    `FileRegenFixer` 修正 `llm_call=None` 早退守卫（回调接管时不需要 LLM）。
    **显式不做**：LLM 类 checker（target_baseline dialogue/action 准入判定）
    等真实失败样本再立项；不改 `protocol.py`（`SourceContext` 保持
    stage-scoped，phase 2 传 `None`）；schema 结构零改动（仅 description
    文本随 call 拓扑同步）；per-char lane 不再细拆（identity+manifest 同
    "自我视角"合一个 call）。Plumbing →
    `extraction/persona_extraction/prompts/baseline_{key_figures,fixed_relationships,identity,target_baseline}.md`
    （4 件 lane prompt，`baseline_production.md` 删除）、
    `prompt_builder.py`（4 个 `build_*_prompt` 入口 + 3 个 phase 2 projector +
    `prepare/cleanup_phase2_lane_inputs`）、
    `extraction/repair/checkers/phase2_baseline_refs.py`（3 checker）、
    `extraction/repair/{coordinator,fixers/file_regen}.py`（extra_checkers /
    lane_regen hook）、`orchestrator.py::run_baseline_production`（fan-out 重写）、
    `extraction/config.toml` + `core/config.py`（`[phase2]` 节）、`.gitignore`
    （`.phase2_lane_inputs/`）、#25 / #48 / #54 就地 supersede、
    `docs/architecture/{extraction_workflow,schema_reference}.md` +
    `docs/requirements.md` + `extraction/README.md` +
    `ai_context/{architecture,conventions}.md` 同步。

60. **未决语义（L3）repair 问题 record-and-continue，不再停机。**
    > **经 #62 扩展**：可 defer 的 `category` 从"仅 semantic"扩到
    > {semantic, schema, structural, cross_file}；只有 `json_syntax`（文件
    > 不可解析）与 worker 崩溃仍硬 ERROR。判据函数 `deferrable_semantic_issues`
    > → `deferrable_issues`，`DEFERRABLE_CATEGORY` → `DEFERRABLE_CATEGORIES`。
    >
    > **再经 T-FIX-FROM-FULLREVIEW 收紧两点**（2026-07-16 `/full-review`
    > H6/H7）：(1) 判定改为**逐 entry**——原实现把所有失败文件的 issue 摊平
    > 后统一判，而 worker 崩溃的合成 `RepairResult` 带 `issues=[]`、对摊平集合
    > 毫无贡献，于是只要同 stage 另有任一可延后 issue，崩溃文件就搭顺风车当
    > PASS 提交、且不进台账，Phase 3.5 收尾 pass 永远不会知道它（函数自己的
    > docstring 承诺"崩溃硬停"，该承诺仅在崩溃文件是唯一失败项时成立）。
    > (2) `coverage_shortage` 残留纳入可 defer——它 `severity=warning` 却仍被
    > `_filter_blocking` 当阻塞项，而判据只收 `severity == "error"`，导致超
    > `accept_cap_per_file` 的薄内容返回 `None` → 硬 ERROR 停机，等于 #62 想
    > 根除的 min_examples 死锁换个入口复活（baseline 常有 ~15 个 target，一个
    > 快照出现 ≥6 处薄内容很现实）。
    **背景**：Phase 3 首次端到端运行时 S002 的 repair 在快照里查出真实的跨字段
    语义自相矛盾（同一事实既 known 又 uncertain；current_status 与
    relationships 对同一物件来源打架）。这类 L3 问题 field-level 的 T1/T2
    追不平（跨字段一致性），T3 又在 lifecycle 2 被禁用；叠加 L3 semantic
    reviewer 本身非确定性（每轮 flag 集合跳动），修复循环不收敛，stage 判
    ERROR、整条 Phase 3 停在 S002。检测本身是对的（问题真实），卡的是"自动
    修复稳定收敛"。**决策**：repair 检测/修复逻辑不动，只改终局门控——加
    `[repair].defer_unresolved_semantic`（代码默认 `false` 保留停机语义，
    `config.toml` 本项目 `true`）。开启时，某 stage 全部文件 repair 收尾后
    残留 `error` **只剩 `category=="semantic"`**（判据纯函数
    `deferrable_semantic_issues`）→ 把未决 issue 写 durable 台账
    `works/{work_id}/analysis/deferred_repairs/{stage_id}.jsonl`（每行
    stage_id/file/json_path/category/severity/rule/message；置于 `works/` 下
    非 gitignored 的 `progress/`，随 `commit_stage` 的 `git add -A
    works/{work_id}/` 一并提交），stage 当 PASS 处理 → post-repair PP rerun →
    PASSED → commit，继续下一个 stage。**边界**：只延后 semantic——残留含
    json_syntax / schema / structural / cross_file（会让下游 stage 读不了）或
    repair worker 崩溃（synthetic result 无 error issue）仍走原 hard ERROR。
    **与 triage 的区别**：triage（#25 source_inherent）处理"源小说自带 bug"，
    写 `extraction_notes/`；本决策处理"提取确有错但自动修不平"，写
    `deferred_repairs/`，两者台账与语义分离。**显式不做（登记为 todo）**：
    读台账逐条精准修的 Phase 3.5 收尾修复 pass（Part B）本轮不实现——先让
    真实台账数据积累，据此设计 fixer 形态（可给比行内 repair 更充足的预算：
    更多轮次 / 允许 T3 / 跨 stage 全局上下文），台账同时把"同类错反复出现"
    显性化，成为回改提取 prompt 的诊断信号。Plumbing →
    `extraction/persona_extraction/lifecycle/deferred_repair_log.py`（新增：
    `deferrable_semantic_issues` 判据 + `write_deferred_repairs` 台账）、
    `orchestrator.py`（Phase 3 `_process_stage` Step 4 出口三分支重构：PASS /
    DEFER / hard-ERROR）、`core/config.py` + `config.toml`（`[repair]`
    `defer_unresolved_semantic`）、`docs/architecture/extraction_workflow.md`
    + `extraction/README.md` 同步。

61. **primary / derived 二分：派生文件永不进 repair。**
    **背景**：Phase 3 首次端到端运行时 S002 收尾进入 repair 后
    `T3_EXHAUSTED` 硬 error 停机。排查发现 `world_event_digest.jsonl` 的 3 个
    S001 事件被重复 **13 次**，且 13 份副本的 `involved_characters` 各不相同
    ——证明是 **LLM 重新生成**（repair T3 `file_regen` 整文件重写），而非代码
    投影所致。根因：digest 是**派生文件**（`world stage_events` /
    `memory_timeline.digest_summary` 的 1:1 代码投影，见 #32/#33/#50），却被
    放进 repair 文件集（`_collect_stage_files` 用 `_jsonl_stage_entry` 构造
    `is_jsonl_slice` FileEntry），允许 L0–L3 checker + T0–T3 fixer（含 T3
    整文件 LLM 重写）改写它。这与 `phase3_5_consistency` §32/§33 一致性门
    **直接矛盾**——后者断言 `digest.summary` 必须逐字等于源；repair 一改，
    3.5 门必挂。设计文档本就规定 digest = 1:1 派生（`world_extraction.md`
    §7、`extraction/README.md`），repair 触碰 digest 是对项目自身设计的越界。
    **决策**：确立 **primary / derived 二分**。repair 只作用于 primary（LLM
    产出：world / character stage_snapshots + memory_timeline）；派生文件
    `world_event_digest.jsonl` / `memory_digest.jsonl` 移出 repair 文件集，
    永不进 L0–L3/T0–T3、尤其不被 T3 整文件 LLM 重写。派生正确性三层保证：
    (1) 生成器 `generate_*_digest` 确定性重投影且按主键（`event_id` /
    `memory_id`）**全量幂等去重**（`_dedup_by_key`），使重投影自愈历史遗留的
    前序重复——repair 不再碰 digest，生成器是唯一能清理它的写者；(2) repair
    修 primary 源字段后，post-repair 程序化 PP 重跑据此重新投影 digest（§11.3a
    幂等重跑，机制不变）；(3) `phase3_5_consistency` §32/§33 纯代码门断言
    `digest.summary` 逐字==源。语义错误（事实冲突等）归属 primary 的 repair，
    不在 digest 上修症状。附带：`generate_world_event_digest` 的
    `involved_characters` 归一到 `canonical_name`（新增 alias→canonical 映射，
    一角色多别名出现在同一 summary 时收敛为单条 canonical）。**目标**：减重
    （digest 永不进 LLM）+ 消除 repair 与 3.5 门的自相矛盾。**显式不做**：
    `field_patch` / `protocol` 中随 `_jsonl_stage_entry` 删除后变 dead 的
    slice-merge 基础设施（`_merge_jsonl_slice` / `current_stage_keys` /
    `is_jsonl_slice`）本轮不移除——dead 但无害，留作单独有界清理，避免 diff
    扩散到带测试的 protocol 层。Plumbing →
    `extraction/persona_extraction/orchestrator.py`（`_collect_stage_files`
    删两个 `_jsonl_stage_entry` digest 块 + dead 嵌套函数）、
    `extraction/persona_extraction/phases/post_processing.py`（`_dedup_by_key`
    + 两生成器全量去重 + `alias_to_canonical` 归一）、`docs/requirements.md`
    §「派生文件不进 repair」段改写。数据侧收尾（清 S002 已污染 digest + 修
    某角色 S002.json 的 schema 违规 + `--resume`）为独立后续，在 extraction
    分支上、待本修复经 `/forward` 合入后进行。
    → logs/change_logs/2026-07-15_134148_digest-derived-no-repair.md。

62. **repair 去掉全文重跑（T3）+ 按 rule 分层路由 + 每 tier 封顶 + defer 扩展。**
    > **经 T-FIX-FROM-FULLREVIEW 收紧三点**（2026-07-16 `/full-review`
    > H3/H4，OQ1/OQ2 用户拍板）—— 本条删 T3 的**意图**当时未在代码中完整实现：
    > 1. **`$` 根锚点 issue 永不升到 LLM 层。** 删掉 T3 却留下一条等价路径：
    >    `json_path == "$"` 的 issue 路由到 T2 后，`apply_field_patch` 的根替换
    >    分支（`if not tokens: return new_value`）会拿 LLM 返回值**整体替换整个
    >    文档**——正是全文重写换马甲。实测可把快照写成 `[]` 而 repair 报 PASS
    >    （`targets_keys_eq_baseline` 对非 dict 内容静默 `continue`，写坏的文件
    >    顺利过 L2）。修法：根锚点 issue 的 `max_tier` 钳到 T0；本就起步于 LLM
    >    层的（`start_tier >= 1`）无 fixer 可用 → `NO_FIX_TIER` → 直接 defer。
    >    **T0 仍允许**——它打的是*子*路径（`$.field`）+ 确定性默认值，从不动根
    >    本身，所以「缺顶层 required 字段」这类常见问题仍机械可修（一刀切 NO_FIX
    >    会把它们全部误判为不可修，是本次修复中途自查抓到的回归）。落 NO_FIX 的
    >    实际是三类：`targets_baseline_missing`（缺的是**兄弟**文件，重写本文件
    >    治不了）、`semantic_unavailable` / `_check_crashed` / `_unparseable`
    >    （**复审器**故障，基础设施问题不是内容缺陷）、LLM 漏写 `json_path` 的
    >    降级兜底。`json_syntax` 豁免（T0 在原始文本上修、不走
    >    `apply_field_patch`，且不可 defer——归入根锚点会让它硬 ERROR）。
    >    另加根替换类型守卫：改变文档顶层类型的根替换直接拒（T0 撞上视为不可修，
    >    留给 defer，而不是把文件搅坏）。
    > 2. **T2 也做即时 scoped 复验。** 本条只给 T1 装了"复验过了才算 resolved"
    >    的 spin 守卫，而 `semantic` / `cross_file` 全部路由 `(2,2)`——最需要
    >    复验的判断类问题恰好完全没有复验，T2 `apply == resolved`。
    > 3. **L3 gate 覆盖本轮全部被改文件。** 原以"Phase A 报过语义问题"建
    >    `l3_file_set`，但 checker pipeline 对有 L0–L2 error 的文件跳过 L3
    >    （有意设计），故"Phase A 没报语义问题"通常意味着 L3 压根没跑；结果
    >    T0 刚修完 schema 错的文件整轮零语义复审仍报 PASS（实测语义 checker
    >    调用 0 次）。
    > → logs/change_logs/2026-07-16_103421_fix-from-fullreview.md。

    **背景**：决策 #61 落地后重跑 phase 3，S001 的 repair 在
    `某角色 voice_state.target_voice_map[*].dialogue_examples` 的 `min_examples`
    （coverage_shortage）与 L3 语义 issue 之间**死循环 1.5h**——T2 fixer 凑对白
    满足 min_examples → 凑的内容触发语义矛盾 → 语义 fixer 删掉 → min_examples
    又不足；期间还触发一次 T3 全文重生烧 ~20min。逐调用分析（`logs/runs/`）显示
    T3 `file_regen` 是最贵单一事件（一次 sub_lane_regen 把 4 个 sub-lane 从头重抽
    ~17min），且 T1/T2 的 23 次 patch 里有近空转（apply 即算 resolved → 阻断升级 →
    跨轮打转）与巨型 patch（29k token，根因是 checker 把 issue 锚在大容器、T1
    `extract_subtree` 退化成整段重写）。**决策**：repair 只保留 3 层就地修复
    T0（程序 0 token）→ T1（`local_patch`，LLM，**不载 source**）→ T2
    （`source_patch`，LLM，载章节原文），**彻底删除 T3 全文重生成**（`file_regen.py`
    + `sub_lane_regen`（#55）+ `lane_regen`（#59），全 phase），**单轮** Phase A→B→C
    （删 lifecycle 2 / `max_lifecycles_per_file` / `T3_TRIGGERED` / `T3_EXHAUSTED` /
    `prior_attempt_context`）。**按 rule（回退 category）路由** `(start_tier, max_tier)`
    ——机械类 起 T0 封顶 T1；判断类无源（enum）起 T1 封顶 T1；语义 / cross_file /
    需原文 起 T2 封顶 T2；`coverage_shortage` → T2 + 0-token SourceNote 接受，不进
    fixer padding（砍 min_examples↔semantic 打地鼠源头）。**每 tier ≤2 次**，第 2
    次只针对即时复验仍未过的字段。**T1 即时复验**：apply patch 后立即 scoped
    L0–L2 复验，fingerprint 不再出现才算 resolved（止空转 spin）+ 同文件多 issue
    批量单次 call + related context 提前到 attempt 0。修不平的残留按 #60 defer
    （已扩展到 semantic/schema/structural/cross_file 四类）。decision #48 长度容差门
    保留，改在封顶后触发。**开放决策落定**：(#2) 薄内容走 coverage_shortage 接受、
    不单点修（门在跟稀疏源现实打架就改门，同 #61 哲学）；(#1) 非语义残留连 T1 都
    修不掉也 defer（承担 Phase 3.5 可能 error、人工兜底）。**净删 ~630 行**。Plumbing →
    `extraction/repair/{coordinator,protocol,field_patch}.py`、
    `extraction/repair/fixers/{local_patch,programmatic}.py`（删 `file_regen.py`）、
    `extraction/repair/checkers/{schema,semantic}.py`（叶子锚点）、
    `extraction/persona_extraction/orchestrator.py`（删 sub_lane/lane_regen 接线）、
    `lifecycle/deferred_repair_log.py`（`DEFERRABLE_CATEGORIES`）、`config.toml` +
    `core/config.py`（去 `max_lifecycles_per_file` / `t3_retry`）。
    → logs/change_logs/2026-07-15_155408_repair-no-reextract.md。

## Repository

41. Git 里不放小说 / 数据库 / 索引 / 大产物 / 真实用户 package。

42. `works/*/analysis/` + `works/*/indexes/` 作为 canonical 跟踪；`works/*/retrieval/` 仅本地。

43. `logs/change_logs/` + `logs/review_reports/` 以写为主 —— 不要主动读取。

44. `prompts/` = 仅手动场景（ingest / review / supplement / 冷启动）。抽取 prompt 在 `extraction/persona_extraction/prompts/`；runtime 规则在 `simulation/prompt_templates/`。模块自包含。
