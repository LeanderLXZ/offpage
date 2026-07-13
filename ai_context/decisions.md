<!-- holo:section start -->
<!--
MAINTENANCE — 编辑本文件前请先阅读。
本文件是决策的索引（INDEX），不是决策本身。
1. 每条 entry 1–2 行：一行决策陈述 + `→ docs/decisions.md #N`。完整条目（理据 / 边界 / 指针）放在 `docs/decisions.md` 同编号下。
2. 准入判据：只记录当时确有争议的决策 —— 存在像样的备选方案、且未来可能被重新提出。显然的 / 无争议的选择不立条目。
3. 优先就地替换 / 删除而非新增；新增前先检查是否能并入已有条目。
4. 只描述当前设计 —— 不写"legacy / deprecated / formerly / renamed from"。
5. 不出现真实产品 / 客户 / 私有内容名称 —— 使用结构性占位符。
6. 本文件 + `docs/decisions.md` 是一对 lockstep —— 同编号、同主题分节；改其一必须同步改另一个（若项目在 §Cross-File Alignment 维护行，可把这一对登记为一行）。
7. Sentinel 纪律（参见 CLAUDE.md §plugin 管理段）：sentinel `<!-- holo:section start/end -->` 内的内容是 plugin canonical，`/holo:update` 会覆写；项目专属新增内容写在 sentinel 之外的 gap 里。
-->
<!-- holo:section end -->

# 关键决策 —— 索引 <!-- holo:heading -->

<!-- holo:section start -->
持久性工程决策的索引：每条决策 1–2 行 —— 决策陈述本身 + 指向
`docs/decisions.md` 完整条目的指针（同 `#N`）。本文件在每个会话
开始时被读取，因此在结构上保持轻量：陈述放这里，理据放
`docs/decisions.md`，完整讨论历史存放于
`logs/change_logs/<slug>.md`。会话开始时永不加载
`docs/decisions.md` —— 需要某条决策的"为什么"时按需查阅。
<!-- holo:section end -->

## 格式 <!-- holo:heading -->

<!-- holo:section start -->
每条 entry 是一个 1–2 行的编号块：

```
N. <决策陈述，一行>。
   → docs/decisions.md #N
```

只看决策陈述就应能知道"什么已有定论"；为什么放在归档条目里。
当某句理据是承重的（会改变读者的下一步动作）时，可以并入首行 ——
但边界、实测数据、历史沿革永远不放这里。

**准入判据：** 只在"当时存在像样的备选方案、且未来读者可能重新
提出它"时才立条目。试金石：没有这条 entry，一个不知情但有能力的
人会做出不同选择吗？不会 → 不立。

**编号 —— 全局 append-only，与 `docs/decisions.md` 共享：**

- 编号全局、不分节，且两文件完全一致：索引 `#N` ⇔ 归档 `#N`，
  要么都有、要么都没有。
- 追加前扫本文件 `max(N)`；新条 = `max + 1`。同一趟里在这里追加
  索引行、在 `docs/decisions.md` 追加完整条目。
- 永不重号已有 entry —— 下游代码 / docs / log 用 `#N` 引用。
- 永不填洞；append-only 下 gap 是正常的。
- 节内视觉顺序不是数字顺序（节按主题聚，编号按落地时间聚）。

**引用语义：** `decisions.md #N` 指索引（本文件）—— 稳定的公共
引用。`docs/decisions.md #N` 指归档条目 —— 需要专指理据或边界时
使用。

**就地替换**（决策变了，主题还相关）：在**两个文件里**都用新决策
替换 entry 内容。编号不变。前提：(a) 旧信息确认已失效；(b) 下游
引用旧决策的文件已更新。若被替换的方案曾被实际尝试后退回，在归档
条目里保留半行痕迹 —— `（曾试 X，退回，见 log）` —— 防止失败路径
被再次提出；索引行只描述当前决策。

**删除条目**（主题完全不相关了）：从**两个文件里**删掉 entry；gap
保留（永不重号填洞）。前提：(a) 信息确认已失效；(b) `grep -rn
"decisions.md #<N>" . --exclude-dir=logs` 返回 0 live 引用。若信息
已失效但 `logs/` 之外仍有 live 引用 → 询问用户决定。
<!-- holo:section end -->

## 段（按主题组织） <!-- holo:heading -->

<!-- holo:section start -->
随决策日志增长，挑选稳定的主题化标题 —— 例如
"Data Separation"、"Runtime Loading"、"Schema Bounds"。
`docs/decisions.md` 使用**相同的**节标题；一条决策的索引行和归档
条目位于相互对应的节下。同一节内的决策仍按全局（整文件）编号。
<!-- holo:section end -->

## Roleplay Philosophy

1. 优先级 = 深层行为 / 决策一致性，而非语气模仿。
   链条：记忆 + 关系 → 心理反应 → 行为 → 语言。
    → docs/decisions.md #1。

2. 客观事实与主观认知必须分离 —— 角色可能误解、隐瞒、扭曲。
    → docs/decisions.md #2。

3. 保留阶段差异；不压平成一份无时间维度的静态档案。
   → `project_background.md`、`simulation/prompt_templates/`。
    → docs/decisions.md #3。

## Data Separation

4. 用户数据与角色 canon 数据分离。用户侧永不漂移进 canon。
    → docs/decisions.md #4。

5. 世界是一等层级，不放在角色笔记内部。
    → docs/decisions.md #5。

6. 世界 canon 只凭源文证据修订 —— 永不因用户对话改动。
    → docs/decisions.md #6。

7. 冲突 / 修订显式记录，不静默覆写。
   → `conventions.md` §Data Separation + `docs/architecture/data_model.md`。
    → docs/decisions.md #7。

## Work Scope

8. 每部小说 = 独立命名空间（`work_id`）。用户流程先选作品、再选角色。
    → docs/decisions.md #8。

9. 中文作品：中文 `work_id`、实体名、标识符取值、路径段。
    → docs/decisions.md #9。

10. `ai_context/` 与 `docs/` 的书面语言跟随 `skills_config.md` §Language 的 `content_language`（当前 zh）；代码标识符与 JSON 字段名保持英文。（含子条目 10a，细节见归档）
    → docs/decisions.md #10。

## Character Depth

11a. `identity.json` 承载 `core_wounds`（根源创伤 + 行为影响）+ `key_relationships`（含初始状态 / 演化 / 转折点的关系弧线）。
    → docs/decisions.md #11a。

11b. `behavior_state` 把 `core_goals`（理性、可重排优先级）与 `obsessions`（非理性、创伤 / 情绪绑定、不做成本收益计算）分开。
    → docs/decisions.md #11b。

11c. `stage_snapshot` 内的 `character_arc` = 从 stage 1 → 当前的鸟瞰。与 `stage_delta`（仅上一步）互补。
    → docs/decisions.md #11c。

11d. **角色 voice / behavior / boundary / failure_modes 内联在 stage_snapshot 中。**
    → docs/decisions.md #11d。

11e. **maxItems 感知的裁剪规则（通用）。** 所有抽取 prompt 必须指示 LLM 在抽取时就按 `maxItems` 上限 排序 + 截断（而不是溢出后 schema fail），优先级锚点： 当前 stage 相关性 → identity 锚点关系（core_wounds / key_relationships）→ 覆盖广度 → 跨 stage 稳定性（针对 `failure_modes` 这类全量演化字段）。
    → docs/decisions.md #11e。

11f. **prev_stage 四态抽取规则。**
    → docs/decisions.md #11f。

## Extraction Model

12. stage（抽取）= stage（runtime），1:1。按自然故事边界 （目标 10，最少 8，最多 15）。累积 1..N。
    → docs/decisions.md #12。

13. Phase 2 从全书上下文产出世界 foundation + per-character `identity.json` + per-character `target_baseline.json` 草稿 （没有独立的 voice / behavior / boundary / failure_modes baseline 文件 —— 那些住在 `stage_snapshot` 里）。
    → docs/decisions.md #13。

14. 没有 per-stage 报告文件；进度就地记录。
    → docs/decisions.md #14。

15. `target_voice_map` / `target_behavior_map` 条目全部以 `target_character_id` 为 key（与 `baseline.targets[].target_character_id` 集合相等，见 #13）；详略随 `tier` 变化 —— 核心 / 重要目标 ≥3–5 个示例，次要 / 普通目标保持简短，从未出场的 baseline 目标保留空 entry（D4 状态 3）以维持跨文档 集合相等。
    → docs/decisions.md #15。

## User Model

16. 一个 `user_id` = 一个锁定的 作品-目标-对手方 绑定。Setup 时锁定；变更需要新 package 或显式迁移。
    → docs/decisions.md #16。

17. 有 canon 依据的用户角色默认继承目标 stage。
    → docs/decisions.md #17。

18. 会话 / 上下文状态持续更新。长期档案 + 关系内核只在显式 merge 确认后更新。
    → docs/decisions.md #18。

19. Per-context 的 `character_state.json` 实时跟踪情绪、性格、语气、约定、关系增量、事件、记忆 —— 仅在 merge 时晋升为长期。
    → docs/decisions.md #19。

20. Merge 是 append 优先。事件 / 记忆只添加，永不覆写。
    → docs/decisions.md #20。

21. 会话关闭是显式动作。系统询问是否 merge。
    → docs/decisions.md #21。

22. 完整逐字稿留在本地；启动只加载摘要层。（含子条目 22a–22b，细节见归档）
    → docs/decisions.md #22。

## Automated Extraction (non-obvious)

23. 每次 phase 调用都是全新的 `claude -p` / `codex` —— 无共享会话
    记忆。步骤间上下文基于文件。
    → docs/decisions.md #23。

24. 抽取 prompt 不读 `memory_digest.jsonl`、`world_event_digest.jsonl`、`stage_catalog.json`。自包含的 snapshot 契约内嵌在 prompt 中；digest / catalog 由 `post_processing.py` 程序化维护（0 token，幂等）。
    → docs/decisions.md #24。

25. Per-stage 质量门 = `repair`（统一的 check + fix + verify）。Checker L0–L3 × fixer T0–T3，正交；field-level json_path patch。（含子条目 25a，细节见归档）
    → docs/decisions.md #25。

26. 抽取跑在 `extraction/{work_id}` 分支上。每个通过的 stage 都提交。回滚 = `git reset`。
    → docs/decisions.md #26。

27. Orchestrator 预先计算每次调用的读取清单（仅最新 snapshot + memory_timeline）。Agent 不自由探索。（含子条目 27a–27m，细节见归档）
    → docs/decisions.md #27。

## Memory System

28. 三层记忆（`stage_snapshot` / `memory_timeline` / `scene_archive`）。没有独立的对话语料库。
    → docs/decisions.md #28。

29. ID 约定 `{TYPE}-S{stage:03d}-{seq:02d}`，用于 `M-` / `E-` / `SC-`。
    → docs/decisions.md #29。

30. 模拟角色 A 时只加载 `characters_present` 含 A 的场景与 A 自己的 `memory_timeline`。
    → docs/decisions.md #30。

31. `stage_events` 仅限世界公开层（50–100 CJK 字，硬门）。个人 / 内在条目属于角色 `memory_timeline`，永不进 world。
    → docs/decisions.md #31。

32. `world_event_digest.summary` = 源 `stage_events` 的 1:1 拷贝（写入时由 prompt + repair agent 强制）。5 级重要度按关键词推断；默认 significant。
    → docs/decisions.md #32。

33. `memory_digest.summary` = `digest_summary` 的 1:1 拷贝（30–50 CJK 字，硬门）。
    → docs/decisions.md #33。

34. 角色 `stage_snapshot.stage_events` = 仅本 stage（50–80 CJK 字，硬门），不累积。跨 stage 历史在 `memory_timeline` + `memory_digest` + `world_event_digest`。
    → docs/decisions.md #34。

35. `fixed_relationships.json`（血缘 / 宗族 / 阵营）不依赖 stage。Phase 2 出骨架；后续 stage 可修正。Runtime Tier 0。
    → docs/decisions.md #35。

## Retrieval

36. 两级漏斗：Level 1 jieba + 词表 dict + FTS5（<20ms，默认）；Level 2 经 LLM tool use 的 embedding（罕用）。单一 SQLite —— 无独立向量库。
    → docs/decisions.md #36。

37. 主动式上下文状态联想：引擎每轮抽取地点 / 近期事件 / 情绪 / 对话对象做 jieba 匹配 —— 不只匹配用户输入。
    → docs/decisions.md #37。

38. 词表 dict（作品级，jieba 自定义格式）由抽取产物自动生成。`works/{work_id}/indexes/vocab_dict.txt`（提交）。
    → docs/decisions.md #38。

39. 检索产物放在 `works/{work_id}/retrieval/`（不提交）。Phase 4 中间产物 `works/{work_id}/analysis/scene_splits/` 必须不被 git 跟踪（否则回滚 `git checkout --` 会静默销毁它们）。（含子条目 39a，细节见归档）
    → docs/decisions.md #39。

## JSON Repair

40. LLM 产出的 JSON 常有格式错误（未转义引号、尾逗号、截断）而内容完好。Phase 0 三级 修复：L1 regex（0 token）→ L2 LLM 只修破碎 JSON （最小化）→ L3 全量重跑（最后手段）。
    → docs/decisions.md #40。

## Configuration & Runtime Resilience

45. 单源 TOML 配置在 `extraction/config.toml`（loader `extraction/persona_extraction/core/config.py`）。
    → docs/decisions.md #45。

46. Token 限额自动暂停（订阅模型，§11.13）—— `RateLimitController` 解析 DST 感知的 reset，写 flock 合并的 `rate_limit_pause.json`，在预启动 + 每次 `run_with_retry` 处阻塞，reset 后重跑失败的 prompt 且不消耗重试槽。
    → docs/decisions.md #46。

47. Phase 0 摘要子进程超时 = `[phase0].summarize_timeout_s`（默认 1800s），而不是历史上借用的 `[phase3].review_timeout_s`（600s）。
    → docs/decisions.md #47。

48. **长度 bound 容差门（B 方案）。**
    → docs/decisions.md #48。

49. **Phase 0 降档 effort 的恢复扫尾（per-chunk 定向救火）。** opus-4-7 effort=max 在 phase 0 的多字段 chunk 综合（读 `chunk_size` 章 → 写 N× per-summary + 5 个 chunk 级二级聚合）上随机触发超出 1800s 子进程 wall 预算的服务端超长 thinking。
    → docs/decisions.md #49。

50. **Post-processing 对 derived digests 永远走 replace-slice 语义。**
    → docs/decisions.md #50。

51. **CLI `--resume` 阶段无关续跑契约。**
    → docs/decisions.md #51。

52. **Phase 1 三 lane 并行 + 字段裁剪 + light_novel stage_plan 跳过 LLM。**
    → docs/decisions.md #52。

53. **Analysis schema 收紧 v2 + Phase 1.5 推荐规则化。** 2026-05-08 跑完一次端到端 phase 0 + 1 + 1.5 + phase 2 部分（被 SIGTERM 中止），看实际产物决定收紧三组 analysis schema。
    → docs/decisions.md #53。

54. **Foundation 前移 phase 1 + phase 2 仅补 `key_figures` + target_baseline 准入门槛收紧（dialogue/action 交互）。**
    → docs/decisions.md #54。

55. **char_snapshot lane 拆 4 sub-lane 并行 + prev snapshot 按 lane 切片喂入 + 程序 merge + lifecycle 2 sub-lane 重抽。**
    → docs/decisions.md #55。

56. **Pipeline-resume alignment 三处修复 — `pipeline.json` schema_version 启动、phase 2 recovery 阻 phase 3 committed 产物、`--end-stage` daemon 路径"empty = 全跑"语义贯通。**
    → docs/decisions.md #56。

58. **Foundation schema 收紧（核心字段 required）+ `key_figures` required allow-empty + Phase 2 不再让 LLM 写空 stage_catalog。**
    → docs/decisions.md #58。

59. **Phase 2 baseline 拆 2+2N lane 并行 + per-lane repair 缩水版接入。** lane A `key_figures` 先行串行，fixed_relationships + 每角色 identity / target_baseline 两 lane 并行（输入按 lane 投影裁剪）；repair 只开 T0/T1 + 程序 checker（`source_context=None`，L3/T2/triage 不开），T3 = `lane_regen` 重跑本 lane，终点 `validate_baseline` 保留为最后安全阀。
    → docs/decisions.md #59。

## Repository

41. Git 里不放小说 / 数据库 / 索引 / 大产物 / 真实用户 package。
    → docs/decisions.md #41。

42. `works/*/analysis/` + `works/*/indexes/` 作为 canonical 跟踪；`works/*/retrieval/` 仅本地。
    → docs/decisions.md #42。

43. `logs/change_logs/` + `logs/review_reports/` 以写为主 —— 不要主动读取。
    → docs/decisions.md #43。

44. `prompts/` = 仅手动场景（ingest / review / supplement / 冷启动）。抽取 prompt 在 `extraction/persona_extraction/prompts/`；runtime 规则在 `simulation/prompt_templates/`。模块自包含。
    → docs/decisions.md #44。
