---
name: branch-inventory
description: 全分支盘点 — 列所有本地 + remote 分支，按 Main / Resting / Protected (active) / Protected (abandoned) / Other local / Remote-only 分组。从 ai_context/skills_config.md 读 `## Main branch policy`、`## Protected branch prefixes`、`## Background processes`，每个分支标注：last commit 时间 + age、ahead/behind tracking、对应 worktree、（保护前缀分支额外）pgrep 关联的活跃 extraction 进程。末尾给"建议动作"摘要（如 abandoned 分支可能要 git branch -d、ahead 多 commit 提醒 /push 等）但**不执行**。只读：不 checkout、不 merge、不 push、不 fetch、不删分支、不改 git 状态。$ARGUMENTS 可选 = 分支名子串过滤（如 extraction）/ "all"。用户说 "还有哪些分支"、"分支盘点"、"哪些 extraction 分支废了"、"branch-inventory"、"看下分支状况"、"清一下分支" 时触发。
---

# /branch-inventory — 全分支盘点

列出所有本地 + remote 分支并按角色分组，标注每个分支的 git 状态 + 进程绑定。**只读，不动任何 git / 进程**。

## Step 0: 加载 skills 配置

`Read` `ai_context/skills_config.md`，取：

- `## Main branch policy` → main branch 名（典型：`main`）
- `## Protected branch prefixes` → 受保护前缀清单（典型：`extraction/`）
- `## Background processes` → pgrep patterns + Process artifacts（用于关联保护前缀分支与活跃进程）

任一段缺失或全为 `(none)` → 用 git 默认值兜底（main = `main`、protected = ∅、pgrep = ∅），并在输出顶部显式打印**配置降级**说明。

## Step 1: 解析 $ARGUMENTS

- 缺省 / `all` → 列全部
- 字符串 → 作为分支名子串过滤（仅展示名字含此子串的分支）

## Step 2: 收集本地分支

- `git branch -vv` → 解析出每条：分支名、HEAD short sha、tracking branch、ahead/behind 计数
- 对每条 `git log -1 --format='%cI %s' {branch}` → 拿最后 commit ISO 时间 + 标题
- 计算 age：`now - last_commit`（用 skills_config `## Timezone` 命令模板取 now，输出"3d 4h"形式）

## Step 3: 收集 remote 分支

- `git branch -r` → 列所有 remote 分支（去除 `HEAD ->` 行）
- 对没有对应本地分支的 remote 分支：标注 **remote-only**

## Step 4: 收集 worktree 绑定

- `git worktree list --porcelain` → 解析每个 worktree 的 path / branch
- 建立 branch → worktree 反向映射

## Step 5: 关联活跃进程（仅保护前缀分支）

对每个匹配 `## Protected branch prefixes` 的分支（典型 `extraction/*`）：

- 该分支是否对应活跃 worktree（Step 4 映射）
- 若对应 worktree：在该 worktree 路径下 `pgrep -f '{pgrep_pattern}'` 检查
- 也可通过 `## Background processes` 的 pid 文件路径（如 `works/{work_id}/analysis/progress/*.pid`）反推：分支名是否含 work_id ∧ pid 文件对应进程是否存活

得到每个保护前缀分支的"活跃进程绑定"标志（true / false / unknown）。

## Step 6: 分组 + 输出

按以下顺序输出（每组一张表，**空组也列出"（无）"** 以便一眼看全）：

1. **Main**：`{main_branch}` 单行
2. **Resting branches**：默认包括 `library`、`master` 等常见休息分支（如本仓有）
3. **Protected (active)**：保护前缀分支 ∧ 有活跃进程绑定
4. **Protected (abandoned)**：保护前缀分支 ∧ 无活跃进程（疑似废弃）
5. **Other local**：其余本地分支
6. **Remote-only**：仅 remote 存在的分支

每行表：

| branch | last commit (ISO + age) | ahead/behind | tracking | worktree | process | note |

末尾**建议动作**摘要（**不执行**，只列）：

- `Protected (abandoned)` → 建议核对是否可 `git branch -d`（用户自决；可能仍保留有未合并的 extraction 中间产物）
- 本地 ahead 多 commit 未推 → 提醒可能要 `/push`
- 本地 behind tracking → 提醒可能要 `git fetch` / `git pull`
- worktree 指向已删除分支 → 提醒可能要 `git worktree prune`

## 限制

- 只读：不 `git checkout` / `merge` / `push` / `fetch` / `pull` / `branch -d` / `worktree prune` / `remote update` / `commit`
- 分支数 > 50 时按分组各只展示前 20 行 + "（… 还有 N 条已折叠）"提示，避免对话刷屏

---

**镜像约束**：本文件和 `.agents/skills/branch-inventory/SKILL.md` 的 YAML frontmatter + 正文（从一级标题 `# /branch-inventory` 起到本段之前）**逐字一致** — 任一侧修改必须在同 commit 内镜像到另一侧。本镜像约束段是两侧唯一允许差异的部分（路径互引）。
