# post_check_followup_extraction_pkg_restructure

- **Started**: 2026-05-13 22:25:06 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

上一轮 /go (commit `5d9ef6f`) + /post-check (commit `688175d`, REVIEWED-PARTIAL) 报出 0 H + 6 M + 6 L finding。用户拍板：修 **M1 / M2 / M3 / M6 / L1 / L2 / L3 / L4 / L5 / L6**——即除了 M4（todo 补 `_smoke_triage` 跟进条目）+ M5（TOML stale section silent-drop）以外的全部 finding。M4 + M5 留 todo 跟进（不在本轮 scope）。

## 结论与决策

**修 10 条 finding，全部为单点 doc / 文案 / 注释级修复，不动代码语义、不动 schema 契约**：

- **M1** [docs/architecture/extraction_workflow.md:755](docs/architecture/extraction_workflow.md#L755) — `validator.validate_with_length_tolerance` → 改为裸函数名 `validate_with_length_tolerance`（与同段上下文文风一致）。理由：函数原文件 `validator.py` 已切分消亡，该 stale 模块前缀属于 bulk-replace 漏盖。
- **M2** [extraction/README.md:282-283](extraction/README.md#L282-L283) — 删 "（原 validator.py）" / "（原 consistency_checker.py）" 两处括号说明。理由：违反 `conventions.md §Generic Placeholders` "no legacy / formerly / renamed from" 禁词；目录树自身已说明位置语义。
- **M3** [ai_context/conventions.md:53](ai_context/conventions.md#L53) — Cross-File Alignment row 7 补全 7 个本次实际同步目标：`current_status.md` / `requirements.md` / `skills_config.md`（不限于 `## Source directories` 段）/ `docs/requirements.md` / `extraction/pyproject.toml` / `extraction/validation/README.md` / `.gitignore` / `schemas/README.md` / `works/README.md`。理由：未来同类 path rename 走这条 row 不应漏触发清单。
- **M6** [ai_context/decisions.md:628](ai_context/decisions.md#L628) — rephrase "仅属性 `repair_agent` → `repair` + TOML section `[repair_agent]` → `[repair]`" 为不含 `repair_agent` token 的当前态描述（如"`Config.repair` 属性与 `[repair]` TOML section 同名；`RepairAgentConfig` dataclass 类名保留以避开 `extraction.repair.protocol.RepairConfig` 命名冲突"）。理由：与 user memory `feedback_docs_describe_current_only` 摩擦 + 也消掉本仓内唯一 `\brepair_agent\b` grep 命中。
- **L1** [ai_context/decisions.md:629-630](ai_context/decisions.md#L629-L630) — 删 plumbing 段 `prompts/__init__.py` 列项。理由：磁盘 `extraction/persona_extraction/prompts/` 全是 .md 模板，无 `__init__.py`（Python 包路径上是 namespace package，不需要 init）。
- **L2** [ai_context/decisions.md:#57](ai_context/decisions.md) — 决策 #57 末尾"依赖方向硬约束"段补一行表态："**validation.gates 可依赖 `extraction.persona_extraction.core` 提供的纯函数基础件**（`json_repair` / `schema_loader`）—— gates 是面向具体相位的 validator 实现，需要项目内通用 IO helpers；validation.shared 严格 zero-dep，只用 stdlib + jsonschema。" 理由：covers OQ1，把 `phase2_baseline.py:29-30` 反向 import 的合法性显式写进决策。**用户已认 (a) 选项**——单行表态。
- **L3** [ai_context/decisions.md:38](ai_context/decisions.md#L38) — shell-glob `extraction/persona_extraction/{prompt_builder,scene_archive}.py` 展开为 `extraction/persona_extraction/prompt_builder.py + extraction/persona_extraction/phases/scene_archive.py`。理由：`scene_archive` 已迁 `phases/`，shell-glob 掩盖了迁移事实。
- **L4** [ai_context/decisions.md:339](ai_context/decisions.md#L339) — shell-glob `{orchestrator,progress}.py` 同理：`progress` 已迁 `lifecycle/`。
- **L5** [ai_context/decisions.md:512-513](ai_context/decisions.md#L512-L513) — shell-glob `{snapshot_merge,prompt_builder,orchestrator,progress,config,cli,lane_output}.py` 同理：snapshot_merge→phases / progress→lifecycle / config→core / lane_output→lifecycle 共 4 个文件已迁子目录。展开为完整路径。
- **L6** [extraction/persona_extraction/__main__.py:1](extraction/persona_extraction/__main__.py#L1) — docstring `"""Allow running as: python -m persona_extraction"""` → `"""Allow running as: python -m extraction.persona_extraction"""`。理由：包名改了，docstring 入口字符串未跟新。

## 计划动作清单

- file: `docs/architecture/extraction_workflow.md:755` — `validator.validate_with_length_tolerance` → `validate_with_length_tolerance`
- file: `extraction/README.md:282-283` — 删两处括号注释
- file: `ai_context/conventions.md:53` — Cross-File Alignment row 7 触发清单补 7 个目标
- file: `ai_context/decisions.md` — 5 处改动：(M6) #57 plumbing 段 `repair_agent` token rephrase；(L1) 删 `prompts/__init__.py` 列项；(L2) 补依赖方向硬约束的一行表态；(L3) line 38 shell-glob 展开；(L4) line 339 shell-glob 展开；(L5) line 512-513 shell-glob 展开
- file: `extraction/persona_extraction/__main__.py:1` — docstring 同步包名

## 验证标准

- [ ] `git grep -nE "\bvalidator\.validate_with_length_tolerance\b"` = 0 命中（M1）
- [ ] `git grep -nE "\b原 (validator|consistency_checker)\.py\b"` = 0 命中（M2）
- [ ] `git grep -nE "\brepair_agent\b"` (除 `logs/` + `docs/todo_list_archived.md`) = 0 命中（M6——本次也消掉本仓内唯一一处合法残留）
- [ ] `ai_context/decisions.md` 三处 shell-glob `extraction/persona_extraction/{...}.py` 不再含已迁子目录的文件名（L3 / L4 / L5）
- [ ] `extraction/persona_extraction/__main__.py` docstring 含 `python -m extraction.persona_extraction`（L6）
- [ ] `ai_context/conventions.md:53` row 7 触发清单字符数显著增长（M3 验证补全）
- [ ] `ai_context/decisions.md` #57 末段含 "validation.gates 可依赖 ... validation.shared 严格 zero-dep" 表述（L2）
- [ ] `python -m extraction.persona_extraction --help` 仍 OK（确认 __main__.py docstring 改动不影响 CLI 启动）
- [ ] 所有改动 grep 不引入 `automation` / `repair_agent` / `prompt_templates` 新残留

## 执行偏差

- **M1 扩展到 2 处**：PRE 只列 `docs/architecture/extraction_workflow.md:755` 一处 stale `validator.validate_with_length_tolerance` 模块前缀；Step 5 验证 gate `git grep` 又抓到 `ai_context/decisions.md:384`（决策 #48 length-bound tolerance plumbing 段）有同形态 stale prefix。原 PRE log /post-check report 都没飞过这一处。同源问题、同手势修：rephrase 为裸函数名 `validate_with_length_tolerance` + helper 路径同步指向 `extraction/validation/shared/schema_tolerance.py`（不是 `gates/phase2_baseline.py`——helper 实际在 shared/ 不在 gates/）。覆盖 review_reports/ 内同模式 1 处历史快照按 conventions 不动。

<!-- POST 阶段填写 -->

## 已落地变更

5 个文件，+18/-14 行：

- **`docs/architecture/extraction_workflow.md:755`** — `validator.validate_with_length_tolerance` → `validate_with_length_tolerance`（M1）
- **`extraction/README.md:282-283`** — 删 "（原 validator.py）" / "（原 consistency_checker.py）" 两处括号注释（M2）
- **`ai_context/conventions.md:53`** — Cross-File Alignment row 7 触发清单补 7 个本次实际同步目标（`current_status.md` / `requirements.md` / `pyproject.toml` / `validation/README.md` / `.gitignore` / `schemas/README.md` / `works/README.md` 等），全行长度 750→1383 字符（M3）
- **`ai_context/decisions.md`** — 5 段改动：
  - L38 `{prompt_builder,scene_archive}.py` shell-glob 展开（L3）
  - L339 `{orchestrator,progress}.py` shell-glob 展开（L4）
  - L384 决策 #48 `validator.validate_with_length_tolerance` stale prefix（M1 偏差扩展）
  - L513 `{snapshot_merge,prompt_builder,orchestrator,progress,config,cli,lane_output}.py` shell-glob 展开（L5）
  - 决策 #57 (L595-643)：(M6) `repair_agent` token rephrase 为 `Config.repair` + `[repair]` section + `RepairAgentConfig` 类名独立的当前态描述 / (L1) 删 plumbing 段 `prompts/__init__.py`（不存在）/ (L2) 补依赖方向硬约束 (4)："validation.gates 可依赖 `extraction.persona_extraction.core`，validation.shared 严格 zero-dep" 表态
- **`extraction/persona_extraction/__main__.py:1`** — docstring `python -m persona_extraction` → `python -m extraction.persona_extraction`（L6）

## 与计划的差异

- 增加 1 处偏差修复：`ai_context/decisions.md:384`（决策 #48 同形态 stale validator. prefix）——PRE 与 /post-check report 都没飞过，Step 5 验证 gate `git grep` 抓到后顺手修。
- Step 3 跳过（doc 单点修复，无新设计 / 新需求）。
- Step 6 维护跳过（无 todo 完成、无新 durable 决策、无项目状态变化）。
- Step 7 单线串跑，未派 sub-agent（11 处修改集中在 5 文件、4 个 file 区域，diff 即审）。

## 验证结果

- [x] `git grep -nE "\bvalidator\.validate_with_length_tolerance\b" -- ':!logs/review_reports/'` = 0 命中（M1+偏差）
- [x] `git grep -nE "（原 (validator|consistency_checker)\.py"` = 0 命中（M2）
- [x] `git grep -nE "\brepair_agent\b" -- ':!logs/' ':!docs/todo_list_archived.md'` = 0 命中（M6——本仓内消掉唯一一处合法残留）
- [x] `git grep -nE "extraction/persona_extraction/\{[^}]*(scene_archive|snapshot_merge|progress|config,|lane_output,|,config,|,lane_output)[^}]*\}\.py" ai_context/decisions.md` = 0 命中（L3 / L4 / L5）
- [x] `extraction/persona_extraction/__main__.py:1` docstring 含 `python -m extraction.persona_extraction`（L6）
- [x] `ai_context/conventions.md:53` row 7 长度 1383 字符（M3）
- [x] `ai_context/decisions.md` #57 末段含 "validation.gates 可依赖 ... validation.shared 严格 zero-dep" 表述（L2）
- [x] `python -m extraction.persona_extraction --help` 仍 OK（确认 __main__.py docstring 改动不影响 CLI 启动）
- [x] 所有改动无新引入 `automation` / `repair_agent` / `prompt_templates` 残留（grep 0，除 `simulation/prompt_templates/` 合法存在）

## Completed

- **Status**: DONE
- **Finished**: 2026-05-13 22:36:44 EDT
