---
name: todo-list
description: 直接读 docs/todo_list.md 顶部 ## Index (auto-generated; do not hand-edit) 段并原样渲染给用户，末尾问一句"想看哪条？"。$ARGUMENTS 可传关键字过滤 ID。索引由维护 todo_list.md 的人在改条目时同步刷新（规则在 todo_list.md 顶部 "Index maintenance" 段），/todo-list 信任索引、不重新解析、不重新分档、不生成建议。只读不改 todo_list / 代码 / 不 commit。/todo 是 /todo-list 的别名，两者等价。用户说"todo"、"todo-list"、"接下来做啥"、"todo list 上有啥"、"现在该干嘛"时触发。
---

# /todo-list — todo_list 索引展示（别名 `/todo`）

直接读 `docs/todo_list.md` 顶部 `## Index (auto-generated; do not hand-edit)` 段并原样渲染给用户，末尾问一句"想看哪条？"。**只读**——不解析正文、不重新分档、不生成建议、不改 todo_list、不改代码、不 commit。`$ARGUMENTS` 可选作为 ID 关键字过滤（如 `schema` 只显示 ID 含 schema 的条目）；不传则全展示。

索引段是确定性缓存，由维护 `docs/todo_list.md` 的人在改条目时同步刷新（规则在 todo_list.md 顶部的 "Index maintenance" 段）。`/todo-list` 信任索引、不重新解析。

`/todo` 是本 skill 的别名，等价于 `/todo-list`，输入任意一个都触发同一行为。

## 步骤

### 1. 读索引

`Read` `docs/todo_list.md` **必须带 `limit=100`**——索引段在文件顶部，整文 ~700 行全读会大幅拖慢响应、浪费 context。从读到的内容里提取 `## Index (auto-generated; do not hand-edit)` 段——从该标题起到下一个二级标题（`## File guide`）之前的全部内容。

文件不存在 → 打印"⚠️ docs/todo_list.md 缺失"并停手。
索引段缺失（找不到该标题） → 打印"⚠️ docs/todo_list.md 顶部缺索引段；请先按 todo_list.md 「Index maintenance」段补齐再调 /todo-list"并停手。
读到 100 行仍未见 `## File guide`（说明索引段已涨过 100 行截断） → 重新 `Read` `docs/todo_list.md` **不带 `limit`** 取全文，再从全文中提取该段；不要停手。
索引段存在但三张子表都标 "_(none)_" → 仍正常渲染，只是显示"暂无任何任务"。

### 2. 过滤（可选）

若 `$ARGUMENTS` 传入：在三张子表中保留 ID 含该关键字（不区分大小写）的行；其他行删除。过滤后某段为空时保留段标题但写 "_(no matching entries)_"。

不传 `$ARGUMENTS` → 全展示。

### 3. 渲染

把索引段内容直接打印给用户。markdown 表格保留原样，不重排、不重判、不补建议。

`$ARGUMENTS` 过滤过的话，在汇总行末尾加一行 `(filtered by keyword "<keyword>")`。

### 4. 提问 + 停手

末尾打印一行：

```
想看哪条？告诉我 ID（如 `T-XXX`），或者说点别的。
```

打完即**停手**——不进入 `/go`、不改代码、不改 todo_list、不 commit；等用户响应。

## 约束

- **只读**：不改任何文件、不 commit、不 push
- **不解析正文**：信任索引段。索引若与正文不一致，那是上一次改 todo_list 的人没刷新索引——这是写入端的责任，不是 `/todo-list` 的责任
- **不重新分档**：不重新推断 "Importance / Ready / Scope"。这些标签由维护索引的规则决定，规则在 `docs/todo_list.md` 的 "Index maintenance" 段
- **不生成建议**：之前版本会给"建议 1: 直接 /go XXX、建议 2: 讨论 YYY、建议 3: 聊聊别的"——现在删掉。用户看完索引自己决定即可
- **逃生口仍在**：第 4 步的提问明确"或者说点别的"，让用户随时跳出 todo_list
- **`$ARGUMENTS` 仅作过滤**：不接受"展开 T-XXX 详情"等指令；要看详情用户会自己 Read todo_list.md 或说"展开 T-XXX"，那是另一轮交互

---

**镜像约束**：本 skill 由 4 份镜像文件组成，正文必须保持逐字一致（仅 SKILL.md 的 YAML frontmatter `name` 字段不同）：

- `.claude/commands/todo-list.md`（canonical 触发名）
- `.claude/commands/todo.md`（别名触发，正文同步）
- `.agents/skills/todo-list/SKILL.md`（`name: todo-list`，canonical skill）
- `.agents/skills/todo/SKILL.md`（`name: todo`，别名 skill，正文同步）

任一侧修改必须在同 commit 内镜像到全部 4 份。
