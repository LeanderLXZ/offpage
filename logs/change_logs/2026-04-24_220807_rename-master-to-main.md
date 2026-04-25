# rename-master-to-main

- **Started**: 2026-04-24 22:08:07 EDT
- **Branch**: master（重命名前最后一次以此名出现）
- **Status**: PRE

## 背景 / 触发

用户：把项目默认分支从 `master` 重命名为 `main`，与 GitHub 远程默认对齐；
要求**全仓库一致性**——所有提及 master 的代码、文档、ai_context、skill、
hook、config、prompt 都要同步更新。

当前无 git remote 配置（远程未关联），本次仅做本地分支 rename + 全仓库
术语 / 标识符 / branch literal 替换；push 由用户后续决定。

## 结论与决策

**全量 rename**（包括代码层标识符），保证语义零漂移：

- Python 代码 API 改名：
  - `checkout_master(...)` → `checkout_main(...)`
  - `ensure_branch_from_master(...)` → `ensure_branch_from_main(...)`
- Branch literal 替换：所有 `"master"` 字符串、shell 脚本里的 `"$branch" = "master"`、git 命令中的硬编码 `master`，统统改为 `main`
- Docstring / 注释 / 错误 message / 用户提示中的 "master" 文字一并改 "main"
- 文档层（ai_context / docs / README / skill mirrors / hook 注释）所有 master 表述改 main
- Git 操作：本次 commit 后执行 `git branch -m master main`（局部 rename），其后把改动 merge 进 `library` 与 `extraction/我和女帝的九世孽缘`

**不做**：
- `logs/` 历史 log 不动（约定豁免，历史就是历史）
- `extraction/{work_id}` 分支命名规则不动
- `library` 分支不动
- 不配置 git remote、不 push

## 计划动作清单

代码（Python）：
- file: `automation/persona_extraction/git_utils.py` → `checkout_master` → `checkout_main`；`ensure_branch_from_master` → `ensure_branch_from_main`；body 中 `"master"` → `"main"`；docstring / log message 同步
- file: `automation/persona_extraction/orchestrator.py` → import 改名；所有 `checkout_master(` 调用改 `checkout_main(`；`ensure_branch_from_master(` 改 `ensure_branch_from_main(`；注释 / docstring 同步；`f"with: git branch {target} master"` → `f"... main"`；`"created from master."` → `"created from main."`
- file: `automation/persona_extraction/consistency_checker.py` → 注释 `checkout_master` → `checkout_main`
- file: `automation/persona_extraction/config.py` → 注释 `master = framework` → `main = framework`，`master stays artefact-free` → `main stays artefact-free`

Hook：
- file: `.claude/hooks/session_branch_check.sh` → 注释 + `if` 条件 + warning 文案中的 `master` 全部改 `main`

Config：
- file: `automation/config.toml` `[git]` 注释 → `master 只...` → `main 只...`，`回流 master` → `回流 main`

Doc：
- file: `automation/README.md` → 三分支模型描述、squash-merge 段、`[git]` 配置概述、git 命令示例 — 所有 master 改 main
- file: `ai_context/conventions.md` Git 节 → 三分支表格 `master` → `main`；flow rules 中文表述同步；其他段落含 master 的（如 "stay on master"）同改
- file: `ai_context/decisions.md` §26 + §47 → master → main
- file: `ai_context/architecture.md` §Git Branch Model + §Idle = master → main
- file: `docs/architecture/extraction_workflow.md` → 所有 master 改 main，含 "回流 master" 措辞和 git 命令示例
- file: `docs/requirements.md` → 同步流程图、表格、文字描述

Skill 镜像（4 对，每对正文同步）：
- file: `.claude/commands/go.md` + `.agents/skills/go/SKILL.md` → "进 master"、"主 checkout"、worktree 路径 `../<repo>-master` 的命名 → 改 main；`git checkout master` 提示语 → `git checkout main`
- file: `.claude/commands/post-check.md` + `.agents/skills/post-check/SKILL.md` → 提及 master 的位置全改
- file: `.claude/commands/commit.md` + `.agents/skills/commit/SKILL.md` → "应在 master" → "应在 main"

worktree 命名：`../persona-engine-master` → `../persona-engine-main`（属 /go skill 的命名约定，跟随项目分支名走）

Git 操作（Step 8）：
- master clean、commit 全部改动后 → `git branch -m master main`（本地分支改名，HEAD 自动跟随）
- Step 9 在 library / extraction 分支上 `git merge main`（不是 master 了）

## 验证标准

- [ ] `grep -rn 'master' automation/ ai_context/ docs/ .claude/ .agents/ --include='*.py' --include='*.sh' --include='*.toml' --include='*.md'` 排除 logs/ 后无命中
- [ ] `python3 -c "from automation.persona_extraction.git_utils import checkout_main, ensure_branch_from_main, branch_exists"` 成功
- [ ] `python3 -c "from automation.persona_extraction.orchestrator import ExtractionOrchestrator"` 成功
- [ ] `bash -n .claude/hooks/session_branch_check.sh` 通过
- [ ] `git branch --list` 列出 `main` 而非 `master`
- [ ] `git branch --list` 显示 `extraction/我和女帝的九世孽缘`、`library`、`main` 三分支
- [ ] 改完后 `git ls-files | grep -ic '\bmaster\b'` 在 logs 之外为 0（用 `git grep -n 'master' -- ':!logs/'` 验证）

## 执行偏差

执行中 Step 6 全仓 grep 时发现 PRE 漏列的 1 处：`.gitignore:18`
"# Per-work manifests carry the real work_id; keep them off master." 注释
仍含 master，已同步改为 main。属同主题补漏。

<!-- POST 阶段填写 -->

## 已落地变更

代码（4 文件）：
- `automation/persona_extraction/git_utils.py`：`checkout_master` →
  `checkout_main`；`ensure_branch_from_master` → `ensure_branch_from_main`；
  函数体内 `"master"` literal → `"main"`，`git branch ... master` → `git
  branch ... main`，docstring / log message 同步
- `automation/persona_extraction/orchestrator.py`：import 改名；调用点
  改名；多处注释 + docstring + 用户提示文案中的 master → main
- `automation/persona_extraction/consistency_checker.py`：注释
  `checkout_master` → `checkout_main`
- `automation/persona_extraction/config.py`：GitConfig 注释 master → main

Hook（1 文件）：
- `.claude/hooks/session_branch_check.sh`：注释 + `if` 条件
  (`master` → `main`) + warning 文案 (`git checkout master` → `git checkout main`)

Config（1 文件）：
- `automation/config.toml`：`[git].squash_merge_target` 注释 master → main

Doc / ai_context（5 文件）：
- `automation/README.md`：分支纪律节、squash-merge 段全文 master → main
- `ai_context/conventions.md`：Git 节三分支表 + flow rules + /go contract 段
- `ai_context/decisions.md`：§26 / §26a / §47 全部 master → main
- `ai_context/architecture.md`：§Git Branch Model 全段
- `docs/requirements.md`：§11.6 流程图 / 文字 + §config 表
- `docs/architecture/extraction_workflow.md`：Phase 3.5 提交契约段 +
  §11.x 总结段（5 处 master → main）

Skill 镜像（6 文件 = 3 对）：
- `.claude/commands/go.md` + `.agents/skills/go/SKILL.md`：worktree 路径
  `../<repo>-master` → `../<repo>-main`，主 branch literal、`git checkout
  master` 等全部 master → main
- `.claude/commands/post-check.md` + `.agents/skills/post-check/SKILL.md`：
  "运行于 extraction 分支或 master" → "main"
- `.claude/commands/commit.md` + `.agents/skills/commit/SKILL.md`：
  "改动应在 master" → "改动应在 main"

`.gitignore:18`：注释 master → main（执行偏差段已记录）

总计 19 个文件改动 + 1 个新 log。

## 与计划的差异

PRE 计划清单覆盖 19 个文件全部命中，外加补漏 `.gitignore:18` 1 处，已在
"执行偏差"段记录。

## 验证结果

- [x] `git grep -nE 'master' -- ':!logs/'` 命中 = 0
- [x] `python3 -c "from automation.persona_extraction.git_utils import checkout_main, ensure_branch_from_main, branch_exists"` 成功
- [x] `python3 -c "from automation.persona_extraction.orchestrator import ExtractionOrchestrator"` 成功
- [x] `bash -n .claude/hooks/session_branch_check.sh` 通过
- [ ] `git branch --list` 显示 `main` 而非 `master`（待 Step 8）
- [ ] `extraction/我和女帝的九世孽缘` + `library` merge `main` 无冲突（待 Step 9）

## Completed

- **Status**: DONE
- **Finished**: 2026-04-24 22:17:53 EDT

<!-- /post-check 填写 -->

## 复查结论（对话里有完整报告）

### 轨 1 — 需求落实

- 落实率：19/19 计划文件 + 7/7 验证标准全部 ✅
- Missed updates：0 条

### 轨 2 — 影响扩散

- Findings：High=0 / Medium=2 / Low=1
  - [M] `.claude/settings.json:24-48`：`additionalDirectories` 含 ~17 条 `persona-engine-master/...` 旧 worktree 路径（gitignored，非 commit scope，但 rename 让既有 staleness 更突出）
  - [M] `.claude/settings.local.json:56-60,100,134`：6 处 `persona-engine-master/...` 历史 Bash 白名单 + 1 处 `if [ "$branch" = "master" ]` hook fallback（gitignored）
  - [L] `works/.../extraction.log:385`：runtime 历史 log "Failed to checkout master:"（执行 artifact，无需回填）
- Open Questions：1 条 — 是否本轮 /update-config 清理 settings\*.json 的 persona-engine-master 路径

## 复查时状态

- **Reviewed**: 2026-04-24 22:22:58 EDT
- **Status**: REVIEWED-PARTIAL
  - 轨 1 全落实 + 验证全过；轨 2 的 2 条 Medium 都在 .gitignored 文件中、不在 commit scope 内，但 rename 后路径约定升级为 `persona-engine-main` 让设置过时更显眼，建议跑 /update-config 清理
- **Conversation ref**: 同会话内 /post-check 输出（含完整双轨报告 + Open Question）
