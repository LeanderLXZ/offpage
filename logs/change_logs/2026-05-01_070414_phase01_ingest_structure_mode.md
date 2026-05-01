# phase01_ingest_structure_mode

- **Started**: 2026-05-01 07:04:14 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

`docs/todo_list.md` 的 `T-INGEST-STRUCTURE-MODE` 条目（2026-04-30 提出 / 2026-05-01 收敛锁定）。
2026-04-30 接入新增 22 卷结构化多卷轻小说 fixture 时，暴露 phase 0/1
当前流程仅为单卷非结构化中文网络小说（既有 fixture）设计：phase 0 按
token-budget 启发式切 batch、phase 1 自主发现 stage 边界。多卷轻小说的
天然结构（卷 → 印刷章 → sub-section）这套流程没有利用，且
`1 stage = 1 sub-section` 的粒度需求与启发式不匹配。

用户消息：`T-INGEST-STRUCTURE-MODE /go` —— 2026-05-01 收敛已拍板 8 条
直接落盘。

## 结论与决策

按 `docs/todo_list.md` § `[T-INGEST-STRUCTURE-MODE]` "已拍板（2026-05-01
收敛）" 8 条执行。要点：

1. phase 0/1 引入双模式调度信号 `structure_mode: "monolithic" | "light_novel"`，
   default `"monolithic"`（既有 fixture 向后兼容）
2. 真相源 = source manifest（normalization 写入），works manifest 在
   phase 0 init 时复制；validator 跨文件断言两边一致
3. light_novel 三层 seq 全部 required：`volume_id` (V###) + `volume_seq`
   (int≥1) + `original_chapter_seq` (int≥1) + `original_sub_chapter_seq`
   (int≥1)；`volume_title` / `original_chapter_title` optional。
   **重命名**：原 `volume_chapter_seq` → `original_sub_chapter_seq`
   （语义保持"在所属 original_chapter 内 1 起递增、过原章重置"，仅改名
   以与新增的 `original_chapter_seq` 区分层级）
4. `chapter_index.schema.json` items 改 `oneOf` 双 profile：
   - monolithic profile：禁用 6 个 light_novel 字段（`additionalProperties: false`）
   - light_novel profile：required 4 个 seq 字段，optional 2 个 title 字段
   - title 始终 required (minLength 1)
5. title 由 normalization 派生：
   `f"{volume_title or '第N卷'} {original_chapter_title or '第M章'} {original_sub_chapter_seq}"`
6. light_novel 模式仍跑 phase 0 LLM chunk_summary + phase 1 LLM stage_summary
   （每 sub-section 一次，接受冗余换代码复杂度收敛）
7. light_novel 模式绕过 phase 1 STAGE_MIN / STAGE_MAX chapter_count 校验
8. structure_mode 由 normalization LLM 形态识别 → **本次不做**（独立后续
   todo），暂时靠 manifest 手填 `structure_mode` 跑通

phase 2+ 不分叉：统一消费 stage_plan，volume / 印刷章语义由 chapter_index
profile-B 字段携带，character / world schema 不动。

## 计划动作清单

Schema：

- file: `schemas/work/chapter_index.schema.json` — items 改 `oneOf` 双
  profile；monolithic 禁 6 字段、light_novel 必填 4 + 可选 2；重命名
  `volume_chapter_seq` → `original_sub_chapter_seq`；新增 `volume_seq` /
  `original_chapter_seq` / `original_chapter_title`
- file: `schemas/work/work_manifest.schema.json` — 加 `structure_mode`
  enum (`monolithic` / `light_novel`)，default `monolithic`；source 与
  works 两端均复用本 schema（参见 `automation/ingestion/validator.py`
  REQUIRED_FILES + decisions.md §27a）
- 检查 `schemas/analysis/`、`schemas/work/` 下间接引用 chapter_index 的
  schema，确认 oneOf 拆分不破坏下游引用（预期无破坏：`stage_plan` /
  `chapter_summary_chunk` 只引用 `chapter_id`，与 profile 无关）

Code：

- file: `automation/ingestion/validator.py` — 加跨文件断言：
  source `manifest.json::structure_mode` ⇔ source
  `metadata/chapter_index.json` items profile（monolithic items 不含
  volume_id 等 6 字段；light_novel items 含全部 4 必填）
- file: `automation/persona_extraction/manifests.py::write_works_manifest`
  L60+ — 从 source manifest 拷 `structure_mode` 字段写入 works manifest；
  断言一致
- file: `automation/persona_extraction/orchestrator.py` phase 0 入口
  （`run_summarization` L695+）— 分支：light_novel 则
  `chunks = [(i+1, i+1, i+1) for i in range(total_chapters)]`（1
  chapter = 1 chunk = 1 sub-section），跳过 token-budget batch 逻辑；
  chunk_summary 落盘 schema / 路径 / 命名不变
- file: `automation/persona_extraction/orchestrator.py` phase 1 入口
  （`run_analysis` L914+）— 分支：light_novel 跳过 boundary discovery，
  1:1 派生 stage_plan（不调 LLM 走 prompt 路径，而是程序构造）：
  - `stage_id = S{n:03d}` 顺序号（1 起）
  - `chapters` 单字符串：`f"{volume_id}-{original_chapter_seq:02d}-{original_sub_chapter_seq:02d}"`
    （例 `"V001-02-03"`；3 字段组合保证全书唯一）
  - `chapter_count = 1`
  - `stage_title = chapter_index[i].title`
  - 仍写 `world_overview.json` / `candidate_characters.json` 由 LLM 走
    （或暂时输入空白模板，待后续完善）
- file: `automation/persona_extraction/orchestrator.py` L982+ phase 1
  exit validation — light_novel 模式下绕过 STAGE_MIN / STAGE_MAX 限制
- file: `prompts/ingestion/原始资料规范化.md`（具体 ingest prompt 路径
  /go 内 grep 定位）— 加 light_novel 形态识别（手填占位 → 后续接 LLM
  判定）+ chapter_index profile B 字段填充指引 + title 派生公式

ai_context / docs：

- file: `ai_context/architecture.md` — 增加双模式调度说明（phase 0/1 两
  种走法 + structure_mode 字段位置 + light_novel stage 1:1 派生规则）
- file: `ai_context/decisions.md` — 记三条决策：structure_mode 调度信号；
  schema oneOf 双 profile；title 由 normalization 派生
- file: `ai_context/conventions.md` Cross-File Alignment 表 — 加一行
  `structure_mode ↔ chapter_index profile ↔ source/works manifest`
- file: `docs/architecture/schema_reference.md` — 同步 chapter_index +
  work_manifest 改动
- file: `docs/requirements.md` — phase 0/1 双模式相关节同步（如有）

## 验证标准

- [ ] jsonschema：既有 fixture chapter_index 通过 monolithic profile
  （混入 `volume_id` 时明确报错）
- [ ] jsonschema：新 fixture（light_novel）chapter_index 通过 light_novel
  profile；缺 `volume_seq` / `original_chapter_seq` / `original_sub_chapter_seq`
  任一时明确报错
- [ ] `automation/ingestion/validator.py` 跨文件断言：source manifest
  `structure_mode=monolithic` 与 chapter_index items 不含 volume_id 一致；
  source manifest `structure_mode=light_novel` 与 chapter_index items 必填
  4 字段一致；不一致时 fail
- [ ] `manifests.py::write_works_manifest` smoke：拷 `structure_mode` 进
  works manifest，且与 source 一致
- [ ] orchestrator phase 0 / phase 1 import 无报错（dry-run，不跑 LLM）
- [ ] grep 残留：`volume_chapter_seq` 在所有 schemas / code / prompt /
  docs / ai_context 全库残留 = 0（重命名为 `original_sub_chapter_seq`）
- [ ] grep 残留：仓内不出现真实书名 / 角色名（按
  skills_config.md `## Sensitive content placeholder rules`）
- [ ] Cross-File Alignment 表新条目落地，且与本次 schema / code 改动
  字段名一致

## 执行偏差

1. **手动 plan 列表里只点名 chapter_index + work_manifest 两份 schema，
   实际还需要更新 `schemas/work/works_manifest.schema.json` 与
   `schemas/analysis/stage_plan.schema.json`。**

   - works_manifest（canon 端）需要 `structure_mode` 字段，因为
     `manifests.write_works_manifest` 要写入它而 schema
     `additionalProperties: false`，不开放则程序化产出会失败 schema
     校验。
   - stage_plan 需要：
     a. `chapter_count.minimum: 5 → 1`（light_novel 1:1 派生天然 = 1，
        schema 5-15 会硬挡）；monolithic 5-15 仍由
        `_check_stage_plan_limits` 在代码层强制
     b. `stages.maxItems: 200 → 1000`（light_novel 多卷可达数百
        sub-section）
     c. `stage_title.maxLength: 14 → 50`（light_novel title 由
        `f"{volume_title or '第N卷'} {original_chapter_title or '第M章'}
        {original_sub_chapter_seq}"` 派生；保 50 留余量避免长卷名 ×
        长印刷章名时触顶 → 无穷重试 → FATAL）

2. **plan 写 `chapters = f"{volume_id}-{original_chapter_seq:02d}-
   {original_sub_chapter_seq:02d}"`（例 `V001-02-03`）—— review 阶段
   risk-track 发现该格式破坏 phase 2/3/4 既有 4 个 `chapters` 字段
   消费者（`prompt_builder._parse_chapter_range`、`scene_archive`、
   `repair_agent.context_retriever`、`post_processing._parse_chapter_scope`）
   ——它们都按 `^C[0-9]{4}-C[0-9]{4}$` 解析。`V###-##-##` 在 phase 1.5+
   会硬崩溃 / 静默返回空 / 写入垃圾 chapter_scope。**
   - 修正：light_novel 模式 `chapters = f"{chapter_id}-{chapter_id}"`
     即 degenerate 单章区间（例 `C0001-C0001`），与 monolithic 共享同
     一 `^C[0-9]{4}-C[0-9]{4}$` 模式。phase 2/3/4 消费者零分叉、零修改。
   - 卷 / 印刷章语义不丢：由 `chapter_index` profile-B 字段（volume_id
     / volume_seq / original_chapter_seq / original_sub_chapter_seq /
     volume_title / original_chapter_title）承载，并通过规范化派生的
     `title` 在 `stage_title` 中显式呈现。
   - stage_plan schema 同步收回：`chapters.pattern` 从 alternation
     `^(C[0-9]{4}-C[0-9]{4}|V[0-9]{3}-[0-9]{2}-[0-9]{2})$` 还原为
     `^C[0-9]{4}-C[0-9]{4}$` 单分支。
   - 决策依据：plan 写"phase 2+ 不分叉，统一消费 stage_plan"。要兑现
     这条承诺，唯一路径是 stage_plan.chapters 在两种 mode 下都用
     `C####-C####` 形态。`V###-##-##` 是显示用语义，不能掺进 phase 2/3/4
     的代码契约里。

<!-- POST 阶段填写 -->

## 已落地变更

Schema（4 文件）：

- `schemas/work/chapter_index.schema.json` — items 改 `oneOf` 双 profile：
  monolithic（`additionalProperties: false`，禁 `volume_id` /
  `volume_title` / `volume_seq` / `original_chapter_seq` /
  `original_sub_chapter_seq` / `original_chapter_title` 共 6 字段）；
  light_novel（required 三层 seq + `volume_id`，optional `volume_title`
  + `original_chapter_title`）；title 始终 required minLength 1
- `schemas/work/work_manifest.schema.json` — 加 `structure_mode` enum，
  default `monolithic`
- `schemas/work/works_manifest.schema.json` — 加 `structure_mode` enum
  （由 `manifests.write_works_manifest` 从 source 拷贝）
- `schemas/analysis/stage_plan.schema.json` — `chapter_count.minimum`
  5→1、`stages.maxItems` 200→1000、`stage_title.maxLength` 14→50；
  `chapters.pattern` 保持 `^C[0-9]{4}-C[0-9]{4}$` 单分支不变（光light_novel
  走 degenerate 单章区间）

Code（3 文件）：

- `automation/ingestion/validator.py` — `validate_source_package` 加跨
  文件断言：`structure_mode == "monolithic"` 时 chapter_index 不能含 6
  个 light_novel 字段；`structure_mode == "light_novel"` 时必含 4 个
  required 字段
- `automation/persona_extraction/manifests.py` — `write_works_manifest`
  写入 `structure_mode`（从 source manifest 拷贝，default `monolithic`）；
  新增 `read_structure_mode(project_root, work_id)` 工具函数（works
  manifest 优先，fallback 到 source manifest，最后 default monolithic）
- `automation/persona_extraction/orchestrator.py` — 加 module-level
  `_write_json` helper；新增 `ExtractionOrchestrator._build_light_novel_stage_plan`
  方法（1:1 派生 stage，`chapters = f"{chapter_id}-{chapter_id}"`，
  `stage_title = chapter_index[i].title`）；`run_summarization` Phase 0
  入口分支（light_novel 1 chapter = 1 chunk）；`run_analysis` Phase 1
  入口分支（light_novel 在 LLM call 后 / schema gate 前覆写 stage_plan，
  并跳过 `_check_stage_plan_limits` STAGE_MIN/MAX 校验）；
  `from .manifests import` 加入 `read_structure_mode`

Prompt（1 文件）：

- `prompts/ingestion/原始资料规范化.md` — 加 `structure_mode` 字段填写
  指引（含双模式判定要点）；chapter_index 段加 light_novel profile 三层
  seq 必填字段说明 + title 派生公式 + 例子；交付前自检段提及 validator
  跨文件断言

ai_context（3 文件）：

- `ai_context/architecture.md` — Phase 0 / Phase 1 段加双模式调度说明
- `ai_context/decisions.md` — 加 27j（structure_mode 调度）/ 27k
  （chapter_index oneOf 双 profile）/ 27l（title 派生公式）；
  10a 同步反映 oneOf profile 切分 + chapters 两模式共享 `C####-C####` 格式
- `ai_context/conventions.md` Cross-File Alignment 表加 `structure_mode`
  行（含 schemas/work/chapter_index + schemas/work/work_manifest +
  schemas/work/works_manifest + schemas/analysis/stage_plan + 4 个
  Python 文件 + prompt + docs + ai_context 全链路）

docs（3 文件）：

- `docs/architecture/schema_reference.md` — `work/work_manifest`、
  `work/works_manifest`、`work/chapter_index`、`analysis/stage_plan`
  四节同步双模式描述
- `docs/architecture/extraction_workflow.md` — § 1 入库段、§ 2 Phase 0、
  § 3 Phase 1 加双模式调度说明；§ 3 出口验证段更正"schema 同义 5-15"为
  schema chapter_count.minimum=1 + 代码层 5-15
- `docs/requirements.md` — § 8.4 manifest 字段加 `structure_mode`
  enum 说明；§ 9.2 Phase 0 / Phase 1 流程加双模式描述

todo_list（2 文件）：

- `docs/todo_list.md` — T-INGEST-STRUCTURE-MODE 从 Next 移到 In Progress；
  index 段 In Progress 计数 2→3、Next 计数 3→2、Total 仍 13；本体加
  开始时间 / 当前状态字段；改动清单总结全 schema/code/prompt/ai_context/docs
  落点 + smoke 结果 + 待跑 runtime 验证
- `docs/todo_list_archived.md` — 暂未追加（runtime 验证未跑，遵循
  T-BASELINE-DEPRECATE / T-PHASE2-TARGET-BASELINE 的 in-progress
  pattern：代码完成、runtime 验证待跑期间不归档）

## 与计划的差异

- **plan 不全**（执行偏差 #1）：plan schema 列表只点了 chapter_index +
  work_manifest 两份，实际另需 works_manifest（写入端 schema 必须开放
  `structure_mode` 字段）+ stage_plan（`chapter_count.minimum` /
  `stages.maxItems` / `stage_title.maxLength` 三处放宽）
- **plan 选错 chapters 格式**（执行偏差 #2）：plan 写 light_novel
  `chapters = V001-02-03`，risk-track review 发现 phase 2/3/4 共 4 个
  消费者按 `^C[0-9]{4}-C[0-9]{4}$` 解析，新格式会硬崩溃 / 静默返回空 /
  写入垃圾。修正为 light_novel 用 `C####-C####` degenerate 单章区间，
  让 phase 2/3/4 零分叉。stage_plan schema 同步收回 `chapters.pattern`
  alternation。

## 验证结果

- [x] jsonschema：monolithic chapter_index 通过 monolithic profile；混入
  `volume_id` 时明确报错（smoke test 1+2）
- [x] jsonschema：light_novel chapter_index 通过 light_novel profile；
  缺 `volume_seq` 时明确报错（smoke test 3+4）
- [x] `automation/ingestion/validator.py` 跨文件断言通过：monolithic +
  含 volume_id → 报错；light_novel + 缺 volume_seq → 报错（smoke test
  6+8）；正常路径双 profile 都通过（5+7）
- [x] `manifests.py` smoke：`write_works_manifest` 拷 `structure_mode`、
  `read_structure_mode` works > source > default monolithic 链路工作；
  works_manifest 写出后通过 schema（重测 5）
- [x] orchestrator 一应 import 无报错；`_build_light_novel_stage_plan`
  从 12-sub-section 假数据派生的 stage_plan 通过 schema；
  `prompt_builder._parse_chapter_range` 解析 `C0001-C0001` 返回 `(1, 1)`
  确认 phase 2/3/4 消费者零破坏（重测 1+2+3）
- [x] grep 残留 `volume_chapter_seq`：仅在 `logs/change_logs/` +
  `docs/todo_list_archived.md` 出现（豁免目录），全库 0 漂移
- [x] grep 残留 `V###-##-##` / `V001-02-03`：除 PRE log（本文件，记录
  执行偏差 #2 的设计转向）外无其他出现
- [x] 真实书 / 角色名 grep：除 PRE log（执行偏差 #2 上下文）+
  `docs/todo_list_archived.md` + `logs/change_logs/`（豁免）外，全库 0
- [x] Cross-File Alignment 表新条目落地，含 4 schema + 3 code + 1 prompt
  + 3 docs + 2 ai_context，全链路覆盖

待跑（runtime gate，超出本次代码改动范围）：

- [ ] 拿一份完整规范化的多卷 light_novel fixture 跑一遍 phase 0 +
  phase 1：phase 0 chunk 数 == chapter_index 长度；phase 1 stage 数
  == chapter_index 长度；stage_plan 顺序 / stage_id / stage_title 正确
- [ ] monolithic 既有 fixture dry-run 一遍 phase 0/1，与历史结果一致
  ——确认默认路径不退化

## Completed

- **Status**: DONE
- **Finished**: 2026-05-01 07:47:40 EDT
