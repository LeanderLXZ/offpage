---
name: extraction-status
description: 当前所有 extraction 任务的 one-shot 快照 — 综合 ai_context/skills_config.md `## Background processes` 声明的 pid 文件 + progress.json + pgrep 进程检查，按 running / slow / stalled / dead-pid / orphan-process / completed 分类，输出 work_id × phase × stage × progress × heartbeat × PID × etime 表。和 /monitor（周期上报）互补，本 skill 是即时单次快照，开会话或决策前看一眼。只读：不 kill 进程、不删 pid 文件、不改 progress、不重启、不 commit。$ARGUMENTS 可选 = work_id 关键字（过滤）/ "all"（强制全列）。skills_config 的 `## Background processes` 段缺失或全 `(none)` → 直接报错停手。用户说 "现在有什么任务在跑"、"哪些 extraction 卡了"、"work XXX 跑到哪了"、"extraction-status"、"任务快照"、"看下提取进度" 时触发。
---

# /extraction-status — Extraction 任务即时快照

给当前所有 persona extraction 任务一份 one-shot 状态快照。**只读，不动任何进程 / 文件 / git**。

## Step 0: 加载 skills 配置

`Read` `ai_context/skills_config.md`，取 `## Background processes` 段：

- `pgrep patterns`（典型：`persona_extraction`）
- `Process artifacts`（典型：`works/*/analysis/progress/*.pid`、`*.json`）
- `Process logs`（典型：`works/*/analysis/logs/`）

**段缺失或所有项均为 `(none)`** → 报错"项目未声明后台进程，本 skill 不适用"，**停手**。

## Step 1: 解析 $ARGUMENTS

- 缺省 / `all` → 列全部
- 字符串 → 作为 work_id 子串过滤（仅展示 work_id 含此子串的任务）

## Step 2: 列 pid 文件

- `find` `Process artifacts` 里 `*.pid` glob 模式 → 列出所有 pid 文件路径
- 每个 pid 文件：读 PID 数字、从路径推断 work_id

## Step 3: 检查进程存活

对每个 PID：

- `kill -0 {pid} 2>/dev/null; echo $?` → 进程是否存在（0 = 在）
- 存活则 `ps -p {pid} -o pid=,etime=,cmd=` 拿启动时长 + 完整命令
- 用 `pgrep patterns` 验证 cmd 真的是 persona_extraction（防 PID 复用挂错进程）

## Step 4: 读 progress.json

对每个 pid 同目录或姐妹路径下的 `progress.json`：

- `Read` 取：当前 phase、stage、percent、`last_heartbeat`（或同义字段）
- 计算心跳新鲜度（用 skills_config `## Timezone` 段指定的命令模板取 now）：
  - < 5 min → **fresh**
  - 5–30 min → **slow**
  - \> 30 min → **stale**

## Step 5: pgrep 兜底（找游离进程）

`pgrep -af '{pgrep_pattern}'` 列所有匹配进程：

- 已被 Step 3 覆盖的 PID → 跳过
- 未覆盖 → 标 **orphan-process（无 pid 文件）**，可能是手工启的 / pid 文件丢失 / 路径模式不匹配

## Step 6: 分类 + 输出表

每个任务归一类：

- **running**：pid 文件 ∧ 进程存活 ∧ 心跳 fresh
- **slow**：pid 文件 ∧ 进程存活 ∧ 心跳 slow
- **stalled**：pid 文件 ∧ 进程存活 ∧ 心跳 stale（疑似卡住）
- **dead-pid**：pid 文件 ∧ 进程已死（abandoned，未清 pid）
- **orphan-process**：进程存活 ∧ 无对应 pid 文件
- **completed**：progress.json 显示 100% ∧ 无活进程（可归档）

输出表：

| work_id | status | phase | stage | progress | last heartbeat | PID | etime |

末尾**建议动作**摘要（**不执行**，只列）：

- `dead-pid` → 建议清理 `*.pid` 文件
- `stalled` → 建议查 `Process logs` 看是否真卡死，或 ps 看 CPU/IO
- `orphan-process` → 建议核对 pid 文件是否丢失
- `completed` → 建议归档 work，把 `*.pid` 清掉

## 限制

- 只读：不 `kill` / `kill -9` / `pkill` / `rm` pid 文件 / 改 progress.json / 重启进程 / commit / push（`pgrep` + `kill -0` 是允许的只读探测）
- 不读巨型 log 文件全文（只看 progress.json 摘要 + ps 输出 + log 末 N 行可选）

---

**镜像约束**：本文件和 `.agents/skills/extraction-status/SKILL.md` 的 YAML frontmatter + 正文（从一级标题 `# /extraction-status` 起到本段之前）**逐字一致** — 任一侧修改必须在同 commit 内镜像到另一侧。本镜像约束段是两侧唯一允许差异的部分（路径互引）。
