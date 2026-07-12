<!-- holo:section start -->
<!--
维护说明 — 编辑本文件前请先阅读。
本文件是用于快速项目跟进的索引，不是详细手册。
1. 写"是什么 / 在哪找"；链向权威来源（代码路径、docs/*.md、schema、日志）。
2. 优先删除而非新增；新条目加入前先检查是否能合并进已有条目。
3. 只描述当前设计 — 不写 "legacy / deprecated / formerly / renamed from"。
4. 不出现真实产品 / 客户 / 私有内容名称 — 使用结构性占位符。
5. 精简要求：
   - 越短越好。每条都是总结，不是细节堆叠。
   - 精简的同时也要保证信息的准确性和有效性，不要为了精简而漏掉重要信息。
   - 目标每条 ≤ 5 行，更长的细节推到链接的来源里（docs/<topic>.md）。
   - 不要压缩或改动与当前编辑无关的内容。
6. Sentinel 纪律（参见 CLAUDE.md §plugin 管理段）：sentinel `<!-- holo:section start/end -->` 内的内容是 plugin canonical，`/holo:update` 会覆写；项目专属新增内容写在 sentinel 之外的 gap 里。
-->
<!-- holo:section end -->

# 操作规范 <!-- holo:heading -->

<!-- holo:section start -->
长会话中容易忘记的规则。Dilution self-check 触发条目放在
`CLAUDE.md` / `AGENTS.md`。
<!-- holo:section end -->

## Logging <!-- holo:heading -->

<!-- holo:section start -->
`logs/change_logs/` 对每次改动写一条活动日志，按文件头中的 `Type`
字段分两种形态：

- **`Type: GO`** — 由 `/go` 拥有；三时间点契约（PRE / POST /
  REVIEW），一个日志文件覆盖一次完整改动的生命周期。
- **`Type: DO`** — 由 `/do` 拥有；面向无需 PRE 阶段的快速修改，
  事后单段日志，不含 REVIEW。

通用：

- 文件名：`YYYY-MM-DD_HHMMSS_slug.md`（HHMMSS 必填；使用
  `skills_config.md` §Timezone 中的时区命令）。
- 头部携带 `Type` + `Status` 字段（确切 token 集见对应 skill 定义）。

`Type: GO` 规则：

- **PRE** — 背景 / 决策 / 计划动作清单 / 验证标准，在任何文件改动
  之前写好。
- **POST** — 已落地变更 / 与计划的差异 / 验证结果 /
  DONE|BLOCKED，在 commit 之前写好。
- **REVIEW** — 复审摘要 + REVIEWED-PASS|PARTIAL|FAIL，在 post-merge
  复审之后写。
- 无 PRE 日志 → 不准开始改文件。

`Type: DO` 规则：

- 单段日志，改动落地后、可选 commit 之前写。子段：`## Motivation` /
  `## Change list` / `## Verification summary` /
  `## Execution deviations`。
- 不要求 PRE（这是上面"无 PRE → 无改动"规则的显式例外）；纪律
  转移到用户在调用 `/do` 前先口头交代要改的范围。
- `/do` 不允许中途升级到 `/go`；改动面超出 `/do` 范畴
  （≥ 6 个文件 / 需要跨文件对齐）时，退出并改用 `/go` 重跑。

早于本约定的旧式单时间点日志保持原样；不要回溯改写或回填
`Type` 字段。

当项目使用内置的 `/go` / `/do` / `/post-check` 时，这三个 skill
拥有确切的日志格式；以它们的定义为准。
<!-- holo:section end -->

项目补充：

- 时间戳命令：`TZ='America/New_York' date '+%Y-%m-%d_%H%M%S'`。
- `/post-check` 是唯一允许向日志回写的 skill。

## Cross-File Alignment <!-- holo:heading -->

<!-- holo:section start -->
**面向 PRE-plan 的提示索引，不是穷举契约。** 仅当 lockstep 依赖
**通过普通 grep / Read 在任务时现查不出来** 才加行 —— 任何 AI
能在执行时通过扫码现场发现的依赖，不进表。拿不准时省略；
膨胀的代价高于漏项（漏的行会被 PRE-plan grep 现场补出来；膨胀
的行每次阅读都在拖累）。

每格格律 —— 每格 ≤ 1 行 / ≤ ~120 字符：

- **允许**：变更概念（左）、文件锚点列表（右）、最多一句简短的
  非显然限定语。
- **禁止**：理由散文、退役历史（"X 在某日被 Y 退役"）、实现细节
  （regex 名 / dataclass 字段 / script 函数名）、"为什么有这行"
  笔记、内嵌 step-by-step。这类内容应 **删除**，**不要** 迁移到
  `docs/architecture/`（膨胀换房间并不能解决膨胀）。

定位依据：见决策归档（`docs/decisions.md` §Skill Implementation）。

下方表格的形状（仅表头 —— 用户在下方 gap 内补行）：

| Changed | Also update |
|---------|-------------|

任何改动之后，grep 旧措辞以捕获残留引用。
<!-- holo:section end -->

| Changed | Also update |
|---------|-------------|
| `schemas/**/*.schema.json` | `docs/architecture/schema_reference.md`、`schemas/README.md`、prompt 模板、`extraction/validation/gates/phase2_baseline.py` |
| `docs/requirements.md` | `ai_context/requirements.md`、`ai_context/decisions.md` |
| 加载策略 | `simulation/retrieval/load_strategy.md`、`simulation/flows/startup_load.md`、`simulation/retrieval/index_and_rag.md`、`docs/architecture/data_model.md`、`ai_context/architecture.md` |
| 提取工作流 | `docs/architecture/extraction_workflow.md`、`extraction/persona_extraction/prompts/`、`extraction/persona_extraction/`、`ai_context/architecture.md` |
| 运行时 prompt | `simulation/prompt_templates/`、`simulation/` |
| 任何持久性决策 | `ai_context/decisions.md` |
| `/go` 或 `/post-check` 运行 | `logs/change_logs/` PRE / POST / REVIEW 段齐全 |
| skill 使用的项目专属锚点（后台进程、受保护分支前缀、main 分支策略、do-not-commit 路径、source / data-contract / example-artifact 目录、核心组件关键词、敏感内容规则、时区） | `ai_context/skills_config.md` 对应段 |
| `structure_mode` | `schemas/{work/{work_manifest,works_manifest,chapter_index},analysis/stage_plan}.schema.json`、`extraction/ingestion/validator.py`、`extraction/persona_extraction/{cli,orchestrator,lifecycle/manifests,lifecycle/progress}.py`、`prompts/ingestion/原始资料规范化.md`、`docs/requirements.md` §8.4/§9.2、`docs/architecture/{schema_reference,extraction_workflow}.md`、`ai_context/{architecture,decisions}.md` |
| `schemas/analysis/chapter_summary_chunk.schema.json`（chunk schema 字段/边界） | `extraction/persona_extraction/prompts/summarization.md`、`extraction/persona_extraction/prompts/analysis_{foundation,stage_plan,candidate_characters}.md`、`extraction/persona_extraction/prompt_builder.py` 的 `_project_chunk_for_*` 三个投影器、`docs/architecture/{schema_reference,extraction_workflow}.md`、`ai_context/{architecture,decisions}.md`（phase 2 不再消费 chunk-level 字段，决策 #54） |
| `schemas/world/foundation.schema.json`（phase 1 foundation lane 落盘 + phase 2 `key_figures` 补齐，决策 #54） | `extraction/persona_extraction/prompts/analysis_foundation.md`、`extraction/persona_extraction/prompts/baseline_production.md`、`extraction/persona_extraction/prompt_builder.py`（`build_foundation_prompt` / `build_baseline_prompt`）、`extraction/persona_extraction/orchestrator.py`、`extraction/validation/gates/phase2_baseline.py`、`schemas/README.md` + `extraction/README.md`、`docs/architecture/{schema_reference,extraction_workflow}.md`、`ai_context/{architecture,decisions}.md` |
| `schemas/character/stage_snapshot.schema.json` 顶层属性增删 / 重命名（含 `stage_delta` / `failure_modes` / `behavior_state` 子键） | `extraction/persona_extraction/phases/snapshot_merge.py::FIELD_ALLOCATION` + `SHARED_KEY_SUBKEYS`（新增 / 改名属性必须挂到某 sub-lane，否则 merge hard gate 报错）、`extraction/persona_extraction/prompts/character_snapshot_extraction.md` `{lane_scope}` 白名单段、`docs/architecture/extraction_workflow.md` §6.2、`ai_context/decisions.md` #55、`docs/requirements.md` §9.3 |

## Single Source of Truth <!-- holo:heading -->

<!-- holo:section start -->
当同一个值（一个数值边界、一个路径前缀、一个 enum、一个 regex
模式）出现在多个地方时，把它写在**一个权威位置**，让其余每处都
引用或派生自该处。按项目类型常见的权威位置：

- **Schema**（`*.schema.json`、Pydantic、Protobuf、SQL DDL）用于
  数据形状边界：`maxLength`、`maxItems`、`required`、enum 值。
- **Config 文件**（TOML / YAML / `.env`）用于运行时常量。
- **代码常量**用于共享行为阈值。

反例：在 prompt 模板里硬编码 "150–250 chars" 散文，同时在 schema
里写 `maxLength: 200`。两者会静默漂移 — 有人改了一处，忘了另一处，
不一致几个月后才以令人困惑的 bug 形式浮出。

当重复无法机械消除时（例如文档里的散文示例），把这条关联作为一行
记录到 §Cross-File Alignment，让镜像更新成为清单项，而不是依赖
记忆。
<!-- holo:section end -->

## Identifier Renames <!-- holo:heading -->

<!-- holo:section start -->
跨仓重命名标识符时，单一字面量 grep **不够** — 标识符会渗透进多
种语法形态。声明"无残留"之前，跑完全部四种扫描：

1. **字面量名称** — 项目使用的每种命名形式中的旧名
   （`old_name`、`OldName`、`OLD_NAME`）。
2. **模式内引用** — regex 字符串、schema `pattern` 字段、glob 模式、
   路由路径，或任何硬编码旧名或其前缀的字符串。零填充的数字 ID
   常藏在像 `"^\\d{4}$"` 这样的 regex 里。
3. **格式化字符串模板** — `f"...{var:fmt}..."`（Python）、模板字面量
   （JS）、`printf` / `format!`（Rust）。用**通用的** regex 抓取
   任何变量名绑定（例如 `\{[a-z_]+:04d\}` 抓零填充整数）— 千万
   不要用特定变量名。否则使用不同变量名的同类代码会静默漏掉。
4. **散文 / 示例提及** — 文档、README、ai_context 条目、commit 消息
   示例中在正文里引用旧名的地方。

将历史冻结目录从扫描中排除：`logs/change_logs/`、
`logs/review_reports/`、已归档 todo、git 历史本身。

规划重命名时把这四种扫描编入 PRE 日志的验证标准段，便于改动后
复审独立校验每一种。
<!-- holo:section end -->

项目专属扫描参数（示例：`chapter0001` → `C0001`、`stage0001` → `S001`）：

- 扫描范围：`schemas/` / `prompts/` / `extraction/` / `docs/` /
  `ai_context/` / `simulation/`。
- 排除（合法携带历史快照）：`sources/` / `users/` / `works/` /
  `logs/change_logs/` / `docs/todo_list_archived.md`。
- 本项目的具体形态：旧字面量前缀 `chapter[0-9]{4}` / `stage[0-9]{4}`；
  JSON Schema 裸数字模式 `"\^\\d{4}\$"` / `"\^\\d{4}-\\d{4}\$"`；
  Python 零填充 f-string 通用 regex `\{[a-z_]+:04d\}`（适用于路径拼接、
  dict-key 构造、log/print f-string，以及任何 `f"...{var:04d}..."` 位点）；
  文档 / 示例中的文件名字面量 `0001\.txt` / `"0001-0010"`。

## Generic Placeholders <!-- holo:heading -->

<!-- holo:section start -->
权威文档（本目录、`docs/`、schema、prompt）在语气上保持
项目无关：

- 不出现真实客户 / 产品 / 私有内容名称。
- 示例使用结构性占位符。
- 不写历史叙事（"legacy"、"deprecated"、"formerly"、
  "renamed from"）— 只描述当前设计。

例外（历史本身就是重点）：`logs/change_logs/`、
`logs/review_reports/`、归档 todo、`docs/decisions.md`
（决策归档 —— supersede 痕迹放那里，永不进
`ai_context/decisions.md` 索引）、git commit 消息。
<!-- holo:section end -->

项目补充：

- 权威文档范围：`schemas/`、`docs/requirements.md`、`docs/architecture/`、
  `ai_context/`、`prompts/`、`extraction/persona_extraction/prompts/`。
- "真实名称"在本项目指真实书名 / 角色 / 地点 / 情节名称；示例占位符
  如 `<character_id>`、`S001`。
- Schema `description` 示例保持结构性、非叙事性（或直接省略）。
- 额外例外：`docs/todo_list_archived.md`、`ai_context/decisions.md`、
  `works/*/` 样例输出、`sources/`（源文本包本身即真实内容，输入层
  天然携带真实名称）。

## Naming and Identifiers <!-- holo:heading -->

- 中文作品 → 中文 `work_id`、`character_id`、路径段。
- `stage_id` = `S###`（3 位零填充），与
  `M-S###-##` / `E-S###-##` / `SC-S###-##` / `SN-S###-##` ID 家族对齐。
- `stage_title` = 人类可读短名（作品语言；长度上限在 schema 里）；
  在 `stage_plan.json` 和每个 `stage_catalog.json` 条目里
  与 `stage_id` 平级；bootstrap 阶段选择时展示的标签。
- `chapter_id` = `C####`（4 位零填充），由
  `schemas/work/chapter_index.schema.json` `pattern: "^C[0-9]{4}$"` 强制。
  `volume_id`（可选，仅多卷来源）= `V###`
  （3 位零填充）。宽度拆分理由：单部作品章节数可达数千
  （≤ 9999 足以覆盖）；卷数保持很小
  （≤ 999），因此 `V###` 让 ID 紧凑且无歧义。
- `ai_context/` 保持英文。JSON 字段名可以是英文；
  内容文本跟随作品语言。

## Data Separation <!-- holo:heading -->

- 用户数据放在 `users/` 下；绝不从用户上下文写 canon。
- `identity.json` + `target_baseline.json` 是角色级恒定基线（Phase 2 产出，Phase 3 起不可变）；voice / behavior / boundary / failure_modes 内联在 `stage_snapshot` 里并逐 stage 演化。Phase 3 stage_snapshot 三个结构（`voice_state.target_voice_map` / `behavior_state.target_behavior_map` / 顶层 `relationships`）的键必须与 `target_baseline.targets[].target_character_id` **集合相等**（双向跨文档硬失败；用内容空性表达三态 — 已出场 = 填写，曾出场 = 继承，从未出场 = 空条目；fixed_relationship 例外：被 `world/foundation/fixed_relationships.json` 绑定时可预填 relationships 条目的关系字段）。校验在 phase 3 单 stage validate 层运行（与 schema validate 平级），违规走文件级 repair 生命周期（L1/L2/L3）；phase 2 漏掉 target 时手工修基线并重跑受影响的 stage。
- Stage snapshot **自包含** — 运行时加载 identity + 当前 stage_snapshot；不做基线合并。
- **边界只写在 schema。**所有 `maxLength` / `minLength` / `maxItems` / `required` 都放在 `schemas/**.schema.json`；其他任何地方不留副本。确切数值 → schema 文件。索引 → `docs/architecture/schema_reference.md`。单个边界的跨 schema 共享通过 `$ref` 指向共享片段实现，片段就近放在它所服务的 schema 所在的领域目录里（例如 target 数组上限由 `target_baseline.targets` + stage_snapshot 的三个 target 结构共享，两者都在 `schemas/character/`，所以片段作为 `schemas/character/targets_cap.schema.json` 放在那里）。仍是单一来源，无重复。
- **边界是上限，不是目标。**每个提取 prompt 模板必须显式告诉 LLM：`maxLength` / `maxItems` 是**硬上限，不是配额** — 写原文里真实存在的内容，不要为凑满上限而填充 / 注水 / 编造条目。缺了这句，模型会因为"schema 说 ≤N"而默认每个数组正好写 N 条。
- **maxItems 感知的截断。**字段超出 `maxItems` 上限时，由 LLM 在提取过程中排序 + 截断（而不是事后靠 schema 失败兜底）。优先级锚点：当前 stage 相关性 → identity 锚点关系 → 覆盖广度 → 跨 stage 稳定性（针对 `failure_modes` 这类全量演化字段）。子类独立计数 maxItems。→ `extraction/persona_extraction/prompts/character_snapshot_extraction.md` §maxItems 触顶时的裁剪规则。
- **snapshot 上不留章节锚点。**任何 schema（world / character / `stage_snapshot` / `memory_timeline`）都不携带 `evidence_refs` / `source_type` / `scene_refs`；`dialogue_examples` / `action_examples` 里没有逐条的 `evidence_ref`。锚定使用 `timeline_anchor`（world 另加 `location_anchor`）和 `memory_timeline`。
- **`stage_catalog`** — world 目录表在 `schemas/world/world_stage_catalog.schema.json`；character 目录表在 `schemas/character/stage_catalog.schema.json`。两者都仅供 bootstrap，不做运行时加载；按 `stage_id` 字典序排序（无 `order` 字段）。`snapshot_path` 不同：character → `canon/stage_snapshots/{stage_id}.json`；world → `world/stage_snapshots/{stage_id}.json`。

## Git <!-- holo:heading -->

三分支模型（main 是唯一会推到 remote 的分支）：

| 分支 | 角色 | 是否推 remote？ |
|---|---|---|
| `main` | 仅框架 — 代码 / schema / prompt / docs / `ai_context/` / skill。永不携带真实 work ID、原著小说或提取产物。 | ✅ |
| `extraction/{work_id}` | 逐作品进行中的提取。每个通过的 stage 都 commit。 | ❌ 仅本地 |
| `library` | 已完成作品的归档。每个完结的 `extraction/{work_id}` squash-merge 到这里。 | ❌ 仅本地 |

流转规则：

- 默认分支 = `main`。除非正在运行提取，否则待在 `main` 上。
- 代码 / schema / prompt / docs / `ai_context/` / skill 的 commit 先进 `main`；extraction 和 library 分支通过 `git merge main` 同步。
- `extraction/{work_id}` 只携带 stage 输出。**完成时 squash-merge 到 `library`**（永不进 main — main 必须保持无产物）。
- **squash-merge 成功后，orchestrator 交互式询问（`[y/N]`，默认 N）是否删除来源 `extraction/{work_id}` 分支（`git branch -D`）并运行 `git gc --prune=now`**，让累积的 regen commit 变为不可达并被回收。删分支是破坏性操作 — 即便 `[git].auto_squash_merge=true`，该询问也总会运行。一旦用户选择删除，`library` 上的 squash 就是唯一保留的记录；`extraction/{work_id}` 是可丢弃的草稿区。
- `library` 定期 `git merge main` 吸收框架更新；永不回流到 main。
- 永不 commit：小说、数据库、embedding、缓存、真实用户包、`main` 上以真实 `work_id` 命名的 manifest。
- 不要 amend 他人的 commit。

## Post-Change Checklist <!-- holo:heading -->

<!-- holo:section start -->
1. 所有对齐文件都更新了吗？（上方 Cross-File Alignment 表）
2. 改动之前写了 PRE 日志、commit 之前写了 POST 日志吗？
3. `ai_context/` 仅在改动具有持久性时才更新了吗？
4. grep 过对旧名 / 旧路径 / 旧值的残留引用吗？
   （标识符重命名请使用 §Identifier Renames 的四种扫描。）
5. 如果代码或 schema 改了，跑了 smoke test 或类型检查吗？
<!-- holo:section end -->

项目补充：代码 / schema 改动的 smoke test = Python import smoke test。
