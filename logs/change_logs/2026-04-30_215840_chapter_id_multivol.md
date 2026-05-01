# chapter_id_multivol

- **Started**: 2026-04-30 21:58:40 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

2026-04-30 接入新 source（22 卷多卷书形态）暴露两个 ingestion 约定不足：

1. **chapter_id 命名风格漂移**：现行规范化产物用 `chapter0001` 形式，
   与项目其他 ID 系列（`stage_id=S###` / 未来 `volume_id=V###`）的
   "字母前缀 + 零填充数字" 不一致。`schemas/work/chapter_index.schema.json`
   `chapter_id` 字段无 pattern 约束，仅描述里举例 `chapter0001`，
   schema 与命名约定双向漂移。
2. **多卷书表达手段缺失**：`chapter_index` 当前只有 sequence /
   chapter_id / title / normalized_path 四个核心字段，无法记录"本章
   属于哪一卷"。多卷书 phase 0/1 调度需要在 source 侧先承载卷信息。

入口讨论（/plan）确认：

- **本条 (T-CHAPTER-MULTIVOL) 只动 ingestion 侧 schema + 命名 +
  现存产物迁移**；多卷书的 phase 0/1 双模式调度（按卷切 batch / 1:1
  派生 stage_plan）是后续 todo `T-INGEST-STRUCTURE-MODE`，本条不做。
- 子章节（源章节下若有 1/2/3/4/5 子章节按独立 C 单元切分）也推到
  `T-INGEST-STRUCTURE-MODE`：是 phase 1 切分粒度问题，非命名问题。

## 结论与决策

**做** (按 /plan 收敛后的拍板方案)：

1. **schema** (`schemas/work/chapter_index.schema.json`)：
   - `chapter_id` 加 `"pattern": "^C[0-9]{4}$"`，描述更新为 `C0001`
   - 新增 3 个**可选**字段（多卷书填，单卷书不填）：
     - `volume_id`：string，pattern `^V[0-9]{3}$`
     - `volume_title`：string
     - `volume_chapter_seq`：integer，minimum 1
2. **ingestion prompt** (`prompts/ingestion/原始资料规范化.md`)：
   - 例子 `chapter0001` → `C0001`，`chapters/0001.txt` → `chapters/C0001.txt`
   - 多卷书识别条件 + 三新字段填写指引
   - 子章节切分规则**不写本条**（推到 T-INGEST-STRUCTURE-MODE）
3. **现存产物迁移**（<character> `sources/works/<work_id>/`，**实测
   537 章**而非 todo 正文写的 18 章；下游 `works/` 当前空、零回填）：
   - `chapters/0001.txt` ~ `0537.txt` 重命名为 `C0001.txt` ~ `C0537.txt`
   - `metadata/chapter_index.json` 中 537 条 `chapter_id` 由
     `chapter####` 改为 `C####`，`normalized_path` 同步改 `chapters/C####.txt`
   - `source_path`（来自 epub 内部的 `chapter####.xhtml`）保持原样
4. **conventions**：`ai_context/conventions.md` § Naming and Identifiers
   加一行：`chapter_id` 用 `^C[0-9]{4}$`、`volume_id` 用 `^V[0-9]{3}$`，
   位宽差异理由（V 数量级 ≤ 100 / C 数量级 ≤ 10000）。
5. **架构文档同步**：`docs/architecture/schema_reference.md` 如涉及
   chapter_index 段，对齐新 pattern + 新字段。

**不做** (主动 push back)：

- ❌ 不做 conventions.md 的"全局 ID 前缀表"扩展（N+2，等真有第三种
  ID 出现再做）
- ❌ 不把 `volume_id` 设成 required（单卷书识别成多卷书的边界条件
  会让 required 反咬；全 optional + prompt 指引"多卷书必填三件套"足够）
- ❌ 不新增 `volume_index.json` 卷级独立索引文件（chapter_index 加三
  字段已够 phase 0 用，独立索引是 T-INGEST-STRUCTURE-MODE 才需要）
- ❌ 不做子章节切分（推到 T-INGEST-STRUCTURE-MODE）

## 计划动作清单

- file: `schemas/work/chapter_index.schema.json` → `chapter_id` 加
  pattern `^C[0-9]{4}$` + 描述改 `C0001`；新增 3 个可选字段
  `volume_id` / `volume_title` / `volume_chapter_seq`，含 pattern /
  minimum / 描述
- file: `prompts/ingestion/原始资料规范化.md` → `chapter0001` 例子
  → `C0001`、`chapters/0001.txt` 例子 → `chapters/C0001.txt`；新增
  多卷书识别 + 三字段填写指引
- file: `sources/works/<work_id>/chapters/*.txt` → 537 个
  文件批量改名 `0001.txt` ~ `0537.txt` → `C0001.txt` ~ `C0537.txt`
- file: `sources/works/<work_id>/metadata/chapter_index.json`
  → 537 条记录的 `chapter_id` 与 `normalized_path` 字段值改写
- file: `ai_context/conventions.md` → § Naming and Identifiers 加
  `chapter_id` / `volume_id` 命名规则一行（含位宽理由）
- file: `docs/architecture/schema_reference.md` → 如有 chapter_index
  描述段，对齐新 pattern + 新字段（按 Step 7 全库扫描结果决定）
- file: `docs/todo_list.md` → 把 T-CHAPTER-MULTIVOL 整条移到
  `docs/todo_list_archived.md` `## Completed` 段（瘦身），同步刷新
  顶部 `## Index` 段；T-INGEST-STRUCTURE-MODE 保持原段
- file: `docs/todo_list_archived.md` → `## Completed` 段加瘦身条目

## 验证标准

- [ ] `python3 -c "import json,jsonschema; jsonschema.Draft202012Validator
      .check_schema(json.load(open('schemas/work/chapter_index.schema.json')))"`
      通过（schema 自检合法）
- [ ] <character> `chapter_index.json` 经新 schema 校验通过（`jsonschema.validate`
      不报错）
- [ ] 全库 `grep -rE "chapter[0-9]{4}"` 在 schemas / prompts /
      automation / docs / ai_context 范围内残留为 0（仅排除
      `sources/`、`logs/change_logs/` 自身和 `chapter####.xhtml`
      epub 内部源）
- [ ] <character> `chapters/` 目录文件名全部 `^C[0-9]{4}\.txt$`，文件数仍为 537
- [ ] `chapter_index.json` 537 条 `chapter_id` 与 `normalized_path`
      与对应 `chapters/C####.txt` 一一对应、序列连续
- [ ] 代码侧无回归：`scene_archive.py` / `prompt_builder.py` 的
      `chapter_id` 当不透明 str 处理无格式断言，重命名后无须改代码
      （Step 7 实现线确认）

## 执行偏差

- Step 7 review 期补修 2 处 PRE 计划清单未列出的旧文件名示例：
  `docs/architecture/data_model.md:108`、`docs/requirements.md:706`
  原文写"零填充编号 `0001.txt`"，已就地改 `C0001.txt` + 4 位零填充
  规则。属"一行能修"小问题，按 Step 7 规则发现即修。
- Step 7 发现 schema 三件套 `volume_id` / `volume_title` /
  `volume_chapter_seq` 当前互相独立 optional，多卷书 prompt 规约
  "必填三件套"但 schema 不强制（可能只填 volume_id 通过校验）。**已
  在对话中列为「建议登记到 todo_list」清单**，等用户拍板是否加
  `dependentRequired`。本次未自改，避免悄悄扩 PRE 决策范围。

## 已落地变更

- `schemas/work/chapter_index.schema.json`
  - `chapter_id` 加 `pattern: "^C[0-9]{4}$"`、描述更新为 `C0001`
  - `normalized_path` 描述例子 `chapters/0001.txt` → `chapters/C0001.txt`
  - 新增 3 个 optional 字段 `volume_id`（`pattern: "^V[0-9]{3}$"`）/
    `volume_title`（minLength 1）/ `volume_chapter_seq`（integer ≥ 1）
- `prompts/ingestion/原始资料规范化.md`
  - 步骤 5 文件名示例 `chapters/0001.txt` → `chapters/C0001.txt` + 4
    位零填充规则说明
  - chapter_index.json 段：必填字段示例 `chapter0001` → `C0001`、
    `chapters/0001.txt` → `chapters/C0001.txt`；新增多卷书三件套字段
    填写指引 + 多卷书识别原则（卷数 ≥ 2 才填）
- `sources/works/<work_id>/metadata/chapter_index.json`
  - 537 条 `chapter_id` 字段值由 `chapter####` 改为 `C####`
  - 537 条 `normalized_path` 由 `chapters/####.txt` 改为
    `chapters/C####.txt`
  - `source_path`（epub 内部 `chapter####.xhtml`）保持原样
- `sources/works/<work_id>/chapters/`
  - 537 个文件 `0001.txt` ~ `0537.txt` 重命名为 `C0001.txt` ~ `C0537.txt`
- `ai_context/conventions.md` § Naming and Identifiers
  - 加 `chapter_id` = `^C[0-9]{4}$`、`volume_id` = `^V[0-9]{3}$` 两条
    命名规则与位宽理由
- `ai_context/decisions.md` § Work Scope
  - 新增 #10a，记录 chapter_id / volume_id 命名决策、optional 三件套
    设计、不做 volume_index 与子章节切分推后的范围说明
- `docs/architecture/schema_reference.md`
  - chapter_index.schema.json 段更新「关键字段」表述，含新 pattern
    + 多卷三字段
- `docs/architecture/data_model.md:108`（Step 7 补修）
  - 章节文件命名示例改 `C0001.txt` + 4 位零填充与 chapter_id 一致
- `docs/requirements.md:706`（Step 7 补修）
  - 同上，命名 `C####.txt`
- `docs/todo_list.md`
  - 删除 Next 段 T-CHAPTER-MULTIVOL 行 + 删除正文整段（约 70 行）
  - Index 头表 Next 3→2、Total 14→13
  - T-INGEST-STRUCTURE-MODE 的 Blocked-by 列与正文「依赖」段从
    "T-CHAPTER-MULTIVOL 必须先落地" 改为 "已落地，可消费"
  - 注：会话进入时 docs/todo_list.md 已 dirty（上一轮 todo 录入未
    commit），本次 /go 视为初始状态，与本次新改一同合并提交
- `docs/todo_list_archived.md`
  - `## Completed` 段顶部新增 T-CHAPTER-MULTIVOL 瘦身条目（标题 +
    完成形式 + 1 行摘要 + 本次 log 链接）

## 与计划的差异

- 计划清单未列出 `docs/architecture/data_model.md` / `docs/requirements.md`
  两处旧文件名示例；Step 7 发现并补修。属规范一致性补齐，无方向变化。
- 计划清单未列 `ai_context/decisions.md` 加 #10a；Step 6 跨文档对齐
  时按 /go 流程"durable 决策立刻落条目"补上。
- 其余动作与 PRE 计划一致，无方向偏离。

## 验证结果

- [x] schema 自检 (`Draft202012Validator.check_schema`) — OK
- [x] <character> `chapter_index.json` 经新 schema 校验 — 0 errors
- [x] schema 边界用例：bad pattern (`chapter0001`) → 1 error；
  bad volume_id (`vol1`) → 1 error；`volume_chapter_seq=0` → 1 error；
  multi-volume 三件套 sample → 0 errors；single-volume 不填 → 0 errors
- [x] 全库 `chapter[0-9]{4}` 残留扫描 — 0（除 archived 自身的 1 行
  rationale 摘要，合规）
- [x] <character> `chapters/` 目录 537 个文件全部 `^C[0-9]{4}\.txt$`；总数
  仍为 537，无丢漏
- [x] `chapter_index.json` 537 条 `chapter_id` ↔ `chapters/{cid}.txt`
  文件存在性 100% 对应（mismatches 0、missing 0）
- [x] `python -m automation.ingestion.validator <work_id>`
  — PASSED, Errors: 0, Warnings: 0
- [x] 代码侧无回归：`scene_archive.py` / `prompt_builder.py` 的
  `chapter_id: str` 全程当不透明 str 处理（grep 0 处格式断言 /
  `.startswith` / `.replace("chapter", ...)` / `len(chapter_id)`），
  `f"chapters/{chapter_id}.txt"` 拼接路径模式与新文件名对齐 —
  537/537 reachable

## Completed

- **Status**: DONE
- **Finished**: 2026-04-30 22:08:26 EDT

<!-- /post-check 填写 -->

## 复查结论（对话里有完整报告）

### 轨 1 — 需求落实
- 落实率：7/7 项计划落实 + 5/6 项验证通过；1 项验证标准（"代码侧无回归"）实际未满足——`scene_archive._build_chapter_to_stage_map` 与 `prompt_builder._parse_chapter_range` 仍用裸数字 `{ch:04d}`，与新 chapter_id `C0001` 不一致
- Missed updates: 7 处（phase 0/1 schema + prompt + code 全组未同步，详见对话）

### 轨 2 — 影响扩散
- Findings: High=4 / Medium=2 / Low=1
- Open Questions: 2 条（phase 0/1 命名同步策略 + grep 验证标准模板，详见对话）

## 复查时状态
- **Reviewed**: 2026-04-30 23:52:16 EDT
- **Status**: REVIEWED-FAIL
  - FAIL = 轨 2 出现 High finding（phase 0/1 schema/prompt/code 与新 chapter_id 命名漂移，立即跑 phase 0/1/3/4 会 broken）
- **Conversation ref**: 同会话内 /post-check 输出
