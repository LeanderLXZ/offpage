# post_check_followup_ingest_structure_mode

- **Started**: 2026-05-01 09:09:52 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

前一轮 `/post-check` 复审 `T-INGEST-STRUCTURE-MODE` 给出 REVIEWED-PARTIAL，
3 类残留缺口（详见 `logs/change_logs/2026-05-01_070414_phase01_ingest_structure_mode.md`
§ 复查结论）。用户：「按照你的推荐进行修复 /go」。本轮专注修这些缺口。

## 结论与决策

**修复范围**（由 /post-check 推荐项确定）：

1. **[H] `stage_title.maxLength=50` 对抗输入仍可超长 → FATAL 无穷重试家族
   风险**：50 字符上限在长 CJK / 英文轻小说卷-章组合下可被超过（实测
   `"Side colors special edition 2024 The story of merchant and his
   apprentice 1"` = 75 字符）。同 PRE 偏差 #1 家族，14→50 经验上仍不足。
   **修法（双管齐下，防御性深度 2）**：
   - schema 端：`schemas/analysis/stage_plan.schema.json::stage_title.maxLength`
     50 → 80（覆盖典型最坏 CJK 组合 ~60-70 字符 + 余量）
   - 代码端：`_build_light_novel_stage_plan` 派生 `stage_title` 时按 80 字符
     软截断 + 中文省略号 `…`，超过则截到 79 字符 + `…`（80 字符总长）。
     用 schema 上限 - 1 = 79 留 1 字符给省略号。
     这样即使 normalization 阶段写出 100 字符的 title，代码层在 `_build_…`
     这一步就能保证产出 ≤80 字符 → schema gate 必过 → 不会触发无穷重试

2. **[M·pre-existing] `progress.py::_expected_chapter_count` 对 `C####` 前缀
   静默失败**：T-CHAPTER-ID-UNIFY 期 chapters 字段从 `0001-0025` 改成
   `C0001-C0025` 后，`int("C0001")` 抛 ValueError 被 try/except 捕获返回
   `None`，使 reconcile_with_disk 的"len(summaries) == 章节数"深度校验对
   所有 done chunk 静默跳过。light_novel N=1 chunk 模式扩大暴露面。
   **修法**：解析逻辑对齐 `prompt_builder._parse_chapter_range` 的
   `int(parts[i].lstrip("C"))` 写法（兼容 `C####-C####` 与历史 `####-####`
   两种形式，仍允许失败 fallback）

3. **[L] cosmetic 项**：
   a. `docs/todo_list.md:15` Index Title 大小写漂移："phase 0/1" → "Phase 0/1"
      与 body header 对齐
   b. `automation/README.md:360+` Phase 0/1 schema-gate 段加一行指针式 link
      到 `docs/architecture/extraction_workflow.md` 的 dual-mode 段落
   c. 其余 cosmetic（commit message 隐式覆盖 / Cross-File Alignment 自引用 /
      orchestrator `_load_json` 类型注解）属于格式 / 类型注解级别，**不修**
      （非破坏性、修了纯噪声）

## 计划动作清单

Schema：

- file: `schemas/analysis/stage_plan.schema.json` →
  `stage_title.maxLength` 50 → 80；description 同步更新（提及代码层软截断）

Code：

- file: `automation/persona_extraction/orchestrator.py::_build_light_novel_stage_plan`
  → `stage_title` 派生加 80 字符软截断 + `…`；与 schema 80 上限对齐
- file: `automation/persona_extraction/progress.py::_expected_chapter_count`
  → `int(part.lstrip("C"))` 兼容 `C####-C####` 与 `####-####`；保留
  ValueError fallback

Docs：

- file: `docs/todo_list.md:15` → Index Title "phase 0/1" → "Phase 0/1"
- file: `automation/README.md` → Phase 0/1 段加 dual-mode 指针 link

ai_context：

- file: `ai_context/decisions.md::§27l`（title 派生）→ 加一句"代码层软截断
  到 schema 上限"
- file: `ai_context/conventions.md` Cross-File Alignment 行 → 加
  `automation/persona_extraction/progress.py`（reconcile chapter-count 解析
  与 stage_plan.chapters 格式同步）

## 验证标准

- [ ] schema 校验：`stage_plan.schema.json` 通过 jsonschema validator self-check；
  `stage_title.maxLength=80` 字段值正确
- [ ] code smoke：`_build_light_novel_stage_plan` 输入对抗性长 title（>80 字符）
  时输出 ≤80 字符且以 `…` 结尾；正常短 title 不变
- [ ] code smoke：`_expected_chapter_count` 解析 `C0001-C0025` 返回 25、
  解析 `C0001-C0001` 返回 1、解析 `0001-0025`（历史格式）仍返回 25、
  解析非法格式（如 `abc`）返回 None
- [ ] 所有 schema 通过 jsonschema validator
- [ ] orchestrator / manifests / validator / progress 4 模块 import 无报错
- [ ] grep 残留：本次 diff 不引入"legacy / 旧 / 已废弃 / 原为"措辞、
  不引入真实书 / 角色名

## 执行偏差

无。

<!-- POST 阶段填写 -->

## 已落地变更

Schema（1 文件）：

- `schemas/analysis/stage_plan.schema.json::stage_title.maxLength` 50 → 80；
  description 同步说明代码层软截断兜底

Code（2 文件）：

- `automation/persona_extraction/orchestrator.py::ExtractionOrchestrator`
  新增类常量 `_STAGE_TITLE_MAX = 80`（与 schema 单源对齐）；
  `_build_light_novel_stage_plan` 派生 stage 时 `if len(title) > _STAGE_TITLE_MAX:
  title = title[:_STAGE_TITLE_MAX - 1] + "…"` 软截断
- `automation/persona_extraction/progress.py::Phase0Progress._expected_chapter_count`
  解析逻辑改 `int(part.lstrip("C"))`，对齐 `prompt_builder._parse_chapter_range`，
  兼容 `C####-C####`（当前）+ `####-####`（历史）；保留 `(ValueError,
  AttributeError)` fallback

Docs（2 文件）：

- `docs/todo_list.md` Index Title "phase 0/1" → "Phase 0/1"（与 body
  header L415 对齐）；In Progress 当前状态字段同步描述本轮残留修
- `automation/README.md` 在 Phase 0 JSON 修复段前新增"Phase 0 / Phase 1
  双模式调度"小节，指针到 `docs/architecture/extraction_workflow.md` §1-3
  + `ai_context/decisions.md` §27j/27k/27l

ai_context（2 文件）：

- `ai_context/decisions.md::§27l` 加最后一段 "Code-side soft-truncation
  safeguard"，描述 `_build_light_novel_stage_plan` 兜底逻辑；引用列表
  追加 `schemas/analysis/stage_plan.schema.json` + `automation/persona_extraction/
  orchestrator.py::_build_light_novel_stage_plan`
- `ai_context/conventions.md` Cross-File Alignment 表 `structure_mode`
  行追加 `automation/persona_extraction/progress.py::_expected_chapter_count`
  （reconcile 解析与 stage_plan.chapters 格式同步）

## 与计划的差异

无。3 类修复（schema bump + 代码软截断兜底；progress.py C 前缀兼容；
cosmetic 2 项）按 PRE 计划清单逐条落地。

## 验证结果

- [x] schema 校验：所有 schema 通过 `jsonschema.check_schema`；
  `stage_plan.schema.json::stage_title.maxLength == 80` 验证通过（smoke 1）
- [x] code smoke：对抗性 103 字符 title → 输出 80 字符且以 `…` 结尾
  （smoke 2）；正常短 title `"短标题"` 不截断（smoke 2）；派生 plan 仍
  通过 stage_plan schema（smoke 3）
- [x] code smoke：`_expected_chapter_count` 各形式解析——
  `C0001-C0025=25` / `C0001-C0001=1`（light_novel）/ `0001-0025=25`（历史）/
  `"invalid"=None` / `"C0001"=None`（缺连字符 fallback）（smoke 4）
- [x] 4 模块 import 无报错：`validator` / `manifests` / `orchestrator` /
  `progress`（smoke 5 + 既有 import 链）
- [x] grep 残留：本次 diff 不引入"legacy / 旧 / 已废弃 / 原为 / renamed
  from"措辞（grep 0）；不引入真实书 / 角色名（grep 0）

## Completed

- **Status**: DONE
- **Finished**: 2026-05-01 09:46:16 EDT

<!-- /post-check 填写 -->

## 复查结论（对话里有完整报告）

### 轨 1 — 需求落实
- 落实率：5/5 计划项 + 6/6 验证标准
- Missed updates: 0 条

### 轨 2 — 影响扩散
- Findings: High=0 / Medium=1 / Low=2
- Open Questions: 0 条
- 关键 Medium：`automation/persona_extraction/orchestrator.py:937 _STAGE_TITLE_MAX = 80`
  硬编码 schema bound，违反 `ai_context/decisions.md` §27b（"Bounds-only-in-schema"）
  / `ai_context/conventions.md` L118（"no duplicates anywhere else"）。§27b 仅
  grandfather 一条 `StructuralChecker.relationship_history_summary_max_chars`
  程序 fallback；本次新加的 `_STAGE_TITLE_MAX` 是第二条未登记的 fallback。
  风险：schema 端 80 改动后，代码端不会自动同步，可能复发本次试图根除的
  无穷重试家族风险（schema 收紧时）或失去截断意图（schema 放宽时）

## 复查时状态
- **Reviewed**: 2026-05-01 10:05:38 EDT
- **Status**: REVIEWED-PARTIAL
  - 轨 1 全落实 → PASS
  - 轨 2 有 1 Medium（§27b duplicate）→ 不达 PASS
  - 不到 FAIL（无 High；轨 1 无大面积缺口）
- **Conversation ref**: 同会话内 /post-check 输出
