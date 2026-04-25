# rename-project-to-offpage

- **Started**: 2026-04-25 02:18:04 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

GitHub 远程仓库已建为 `LeanderLXZ/offpage`；用户要求把项目名也从
`persona-engine` 改为 `offpage`，与远程对齐。

涉及范围（`git grep` HEAD tracked，排除 logs/）：

- `persona-engine`（小写连字符）：~30+ 处文档 + prompt + 33 个 schema 的 `$id`
- `Persona Engine`（Title Case）：README.md / AGENTS.md / CLAUDE.md / config.toml /
  automation/persona_extraction/__init__.py 6 处

`persona_engine` 下划线：0 处。`persona_extraction`（python 子模块名，不是项目
名）：保留不动。

## 结论与决策

**全字串替换**，两条映射：

- `persona-engine` → `offpage`（含所有 schema `$id` 改为 `offpage/<subdir>/<name>.schema.json`）
- `Persona Engine` → `Offpage`（Title Case 6 处）

不动：

- python 包名 `persona-extraction`（pyproject.toml `name`）— 这是子模块名，与项目名独立
- worktree 路径约定 `../<repo>-main`：`<repo>` 是 placeholder，实际展开时自然变成 `offpage-main`，跟随 cwd 的 basename 走，无需改 skill 文本
- `extraction/` 分支前缀、`library` 分支名：与项目名无关
- `logs/` 历史 log：约定豁免

**本会话不做**目录 rename（`/home/leander/Leander/persona-engine` →
`/home/leander/Leander/offpage`）：rename 会让 Claude Code 主 cwd 失效、本会话
shell tool 无法继续工作。本 commit 只改文件**内容**；目录 rename 与
`~/.claude/projects/-home-leander-Leander-persona-engine/memory/` 的 memory dir
迁移作为本会话结束后的手工 follow-up（步骤已在 POST 总结里给用户）。

## 计划动作清单

- 全仓 sed 替换：`persona-engine` → `offpage`、`Persona Engine` → `Offpage`
- 影响文件分类：
  - schemas/（33 文件）：`$id`
  - automation/（README + pyproject + cli + ingestion/validator + 7 prompt templates + config.toml + __init__.py）
  - docs/（requirements.md + architecture/data_model.md）
  - prompts/ingestion 与 prompts/review 与 prompts/shared 各 1 处
  - .claude/commands 与 .agents/skills 的 full-review.md（1 对）
  - schemas/README.md
  - 顶层 README.md / AGENTS.md / CLAUDE.md

## 验证标准

- [ ] `git grep -nE 'persona-engine|Persona Engine'` HEAD 上 = 0 命中（除豁免）
- [ ] schemas/ 中 33 份 $id 全部 `offpage/...` 开头，jsonschema 自校验通过
- [ ] `python3 -c "from automation.persona_extraction.cli import *; from automation.persona_extraction.orchestrator import ExtractionOrchestrator"` 成功
- [ ] commit + push origin main 成功
- [ ] library / extraction merge main 无冲突

## 执行偏差

5 个 prompts/ 下中文路径名文件因 escape 序列再次跑了一次 sed，与上轮 scrub
的处理方式相同；纳入本次提交。

<!-- POST 阶段填写 -->

## 已落地变更

57 个 tracked 文件批量替换：

- 顶层：`README.md` / `AGENTS.md` / `CLAUDE.md`（标题与文案 Persona Engine → Offpage）
- `automation/`：`README.md` / `pyproject.toml` / `config.toml` / `cli.py` / `__init__.py` / `ingestion/validator.py` / 6 份 prompt template
- `docs/`：`requirements.md` 序言、`architecture/data_model.md` 目录树
- `prompts/`：5 份中文文件（ingestion + review×3 + shared）
- `schemas/`：33 份 JSON schema 的 `$id` 全部 `persona-engine/...` → `offpage/...`，外加 `schemas/README.md` `$id` 模板说明
- skill 镜像：`.claude/commands/full-review.md` + `.agents/skills/full-review/SKILL.md`

替换映射：

- `Persona Engine` → `Offpage`（Title Case 6 处）
- `persona-engine` → `offpage`（其余全部）

不动：`persona-extraction`（python 包名 / pyproject `name`，是子模块名而非项
目名）；`persona_extraction` 子包 import 路径；`extraction/` 分支前缀；
`library` 分支名；worktree 命名约定 `../<repo>-main` 中的 `<repo>` placeholder。

## 与计划的差异

PRE 计划清单覆盖完毕；执行偏差段补 5 份中文文件名 sed，已记录。

## 验证结果

- [x] `git grep -nE 'persona-engine|Persona Engine'` 在 HEAD 上 = 0 命中（除 logs/ 豁免）
- [x] 33 份 schema 全部 `Draft202012Validator.check_schema` 通过；`$id` 改为 `offpage/...`
- [x] `python3 -c "import automation.persona_extraction.cli/orchestrator/git_utils/config"` 全部 OK
- [ ] commit + push origin main（待 Step 8）
- [ ] library / extraction merge main 无冲突（待 Step 9）

## Completed

- **Status**: DONE
- **Finished**: 2026-04-25 02:19:34 EDT
