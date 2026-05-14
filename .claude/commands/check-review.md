# /check-review — 复核 review 报告

对 `logs/review_reports/` 下指定模型**最近一次** review 报告做"真实性复核 + 方案设计"。**不改代码**，只确认每条 finding / risk / open question 是否真实存在，并给出落地方案草稿；用户确认细节后再用 `/go` 执行。

`$ARGUMENTS` = 模型筛选关键字，**可选**。映射规则：
- 缺省（不传参） → 不按模型过滤，直接取目录下**时间戳最新**的一份
- `claude` / `opus` / `sonnet` / `haiku` → 同义别名；匹配 slug 以 `opus-` / `sonnet-` / `haiku-` 开头的报告（Claude 家族产出视为同一来源）
- `codex` / `gpt` → 同义别名；匹配 slug 为 `codex` 或以 `gpt-` 开头的报告（codex 与 gpt 系列产出视为同一来源）
- `gpt-5`、`opus-4-7` 等具体 slug → 精确匹配
- 有参数但无匹配：报错，列出 `logs/review_reports/` 下已有的 model slug 供选择

## 0. 选文件

1. 枚举 `logs/review_reports/` 下所有 `{YYYY-MM-DD_HHMMSS}_{model}_{slug}.md`
2. 按 `$ARGUMENTS` 映射规则过滤（无参数则跳过过滤）
3. 按时间戳降序取**最新一份**（只取 1 份，不合并多份）
4. 打印："选中：`{filename}`（模型：{model}，生成时间：{timestamp}）"
5. 若有参数但无匹配：报错并列出目录下所有 model slug 及最近一份的时间戳
6. 若目录为空：报错并停手

## 1. 通读报告

完整读选中的报告；把 `Findings`（按 High / Medium / Low）、`Open Questions / Ambiguities`、`Alignment Summary`、`Residual Risks`、建议落地顺序逐条拆成条目清单。**不略读、不跳过 Low**。

## 2. 加载真相来源

- `ai_context/` 核心文件：conventions / requirements / current_status / architecture / decisions（如本项目 `ai_context/` 结构不同，则读所有 `.md` 文件作为兜底）
- `docs/requirements.md`、`docs/architecture/`
- 报告中引用的代码文件 + 行号：直接读当前代码，不要依赖报告里的节选
- 若报告时间戳较早、期间有 commit：`git log --since={报告时间戳} --oneline` 快速扫一眼，识别可能已修复的条目

## 3. 逐条复核

对每条 finding / risk / open question，产出：

- **复核结论**：`真实` / `部分真实` / `已失效`（已修复 / 误判 / 版本不一致）
- **证据**：引当前代码 / 文档的具体文件 + 行号，直接确认或反驳报告描述；区分"直接证据"与"推断"
- **影响评估**：是否仍影响当前主线；严重性是否需要调整（升 / 降 / 保留），并说明理由
- **方案草稿**（仅对"真实 / 部分真实"）：
  - 改哪个文件 / 函数 / 文档节 / schema 字段 / prompt 段
  - 改动边界（**不要顺带重构 / 扩范围**）
  - 风险点与回退方式
  - 跨文件连带更新：对照 `ai_context/conventions.md` 的 "Cross-File Alignment" 段列出（该段不存在则跳过本项）
- **依赖顺序**：与其他 finding 的方案之间是否有依赖、是否可合并成一个 commit
- **推迟 / 驳回**：明说"本轮不做"并写理由（登记 `docs/todo_list.md` 是下一步 /go 的事，这里只标记）

## 4. 输出结构

输出 markdown（**不落盘、不改代码、不提交**）：

1. `Source Report`：文件路径、报告模型、生成时间戳
2. `Per-Finding Review`：逐条带复核结论 / 证据 / 方案草稿
   - **强制沿用 source report 的 finding ID**（`H1` / `M1` / `L1`...）；source report 若缺 ID 则按其顺序补编号并在本轮报告说明 "ID 由本次复核回填"。复核后**保留同 ID**——即使严重度调整或合并，原 ID 不重排（撤回的标 "撤回"，合并的标 "合入 H1"）
3. `Revised Priority`：按复核后的严重度重排（仍引用原 ID，不改名）
4. `Proposed Execution Plan`：本轮建议做哪些、commit 拆分、先后顺序（按 ID 引用）
5. `Deferred / Rejected`：推迟或驳回的条目及原因（按 ID 引用）
6. `Open Questions for User`：需用户拍板的分歧点；每条编号 `OQ1` / `OQ2`...
7. `Recommendations`
   - **仅供参考，用户拍板优先**。给出每条建议前先过三问自检：
     1. **必要吗** —— 不修会怎样？只是看着不顺眼 / 强迫症 → 倾向"跳过"或"留 todo"
     2. **能更简单吗** —— 能改 3 行解决就别抽 helper / 加层 / 加配置 / 加 flag
     3. **超出 source report scope 吗** —— 顺手改的"相关项"是不是已经溢出本轮目标
   - 一段 flat list：每条 finding ID（沿用原 ID）+ 每条 OQ 给"建议{修 / 留 todo / 跳过}：{一句话理由 / 推荐方案}"

## 5. 等待确认

输出后**停手**。不要进入 `/go`、不要写 log、不要改文件；等用户逐条确认 / 调整方案后再执行。

## 约束

- 这是复核，不是二次 review；不要在报告之外新增 finding（除非报告明显漏掉了与其同一根因的连带问题，需标注"报告外补充"）
- 不要因为报告写得模糊就盲信，也不要无证据就驳回；每条结论都要落到文件 + 行号
- 不同模型的判断差异本身是信号：若你的复核结论与报告显著不同，明说分歧点，让用户裁决

---

**镜像约束**：本文件和 `.agents/skills/check-review/SKILL.md` 正文保持同步——任一侧修改必须在同 commit 内镜像到另一侧。`.agents/skills/check-review/SKILL.md` 额外带 YAML frontmatter（`name` / `description`），正文（从一级标题 `# /check-review` 起往下）与本文件**逐字一致**。
