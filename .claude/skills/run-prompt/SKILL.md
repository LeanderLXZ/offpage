---
name: run-prompt
description: 加载并执行指定的 prompt 文件作为本轮任务。$ARGUMENTS 接受路径（以 `/`、`./`、`../` 开头或含 `/`）或纯文件名 stem（在 `prompts/` 全树模糊搜索匹配 `<stem>` 或 `<stem>.md`）。路径直读、stem 模糊搜（0 命中 fail loudly + 列 `prompts/` 目录结构 / ≥ 2 命中列所有匹配路径要求完整路径 / 1 命中即用）。文件含恰好 1 对外层 fenced 代码块（```text / ```markdown / ```）→ 仅提取块内内容；否则取整文件正文。打印一行 `运行 prompt: <相对路径>` 让用户确认解析正确 → 把 prompt 正文当作本轮用户指令直接接管执行。若 prompt 末尾要求用户补充输入字段（"原始资料路径："、"书名："等）而 `$ARGUMENTS` 未附带 → 先列出待补字段等用户回复再开干。只读 prompt 文件本身，不改、不 commit / push / 改 git 状态；prompt 内的具体动作由 prompt 自己决定。用户说"运行 prompt"、"run-prompt <name>"、"跑一下 <prompt>"、"按 <prompt> 处理"、"加载 <prompt>"、"用 <prompt> 跑一遍" 时触发。
---

# /run-prompt — 运行指定 prompt 文件

把指定的 prompt 文件内容当作本轮任务直接执行。等价于"把 prompt 文件粘贴到对话框作为用户消息发出"，但省去复制粘贴 + 自动模糊匹配文件名。

## Step 0: 解析 $ARGUMENTS

`$ARGUMENTS` 必须非空；缺省 → fail loudly：提示 `/run-prompt 需要 prompt 文件路径或名称参数（如 /run-prompt ./prompts/ingestion/原始资料规范化.md 或 /run-prompt 原始资料规范化）`，停手。

参数形态判定（按以下顺序）：

- **路径形态**：以 `/`、`./`、`../` 开头，或含 `/` → 视为相对 / 绝对路径
- **名称形态**：纯文件名 stem（无 `/`，可带可不带 `.md` 扩展名）→ 视为模糊匹配键

## Step 1: 解析到单个 prompt 文件

**路径形态**：

- 直接 `Read` 该路径
- 文件不存在 → fail loudly：`$ARGUMENTS 解析为路径 '<arg>' 但文件不存在`，停手

**名称形态**：

- 剥离可能的 `.md` 后缀得到 stem
- `find prompts/ -type f \( -name '<stem>' -o -name '<stem>.md' \)` 全树搜索
  - **0 命中** → fail loudly：`在 prompts/ 下找不到名为 '<stem>' 的 .md 文件` + 跑 `find prompts/ -maxdepth 2 -type f -name '*.md'` 列出候选帮助用户校对，停手
  - **1 命中** → 使用该文件
  - **≥ 2 命中** → 列出所有匹配的完整路径，提示 `多个 prompt 同名，请用完整路径再运行`，停手

## Step 2: 提取 prompt 正文

读取文件后判断结构：

- **若文件含恰好 1 对外层 fenced 代码块**（``` 后跟可选语言标记如 `text` / `markdown`，再到匹配的闭合 ```）：
  这是项目里"可直接使用的提示词"包装格式（典型例：`prompts/ingestion/原始资料规范化.md` line 14-117）→ 提取该代码块**内部内容**作为 prompt 正文（不含 fence 行本身）
- **否则**（无 fence / 多对 fence / fence 不匹配）→ 使用整个文件正文作为 prompt 正文

## Step 3: 打印解析摘要 + 接管执行

打印一行：`运行 prompt: <相对工作目录的路径>`（让用户一眼确认解析正确）。

然后**把 prompt 正文当作本轮用户指令直接接管执行**——按 prompt 内的指引开始干活。

**输入字段补全**：

- 不少 prompt 末尾会列出"用户补充输入"清单（典型例：原始资料路径 / 书名 / 作者 / 语言 / 其他说明）
- 若 prompt 末尾存在此类清单**且** `$ARGUMENTS` 仅是 prompt 选择器（没附带这些字段）→ **先列出待补字段 + 一行示例格式，等用户回复再开干**，不要擅自推断 / 留空走默认值
- 若 `$ARGUMENTS` 已经在 prompt 选择器之外附带了输入信息（例如 `/run-prompt 原始资料规范化 path=/tmp/book.epub title=测试`）→ 直接代入对应字段执行

## 限制

- **不修改 prompt 文件本身**——本 skill 只读 + 执行 prompt 内容，不写回该文件
- **不递归触发 /run-prompt**——被加载的 prompt 自己不许在执行中再 `/run-prompt` 别的文件；如果 prompt 流程要分支到别的 prompt，应该走显式步骤（read + 跟随）而非嵌套触发
- **不 commit / 不 push / 不改 git 状态**——本 skill 的工作止于"加载并按 prompt 执行"；commit / push 等 git 动作只能由 prompt 内部明确要求时才发生（且按那个 prompt 自己的规则做）
- **不绕过 prompt 内的安全 / 范围约束**——例如 `prompts/ingestion/原始资料规范化.md` 明确 "不要写入 `works/` / `users/`"，本 skill 加载该 prompt 后必须遵守，不许借口"被 /run-prompt 调用所以不算"

---

**镜像约束**：本文件和 `.agents/skills/run-prompt/SKILL.md` 的 YAML frontmatter + 正文（从一级标题 `# /run-prompt` 起到本段之前）**逐字一致** — 任一侧修改必须在同 commit 内镜像到另一侧。本镜像约束段是两侧唯一允许差异的部分（路径互引）。
