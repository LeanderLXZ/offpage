---
name: recent-activity
description: 最近 N 条项目动作倒序时间线 — 综合 git commits（含 commit body）、logs/change_logs/（含文件正文首部）、docs/todo_list.md 条目的 `**更新时间**` 字段，按时间戳 DESC 合并取前 N 条，输出"块视图"——每条带可读详情让你直接看懂"做了什么"。$ARGUMENTS 可选叠加：N（纯数字 / `N=10`，默认 10）、源过滤（commits / logs / todo，默认全扫）。和 /branch-inventory（看分支） / /extraction-status（看任务）形成"看一眼现状"三件套；本 skill 看"最近做了 / 讨论了什么 / 改了什么"。只读：不改 git、不改文件、不 commit、不调外部。skills_config 的 `## Timezone` / `## Activity sources` 任一缺失 → fail loudly。用户说 "最近做了什么"、"recent-activity"、"近期变更"、"近期讨论"、"看下时间线"、"最近 10 条动作" 时触发。
---

# /recent-activity — 最近 N 条项目动作倒序时间线

把项目里最近发生的 N 条"动作"按时间倒序合并成一段块视图，每条不光列时间戳还展开正文（commit body / change_log 首部）让你直接看懂"做了什么 / 改了什么 / 删了什么 / 回滚了什么"。三类源：

1. **git commits**（当前分支，去 merge；带 commit body）
2. **change logs**（`logs/change_logs/` 下文件名带时间戳的 markdown；带文件正文首部）
3. **todo entries**（`docs/todo_list.md` 各条目的 `**更新时间**` 字段；只展条目标题）

**只读**：不改 git / 文件 / todo_list，不 commit，不调外部。

## Step 0: 加载 skills 配置

`Read` `ai_context/skills_config.md`，取：

- `## Timezone` → 时区命令模板（用于解析 filename 时间戳与渲染时拼时区）
- `## Activity sources` → change_logs 路径 + filename 时间模式 + todo_list 路径 + 更新时间字段名

任一段缺失或路径不存在 → fail loudly：打印缺失项 + 提示按 plugin 模板补齐，停手。

## Step 1: 解析 $ARGUMENTS

token 化（按空白拆分，顺序无关）：

| token 形态 | 语义 |
|---|---|
| 纯数字 / `N=<int>` | 取最近 N 条（默认 10） |
| `commits` / `logs` / `todo` | 源过滤（可叠加，多个 = OR） |

缺省：N = 10，源 = 全扫。

非法 token → 打印 "未识别 token `<val>`，可选: <整数 / N=<int> / commits / logs / todo>" 并停手。

**N 的作用范围 = 合并后的总条数**（不是每源各 N）；某源条数远多于另两源时不强行配额，倒序自然取前 N。

## Step 2: 收集 git commits（含 body；若 source 含 commits）

```
git log -n <3*N> --no-merges --pretty=format:'==REC==%n%cI%n%h%n%s%n--BODY--%n%b' HEAD
```

按 `==REC==` 切分；每个记录解析为：

- 第 1 行：`%cI`（ISO 时间戳含时区）
- 第 2 行：`%h`（short sha）
- 第 3 行：`%s`（subject）
- 第 4 行：`--BODY--` 分隔符
- 第 5 行起到下一个 `==REC==` 之前：`%b`（commit body，可能多行；可能为空）

**body 渲染规则**：
- 空 body（多数 single-line commit）→ 显示 `（无 body）`
- 非空 body → 原样保留**前 25 行**；超出在末尾追加 `（… body 截断，git show <sha> 看完整）`
- body 内的反引号 / pipe / markdown 符号**不转义**——直接当 markdown 块嵌入即可（输出格式是块视图不是表格，无 cell 边界冲突）

约束：
- 当前分支视角（`HEAD`），不做跨分支聚合
- merge commits 忽略（`--no-merges`）
- `3*N` 过采样上限；合并后统一截断到 N

## Step 3a: 收集 change_logs 索引（只列文件，不读正文；若 source 含 logs）

按 skills_config.md `## Activity sources` 的 change logs 路径与 filename 时间模式：

```
ls -1 <change_logs_path>/*.md | sort -r | head -n <3*N>
```

filename 倒序排列，**先只构建索引**：每个 filename 解析时间戳（例如
`2026-04-30_134108_skills_polish.md` → `2026-04-30T13:41:08`，按 skills_config
`## Timezone` 拼时区），记录 `(timestamp, filename, slug)`。slug = filename
去时间前缀、去 `.md` 后缀、下划线换空格。

**正文延后读** —— 见 Step 5b。这一步不打开任何文件，避免读那些 Step 5 合并后会被截掉的 log。

## Step 4: 收集 todo_list 更新（若 source 含 todo）

`Read` `<todo_list_path>`（按 skills_config.md `## Activity sources` 路径）取全文（todo_list 通常 ~700 行；本 skill 必须扫到正文，不带 limit）。

按 `### [T-XXX]` 切块（注意标题里方括号需要转义），每块内 grep 一行：

```
**更新时间**：YYYY-MM-DD HH:MM <TZ>
```

**缺字段的条目跳过**（旧格式残留 / 未被 `/todo-add` 触过的条目；不算"近期动作"）。

按时间戳 DESC 排序后取前 `3*N` 条，记录 `(timestamp, T-XXX, 标题首行)`。
**不展开 entry 正文**（动机 / 改动清单 / 状态字段都不读；想看详情让用户打开 `docs/todo_list.md#T-XXX`）。

## Step 5: 合并 + 倒序 + 取前 N

把 Step 2 / 3a / 4 三源结果合并，按 Timestamp **DESC** 排序，截断到 N 条。

如果合并前总数 > N：在输出末尾打印一行 `（… 还有更早的动作未列；用 N=<更大数> 看更多）`。

## Step 5b: 为入选的 log 条目读正文

只对 Step 5 截断后保留的 `log` 类条目逐个 `Read` 对应文件（git body 已在 Step 2 拿到，todo 不展开）：

- `Read <change_logs_path>/<filename>` 加 `limit: 40`（前 40 行足以覆盖首节"## 背景 / ## 改动清单"）
- 渲染时保留**前 25 行**（含 H1/H2 标题、首节内容）
- 超 25 行追加 `（… log 截断，见 <filename>）`
- 文件不存在或读失败 → 该条 body 显示 `（log 读失败：<error>）`，不停手

## Step 6: 输出（块视图）

固定格式：

```
## /recent-activity — 最近 N 条

- N: <N>
- 源: <commits / logs / todo 实际启用的几项>
- 实际条数: <合并后总数>（git=<N1>, log=<N2>, todo=<N3>）

---

### 1. <Timestamp> · git · `<sha>`

**<commit subject>**

<commit body — 最多 25 行；空 body 显示 "（无 body）"；超长追加截断行>

---

### 2. <Timestamp> · log · [<filename>](<change_logs_path>/<filename>)

**<filename slug>**

<change_log 头部 25 行 — 原样保留 markdown>

---

### 3. <Timestamp> · todo · [T-XXX](docs/todo_list.md#T-XXX)

**<标题首行（截断 ≤ 60 字）>**

（todo 仅展条目标题；想看详情打开 docs/todo_list.md#T-XXX）

---
```

排序号 1..N 反映合并后倒序位置；时间戳一律用 ISO 8601 含时区。

末尾**不加建议动作 / 不评论**——本 skill 只列事实，怎么用让用户决定。

## 约束

- **只读**：不 `git checkout` / `merge` / `push` / `fetch` / `commit`，不改 todo_list / change_logs，不调外部 API
- 不接受时间窗参数（`24h` / `since=...` 不支持）；要按时间过滤先 `/branch-inventory` 看 commit 时间，或者直接 `git log --since`

---

**镜像约束**：本文件和 `.agents/skills/recent-activity/SKILL.md` 的 YAML frontmatter + 正文（从一级标题 `# /recent-activity` 起到本段之前）**逐字一致** — 任一侧修改必须在同 commit 内镜像到另一侧。本镜像约束段是两侧唯一允许差异的部分（路径互引）。
