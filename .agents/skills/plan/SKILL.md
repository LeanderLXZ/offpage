---
name: plan
description: **仅在用户当前发送的这条消息字面里包含 `/plan` 时**进入只讨论模式，作用域 = 本轮一条消息，不跨消息延续——下一条消息没有 /plan → 默认行为恢复，所有写工具解锁。激活时禁用 Write / Edit / NotebookEdit；Bash 仅允许只读查询命令（cat / grep / ls / find / git log / git diff / git status / wc / head / tail 等），任何 mutating 命令（git add / commit / push / pull / merge / checkout / reset / rm / mv / mkdir / touch / 写文件 / 网络写）禁止；不主动触发 /go / /commit / /todo-add / /post-check / /full-review 等写 skill；不开 plan.md / draft.md / notes.md 临时文件。会话历史里出现过 /plan 不算激活。讨论收敛后由用户自行调用写 skill 落盘。$ARGUMENTS = 本次讨论主题（可省）。用户说 '/plan'、'纯讨论'、'只讨论不动文件'、'分析一下方案'、'plan 一下'、'先讨论再说' 等触发。
---

# /plan — 锁定为只讨论模式（仅本轮消息）

**仅在用户当前发送的这条消息中包含 `/plan` 时**生效，强制进入"只讨论
方案"模式：**禁止任何写文件 / 改动操作**，专注在会话里分析、列方案、
提问、权衡。**作用域 = 本轮一条消息**——下一条消息里若不再出现
`/plan`，默认行为立即恢复，不延续锁定状态。讨论收敛后由用户自己再用
`/go` / `/commit` / `/todo-add` 等独立 skill 落盘——本 skill 不主动触发。

## 规则

- **作用域硬约束**：只有用户在**本轮发出的消息字面**里出现 `/plan`
  才进入本模式；模式不跨消息延续。下一条用户消息没有 `/plan` →
  默认行为恢复，所有写工具解锁。会话历史里出现过 `/plan` 不算激活
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
