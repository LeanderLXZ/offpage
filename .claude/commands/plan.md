# /plan — 锁定为只讨论模式

激活后强制进入"只讨论方案"模式：**禁止任何写文件 / 改动操作**，专注
在会话里分析、列方案、提问、权衡。讨论收敛后由用户自己再用 `/go` /
`/commit` / `/todo-add` 等独立 skill 落盘——本 skill 不主动触发。

## 规则

- **零写**：禁用 Write / Edit / NotebookEdit
- **Bash 仅只读**：cat / grep / ls / find / git log / git diff /
  git status / wc / head / tail 等查询命令可用；**禁止** git add /
  commit / push / pull / merge / checkout / reset / rm / mv / mkdir /
  touch / 任何写文件 / 任何 mutating 命令；网络写请求（POST / PUT /
  DELETE）也禁止
- **不调用写 skill**：`/go` / `/commit` / `/todo-add` / `/post-check` /
  `/full-review` 等都可能动文件，不要主动触发
- **不开临时文件**：plan.md / draft.md / notes.md / .scratch 都不要

---

**镜像约束**：本文件和 `.agents/skills/plan/SKILL.md` 正文保持同步——
任一侧修改必须在同 commit 内镜像到另一侧。`.agents/skills/plan/SKILL.md`
额外带 YAML frontmatter（`name` / `description`），正文（从一级标题
`# /plan` 起往下）与本文件**逐字一致**。
