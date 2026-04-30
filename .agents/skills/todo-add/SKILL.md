---
name: todo-add
description: 把当前会话刚拍板 / 讨论的事项加进 docs/todo_list.md。先做语义匹配判定 UPDATE vs CREATE：能对应已有条目就更新（必要时换段），否则新建。$ARGUMENTS 指定段位（不传：UPDATE 沿用已有 / CREATE 默认 "Next"；discuss/讨论中 → "Discussing (Undecided)"；executing/正在执行 → "In Progress" 单槽段）。从会话上下文提取动机 / 现状 / 触发链；信息不足或多条疑似命中时主动问，不靠猜。CREATE 时与 todo_list.md + todo_list_archived.md 全量去重；UPDATE 时已有 ID 不变。预览（CREATE 看全文 / UPDATE 看字段 diff + 段位变化）→ 等确认 → 写入 → 同步刷新顶部索引段（规则指向 todo_list.md "Index maintenance" 段）。不 commit / 不 push——持久化交给 /commit 或 /go。用户说"加到 todo"、"登记 todo"、"todo-add"、"加进待办"、"放到下一步"、"放到讨论中"、"更新 todo"等触发。
---

# /todo-add — 把会话讨论结果加进 todo_list

把当前会话中刚刚讨论 / 拍板的事项加进 `docs/todo_list.md`：**已存在
对应条目则更新**（必要时换段），**不存在则新建**。可通过 `$ARGUMENTS`
指定目标段位。**不 commit**——持久化交给 `/commit` 或 `/go`。

## Progress reporting

下方流程分为 `## Step 1:` ~ `## Step 7:`。每进入一个 step，**先打印一行进度**：`[/todo-add] Step N: <子段标题>`，让用户实时看到当前位置；最后一步执行结束打印 `[/todo-add] done`。跳过某 step 时打印 `[/todo-add] Step N: 跳过（理由：…）` 而不是静默略过。

## Step 1: 解析 $ARGUMENTS（目标段位）

| 取值 | 目标段 |
|---|---|
| 不传 / `next` / `下一步` | `## Next` |
| `discuss` / `讨论中` | `## Discussing (Undecided)` |
| `executing` / `正在执行` | `## In Progress`（单槽，限制见 Step 6） |

非法值 → 打印"段位 `<val>` 未识别，可选: Next / Discussing / In Progress" 并停手。

`$ARGUMENTS` 不传时：UPDATE 模式默认沿用已有段位；CREATE 模式默认进
"Next"。

## Step 2: 锁定要登记的事项

从当前会话最近若干轮抓取本次要登记的"事项"——通常是用户刚拍板 /
讨论的具体问题 + 结论 + 触发点。

信息不足（缺动机 / 缺现状 / 缺触发链 / 缺改动指向）时**主动问用户补**——
"要登记的是哪段讨论？补一两句关键背景 / 触发点 / 期望结果。" 不靠猜，
不替用户拼接。

## Step 3: 判定 UPDATE vs CREATE

抓全量已有条目（`docs/todo_list.md` + `docs/todo_list_archived.md`）：
`grep -hoE 'T-[A-Z0-9-]+' docs/todo_list.md docs/todo_list_archived.md | sort -u`
取 ID 集合；并读已有条目的标题 + 上下文，做**语义匹配**判断本次要登记的
事项是否对应一个已有条目（按内容意图，不只是字面 ID）。

判定结果：

- **UPDATE 模式**：找到对应条目 → 记录已有 `T-XXX` + 已有所在段位
  + 已有条目内容快照（用于 Step 4/5 diff）。如多于一条疑似命中，**主动
  问用户**："看到 T-AAA / T-BBB 都可能对应，要更新哪一条？还是新建？"
  不替用户决定。
- **CREATE 模式**：未找到匹配 → 从内容意图凝练新 `T-XXX` slug（英文短
  代号，全大写 + 连字符），与已有 ID 集合不冲突；冲突就改名。

UPDATE 模式下的段位决议：

- `$ARGUMENTS` 显式传段位 → 服从（哪怕跨段移动）
- `$ARGUMENTS` 未传 → 默认沿用已有段位；但如本次讨论的语境**显著暗示**
  应换段（典型场景：Discussing 条目刚被拍板 → 应进 Next / Next 条目 `/go`
  启动 → 应进 In Progress），则在 Step 5 预览里建议换段并问用户。

## Step 4: 合成条目草稿 / 变更 diff

**CREATE 模式**：按目标段位字段要求合成全条。所有段位共有：

- T-XXX ID + 中文短标题
- **上下文**：动机 + 现状 + 触发链
- **完成标准**
- **依赖**

段位差异：

- **Next**：必须含 **改动清单**（文件路径 / 行号 / 改动要点），单源不缺
- **Discussing**：必须含 **待决策项**（编号列表，每条 1–2 句）；改动清单可暂缺
- **In Progress**：要求 **开始时间**（YYYY-MM-DD HH:MM 时区缩写——按
  skills_config.md `## Timezone`）+ **当前状态**（进行中 / 等用户决策 / 暂停）

视情况补：**预估** / **未落地原因** / **暂不做的事**。

格式参照 `docs/todo_list.md` 既有条目（"### \[T-XXX\] 中文标题" 起头，
字段标题用 `**字段名**`）。

**UPDATE 模式**：取已有条目作为基线，把本次讨论的新信息合并进去。
未变更的字段**原样保留**，不复述；变更的字段明确标注。如果换段，按
**目标段**的字段要求补齐缺字段（如 Discussing → Next，需补 **改动清单**）。

## Step 5: 给用户预览 + 等确认

**CREATE 模式**：打印合成的条目全文 + 目标段位，问一句：

```
这样登记到 "<目标段>"？补字段 / 改字段 / 改 ID / 改段位 都行。
```

**UPDATE 模式**：打印**变更摘要**——明确说"将更新已有条目 `T-XXX`"，
列出：

- **字段级 diff**：哪些字段变了，简明 before/after（不复述未变字段全文，
  一句话带过即可）
- **段位变化**（如换段）：显式 `from <原段> → to <目标段>`
- **ID 不变**（除非用户明确要求改 ID）

问一句：

```
这样更新 `T-XXX`？字段微调 / 取消换段 / 变成新建（强制 CREATE）都行。
```

**两种模式都不确认前不写文件**。

## Step 6: 写入 todo_list.md

确认后：

**CREATE 模式**：

a. 找到目标段（`## In Progress` / `## Next` / `## Discussing (Undecided)`），把
   条目按 `### [T-XXX] 中文标题` 起头追加到该段**末尾**（同段内按用户优先级；
   新条默认尾部，除非用户说"插到最前"）。条目之间用 `---` 分隔（与既有约定一致）

b. **In Progress** 段单槽位：写入前 grep 该段已有 `### \[T-` 数；非 0 则**拒绝写入**，
   提示 "In Progress 段已被占用，请先把当前那条 commit 完成或退回 Next 再启动新任务"

**UPDATE 模式**：

a. **同段内更新**：定位 `### [T-XXX]` 块（含其下所有字段，到下一个
   `### [T-` 或段末为止），整块替换为新版本。其他段位完全不动。

b. **跨段移动**：从原段删除整个 `### [T-XXX]` 块（连带其前后多余的
   `---` 分隔），按 CREATE 模式 a 的方式追加到目标段末尾。**In Progress**
   段单槽限制同样适用——目标段非空时拒移入，提示同上。

**统一刷新**：动过的段（CREATE 的目标段 / UPDATE 的同段或源+目标段）
+ 顶部 `## Index (auto-generated; do not hand-edit)` 段——按 `docs/todo_list.md`
"## File guide → Index maintenance"段定义的列规则与字段推断规则刷新对应
子表行 + 汇总行；本 skill **不复述规则**，以那段为唯一权威。

## Step 7: 收尾报告

打印（按本次模式选一）：

- **CREATE**：✓ 已登记 `T-XXX` 到 "<段位>"
- **UPDATE 同段**：✓ 已更新 `T-XXX`（"<段位>"）
- **UPDATE 跨段**：✓ 已更新 `T-XXX` 并移段（<原段> → <新段>）

后接：

- 索引刷新：动过的子表 行数 X → Y，汇总 N → N'（CREATE 时 N+1；UPDATE 同段时不变；UPDATE 跨段时两子表各 ±1）
- 提示："本 skill 不 commit。要持久化请 /commit 或 /go。"

不进入 /go、不 commit、不 push。

## 约束

- **不 commit / 不 push**
- **不动无关段位**：CREATE 只动目标段 + 索引；UPDATE 同段只动该段 +
  索引；UPDATE 跨段只动源段 + 目标段 + 索引；其他段位条目内容一律不
  顺手改
- **UPDATE 优先于 CREATE**：能匹配到已有条目就更新，不要重复造同一
  概念的新条目；多条疑似命中要问用户
- **UPDATE 时已有 ID 不变**：除非用户明确要求改 ID
- **ID 查重必须做**：CREATE 时与 `todo_list.md` + `todo_list_archived.md`
  全量对照，新 ID 不冲突
- **预览必须等确认**：CREATE 看全文 / UPDATE 看 diff，都不能合成完
  直接写盘
- **会话不清晰主动问**：CREATE 时缺字段问；UPDATE 时多条疑似命中问；
  不替用户编字段或挑条目
- **In Progress 单槽**：段非空就拒写（CREATE）/ 拒移入（UPDATE 跨段）
- **索引规则单源**：刷新逻辑指向 `docs/todo_list.md` "Index maintenance" 段，
  本 skill 不重复定义；那段改了这里自动跟随

---

**镜像约束**：本文件和 `.agents/skills/todo-add/SKILL.md` 正文保持同步——
任一侧修改必须在同 commit 内镜像到另一侧。`.agents/skills/todo-add/SKILL.md`
额外带 YAML frontmatter（`name` / `description`），正文（从一级标题
`# /todo-add` 起往下）与本文件**逐字一致**。
