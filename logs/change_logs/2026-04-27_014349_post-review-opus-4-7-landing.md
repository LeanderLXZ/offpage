# post-review-opus-4-7-landing

- **Started**: 2026-04-27 01:43:49 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

`/check-review claude` 复核了 `logs/review_reports/2026-04-27_004333_opus-4-7_full-repo-audit.md`（opus-4-7 full repo audit）。用户逐条确认方案后调用 `/go` 落地。

源报告 9 条 finding（H-1/H-2/H-3 + M-1/M-2/M-3 + L-1/L-2/L-3），复核结论：

- H-1/H-2/H-3/M-1/M-3/L-1 真实，本轮处理
- M-2 (`works/_template/`) 经讨论驳回 —— `works/` 产物由 LLM 按 schema 生成 + orchestrator 程序 mkdir，不存在"等待人工填充"的状态，与 `users/_template/` 的填充模式根本不对称
- L-2 已失效（schema_reference.md 已有"Python dataclass，非 JSON Schema"专门段）
- L-3 推迟（精度优化，非阻塞主线；登记新 todo）

## 结论与决策

### H-1 — stage_title 单源化

`stage_plan.schema.json` 是 stage_title 唯一权威源（保留 `maxLength: 14`）；其他 4 份 schema 只是从 stage_plan 拉取，删除各自的 `minLength` / `maxLength`，描述改为指针式说明。

涉及：
- `schemas/analysis/stage_plan.schema.json`（保留 bound，澄清描述）
- `schemas/character/stage_snapshot.schema.json`（删 bound，描述指向 stage_plan）
- `schemas/world/world_stage_snapshot.schema.json`（同）
- `schemas/character/stage_catalog.schema.json`（同）
- `schemas/world/world_stage_catalog.schema.json`（同）

### H-2 — squash dispose 交互

squash-merge 完成后追加交互：`Delete extraction/{branch} and run git gc --prune=now? [y/N]`。**默认 N**，用户输入 `y` 才执行 `git branch -D` + `git gc --prune=now`。**不引入 auto 路径**（即使 `auto_squash_merge=true` 也不自动 dispose；分支删除不可逆，必须每次交互确认）。打印兜底提示中的 `-d` → `-D`。

涉及：
- `automation/persona_extraction/orchestrator.py:_offer_squash_merge`（追加 dispose 交互）
- `ai_context/decisions.md` #26（措辞改"交互 offer"，不再说"自动"）
- `ai_context/architecture.md` §Git Branch Model（同）
- `ai_context/conventions.md` §Git（同）
- `docs/architecture/extraction_workflow.md`（如有相关段）
- `docs/todo_list.md` —— 删除 `T-EXTRACTION-BRANCH-DISPOSE` 条目

### H-3 — Phase 3.5 检查数对齐

代码实际跑 9 个 `_check_*`（`consistency_checker.py:110-121`），文档说 10。本轮不补第 10 项，把文档改成 9。

涉及：
- `ai_context/architecture.md:160`
- `docs/requirements.md:1266`

### M-1 — prompt 表格改肯定句

`automation/prompt_templates/character_snapshot_extraction.md:120-128` "字段命名严格对照（schema 权威）" 表整段改写为肯定形式的"必填项与正确字段名"清单，不再列"错误字段名 → 正确字段名"。

### M-3 — handoff 简化为 todo_list 指针

`ai_context/handoff.md:51-86` 整段（含小标题 `### Extraction-branch artifact drift (resume gate)`）替换为指针式短段，明确指向 `docs/todo_list.md` 的「立即执行」section，并显式负向指令"Do NOT read other sections"防止 token 浪费。

### L-1 — `.gitignore` 重排优化

通读后整理为 6 个语义清晰的 section（extraction artifacts / source corpus / generated retrieval / user data / local databases / local config / tool artifacts）。删死规则（根级 `analysis/evidence/*`），合并 `.claude/scheduled_tasks.lock` 进 `.claude/*.lock`。**仔细验证不影响现有框架**：
- `users/_template/` 必须仍被豁免
- `sources/works/[!_]*/manifest.json` 模式必须保留（防真实 work_id 进 main）
- `works/*/analysis/evidence/.gitkeep` 必须仍被豁免
- `sources/raw/.gitkeep` 必须仍被豁免

### todo_list 加分组

`docs/todo_list.md` 顶层加二级标题 `## 立即执行` / `## 推迟 / 跟踪`，把现有 `### [T-XXX]` 条目按优先级归类。**这是 M-3 handoff 指向的前置依赖**（handoff 引用「立即执行」section）。

L-3 推迟项作为新条目登记到 `## 推迟 / 跟踪`。

## 计划动作清单

1. **schema 收敛（H-1）**：5 份 schema 文件
   - `schemas/analysis/stage_plan.schema.json` → 保留 maxLength 14，描述改"权威源"措辞
   - `schemas/character/stage_snapshot.schema.json` → 删 minLength/maxLength
   - `schemas/world/world_stage_snapshot.schema.json` → 删 minLength/maxLength
   - `schemas/character/stage_catalog.schema.json` → 描述改"从 stage_plan 拉取"
   - `schemas/world/world_stage_catalog.schema.json` → 同

2. **docs 数量对齐（H-3）**：
   - `ai_context/architecture.md:160` `10 programmatic` → `9 programmatic`
   - `docs/requirements.md:1266` `10 项程序化检查` → `9 项程序化检查`

3. **squash dispose 交互（H-2）**：
   - `automation/persona_extraction/orchestrator.py:_offer_squash_merge` 追加交互段
   - `ai_context/decisions.md` #26 措辞同步
   - `ai_context/architecture.md` §Git Branch Model 同步
   - `ai_context/conventions.md` §Git 同步
   - `docs/architecture/extraction_workflow.md` 检查同步项
   - `docs/todo_list.md` 删 `T-EXTRACTION-BRANCH-DISPOSE` 条目

4. **docs 清理（M-1 + M-3 + L-1）**：
   - `automation/prompt_templates/character_snapshot_extraction.md:120-128`
   - `ai_context/handoff.md:51-86`
   - `.gitignore` 重排
   - `docs/todo_list.md` 加二级分组（M-3 前置依赖）

## 验证标准

- [ ] 5 份 schema 文件 import / 解析无报错（`python -c "import json; json.load(open('schemas/.../X.schema.json'))"`）
- [ ] `automation/persona_extraction/orchestrator.py` `python -m py_compile` 通过
- [ ] `consistency_checker.py` 实际 `_check_*` 数 = `ai_context/architecture.md` + `docs/requirements.md` 中数字
- [ ] grep `relationship_behavior_map` 残留只在 git history / log 文件（不在 ai_context / docs / prompts）
- [ ] grep `analysis/evidence/\*` 仅在 `works/*/...` 形式（无根级）
- [ ] `.gitignore` 仍命中：`users/[非_template]/*`、`works/*/analysis/progress/`、`sources/works/<真实_work_id>/manifest.json`；仍豁免：`users/_template/`、`works/*/analysis/evidence/.gitkeep`、`sources/raw/.gitkeep`
- [ ] `docs/todo_list.md` 顶层有 `## 立即执行` / `## 推迟 / 跟踪` 二级标题；`T-EXTRACTION-BRANCH-DISPOSE` 已删
- [ ] `ai_context/handoff.md` 51-86 段已替换为短指针段
- [ ] `ai_context/architecture.md` + `decisions.md` + `conventions.md` 三处 dispose 措辞一致

## 执行偏差

1. **`automation/persona_extraction/git_utils.py` 新增公共 helper**：原计划在 orchestrator 直接 `subprocess` 或引 `_git`，但 `_git` 是 git_utils 私有符号，跨模块引私有不规范。改为在 git_utils 增加两个公共函数 `delete_branch(project_root, branch)` + `git_gc_prune_now(project_root)`，与既有 `squash_merge_to` / `branch_exists` / `ensure_branch_from_main` 同一抽象层。orchestrator 显式 import 这两个名字。
2. **`automation/README.md:414` 漏改**：Step 6 sub-agent 审计发现该处仍写"10 项程序化检查"，已修正为 9。原 PRE 计划只列了 `ai_context/architecture.md:160` + `docs/requirements.md:1266` 两处。
3. **handoff section 名称对齐**：原计划是新增 `## 立即执行 / ## 推迟 / 跟踪` 二级标题。落地时发现 `docs/todo_list.md` 已有 `## 立即执行` / `## 下一步` / `## 讨论中（未定案）` 三段结构（立即执行原为空）；不再引入新 section 名，改为复用现有结构：把 `T-WORLD-SNAPSHOT-S001-S002-MIGRATE` 从「下一步」迁到「立即执行」（resume gate 主要消费它），handoff 措辞同步指 `## 立即执行` 并显式禁读 `## 下一步` / `## 讨论中` 两段。
4. **`docs/architecture/extraction_workflow.md` + `automation/README.md` dispose 段同步**：原 PRE 列为"如有相关段"作为可选项；实际两处都有 squash 段且需要措辞同步，已落实。
5. **决策日志 `ai_context/decisions.md:27g` 的 `relationship_behavior_map` 历史叙事保留**：M-1 finding 范围限于描述性 docs / prompts；ADR (`decisions.md`) 本身的语义角色就是历史档案，"renamed to" 是其内容职责，不属"history narration"违规对象，本轮不动。

<!-- POST 阶段填写 -->

## 已落地变更

### 1. Schema 收敛（H-1）— stage_title 单源化

- [schemas/analysis/stage_plan.schema.json:47-48](schemas/analysis/stage_plan.schema.json#L47-L48)：保留 `maxLength: 14`，描述改为权威源声明（"本字段是 stage_title 的唯一权威源；下游 schema 从这里按 stage_id 拉取，不重复定义 bound"）
- [schemas/character/stage_snapshot.schema.json:46-49](schemas/character/stage_snapshot.schema.json#L46-L49)：删 `minLength: 1` / `maxLength: 15`，描述改"从 stage_plan.json 同 stage_id 条目拉取"
- [schemas/world/world_stage_snapshot.schema.json:35-38](schemas/world/world_stage_snapshot.schema.json#L35-L38)：同上
- [schemas/character/stage_catalog.schema.json:48-51](schemas/character/stage_catalog.schema.json#L48-L51)：描述改"从 stage_plan.json 拉取"
- [schemas/world/world_stage_catalog.schema.json:43-46](schemas/world/world_stage_catalog.schema.json#L43-L46)：同上

### 2. Phase 3.5 数量对齐（H-3）— 10 → 9

- [ai_context/architecture.md:160](ai_context/architecture.md#L160)：`10 programmatic` → `9 programmatic`
- [docs/requirements.md:1266](docs/requirements.md#L1266)：`10 项程序化检查` → `9 项程序化检查`
- [automation/README.md:414](automation/README.md#L414)：`10 项程序化检查` → `9 项程序化检查`（PRE 漏列、Step 6 audit 补上）

### 3. Squash dispose 交互（H-2）

代码层：
- [automation/persona_extraction/git_utils.py](automation/persona_extraction/git_utils.py)：新增公共函数 `delete_branch` + `git_gc_prune_now`；`squash_merge_to` docstring 同步指向新 helper
- [automation/persona_extraction/orchestrator.py:31-41](automation/persona_extraction/orchestrator.py#L31-L41)：import 新函数
- [automation/persona_extraction/orchestrator.py:_offer_squash_merge](automation/persona_extraction/orchestrator.py#L2110)：squash 成功后追加交互段——`Delete extraction branch '{branch}' and run 'git gc --prune=now'? [y/N]`，**默认 N**；用户输入 `y` 才执行 `delete_branch` + `git_gc_prune_now`，并打印 `[OK]` / `[ERROR]` / `[WARN]` 状态行；用户拒绝则打印手动命令提示（`-D` + gc）

文档层：
- [ai_context/decisions.md:81 (#26)](ai_context/decisions.md#L81)：措辞改为"interactive offers (`[y/N]`, default N)"，明确"即使 `auto_squash_merge=true` 也仍交互询问"
- [ai_context/architecture.md:143](ai_context/architecture.md#L143)：同步
- [ai_context/conventions.md:102](ai_context/conventions.md#L102)：同步
- [docs/architecture/extraction_workflow.md:504-509](docs/architecture/extraction_workflow.md#L504-L509)：同步
- [automation/README.md](automation/README.md)：squash-merge 段落下追加新 bullet "squash 后 dispose（交互）"，描述完整流程
- [docs/todo_list.md](docs/todo_list.md)：删除 `T-EXTRACTION-BRANCH-DISPOSE` 整条

### 4. Prompt 表格改肯定句（M-1）

- [automation/prompt_templates/character_snapshot_extraction.md:120-124](automation/prompt_templates/character_snapshot_extraction.md#L120-L124)："字段命名严格对照（schema 权威）" 表整段改为肯定形式 bullet 清单：`stage_events` 必填、`character_arc` 非首阶段必填、`target_behavior_map` 统一同名（含 `target_type` 内层字段名）。删除原 `错误字段名 → 正确字段名` 表，剥离 history 暗示。

### 5. Handoff 简化为 todo_list 指针（M-3）

- [ai_context/handoff.md:51-58](ai_context/handoff.md#L51-L58)：原 36 行枚举（"removed" / "renamed from" 清单 + 8 项 break points）替换为 6 行短指针段，明确指向 `docs/todo_list.md` 的 `## 立即执行` section，并显式禁读 `## 下一步` / `## 讨论中` 段防止 token 浪费。

### 6. todo_list.md 重组

- 把 `T-WORLD-SNAPSHOT-S001-S002-MIGRATE` 从 `## 下一步` 迁到 `## 立即执行`（handoff 引用此 section）
- 删除 `T-EXTRACTION-BRANCH-DISPOSE` 整条（H-2 已落地）
- 在 `## 下一步` 末尾新增 `T-PHASE35-IMPORTANCE-AWARE`（L-3 推迟项）

### 7. .gitignore 重排（L-1）

- [.gitignore](.gitignore)：通读后整理为 7 个语义 section（Extraction runtime artifacts / Generated retrieval / Source corpus / User data / Local databases / Local config overrides / Tool & OS artifacts）
- 删根级 `analysis/evidence/*` 死规则（仓库无根级 `analysis/`）
- 合并 `.claude/scheduled_tasks.lock` 进 `.claude/*.lock`
- 注释统一为"是什么 + 为什么"

## 与计划的差异

- 见上方"执行偏差"5 条
- 计划清单全数完成，无新增功能也无删除功能

## 验证结果

- [x] 5 份 schema 文件 jsonschema metaschema 校验通过 — `Draft202012Validator.check_schema` for all 5
- [x] `automation/persona_extraction/orchestrator.py` `python -m py_compile` 通过；`git_utils.py` 同；`delete_branch` / `git_gc_prune_now` 两个新公共函数可正常 import
- [x] 代码 `_check_*` 计数 = 9，文档三处（architecture / requirements / automation README）均已对齐为 9
- [x] grep `relationship_behavior_map` 全仓除 `ai_context/decisions.md:90` (#27g, ADR 历史档案，规则豁免) 外无残留
- [x] grep `analysis/evidence/*` 仅命中 `works/*/...` 形式（无根级），通过 `git check-ignore` 32 条路径全量验证 .gitignore 行为：
  - 应 ignore 20 条全部命中（含 progress / chapter_summaries / scene_splits / evidence/foo / sources/raw / sources/works/*/raw / sources/works/真实work_id/manifest.json / users/真实user / config.local.toml / .claude/settings / .claude/scheduled_tasks.lock / .db / .faiss / .npy / __pycache__ / .pyc / .history / .DS_Store）
  - 应 NOT ignore 12 条全部正确豁免（含 users/_template 全树 / sources/raw/.gitkeep / sources/works/_template/manifest.json / works/*/analysis/evidence/.gitkeep / works/*/world|characters|manifest 全树 / config.toml / ai_context）
- [x] `docs/todo_list.md` 顶层确认 `## 立即执行` / `## 下一步` / `## 讨论中（未定案）` 三段；`T-WORLD-SNAPSHOT-S001-S002-MIGRATE` 在「立即执行」、`T-PHASE35-IMPORTANCE-AWARE` 在「下一步」末尾、`T-EXTRACTION-BRANCH-DISPOSE` 已删
- [x] `ai_context/handoff.md:51-58` 已替换为指针段，引用 `## 立即执行` 且显式禁读 `## 下一步` / `## 讨论中`
- [x] dispose 措辞三处一致（decisions.md / architecture.md / conventions.md）+ 两处 docs（extraction_workflow.md / automation README）+ 代码

## Completed

- **Status**: DONE
- **Finished**: 2026-04-27 01:59:00 EDT
