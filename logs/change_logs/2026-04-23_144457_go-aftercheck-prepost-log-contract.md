# go-aftercheck-prepost-log-contract

- **Started**: 2026-04-23 14:44:57 EDT
- **Branch**: master (via worktree `/tmp/persona-engine-master/`)
- **Status**: PRE

## 背景 / 触发

本 session 原本是 /monitor 跟踪 `extraction/<work_id>` 的抽取进程。进程在我盲区内跑崩（S003 `char_support:<character_a>` 撞 `error_max_turns=50`）+ orchestrator finally 的 `checkout_master` 因 6 份 baseline 脏而中止，工作树卡在 extraction 分支。

用户由此提出对 `/go` 和 `/after-check` 的协作机制升级：

> 把讨论 / 需求 / 结论在最最开始就先记录进 log 文件，然后再去落实，这样后面复查的时候，强制要求参考这个 log 文件去查看是否对齐。复查结束后，再重新更新这个 log 文件，添加更新后的状态。

经过几轮对齐，用户又补充：

1. /after-check 要分两部分：**(1) 原始需求的落实情况**（对账）+ **(2) 有没有影响到其他文件，产生 bug/冲突/不一致**（扩散）
2. /after-check 不仅要更新 log，还要**在对话中直接告知用户完整报告**，让用户可以在对话中做决定；log 只存摘要 + 状态，避免 log 爆炸

## 结论与决策

把 `docs/logs/` 从"事后单时点记录"升级为**"PRE 登记 → POST 更新 → REVIEW 追加"三时点契约**，作为 `/go` 和 `/after-check` 的对齐锚点。

### /go 新流程（9 步）

| # | 步骤 | 变化 |
|---|------|------|
| 0 | 环境 & 隔离 | 不变 |
| **1 NEW** | **PRE log 登记** | 创建 `docs/logs/{YYYY-MM-DD}_{HHMMSS}_{slug}.md`，写入"背景 / 结论与决策 / 计划动作清单 / 验证标准 / 状态=PRE"；**写完 log 再动任何代码** |
| 2 | requirements | 原 1 |
| 3 | 核心实现 | 原 2 |
| 4 | 轻量测试 | 原 3 |
| 5 | 文档对齐 | 原 4 |
| 6 | 全库 review | 原 5 |
| **7 CHANGED** | **POST log 更新** | 更新同一份 log：已落地变更 / 与计划差异 / 验证结果 / 状态=DONE\|BLOCKED |
| 8 | Git commit | 原 7 |
| 9 | 分支同步 | 原 8 |

执行中发现偏离计划 → 在 log 里加 `## 执行偏差` 段落记新决定，**不默默改**。

### /after-check 新流程（双轨）

| # | 步骤 | 变化 |
|---|------|------|
| 0 | 界定范围 | 不变 |
| **0.5 NEW** | **强制加载 intent 基线** | `$ARGUMENTS` 传 slug → 精确匹配；否则取 `docs/logs/` 按 filename 时间戳最新的一份；读 PRE 段；log 缺失 → 标"intent 基线缺失"继续（轨 1 跳过） |
| 1 | Cross-File Alignment 对照 | 保留 |
| 2 | 并行 sub-agent 双轨审计 | 三线（规范/实现/产物）各自同时承担双轨 |
| 3 | 重点检查项 | 保留 |
| **4 CHANGED** | **对话输出完整双轨报告** | 轨 1 对账表 + 轨 2 Findings + Open Questions + Alignment Summary + Residual Risks。**这是用户决策的主要界面** |
| **5 NEW** | **回写 log（摘要版）** | 追加到同一份 log：复查结论摘要 + 轨 1/2 计数 + 复查时状态 + "详见对话"引用。log 不贴全文 |
| 6 | 等待确认 | 原 Step 5 |

双轨定义：
- **轨 1 — 原始需求落实情况**（对账）：用 PRE log 的"计划动作清单 + 验证标准"逐项核对，列 Missed Updates（对账差集 ∪ Cross-File Alignment 差集）
- **轨 2 — 影响扩散 / 计划外副作用**：用 intent 圈定 scope 后向**计划之外**的文件扩散找冲突 / bug / 歧义 / 残留旧逻辑 / README 漂移 / ai_context 漂移

intent 基线缺失时，轨 1 跳过并标注"无 PRE log，无法对账"；轨 2 正常跑。

### 状态语义

log 复查时状态三档：
- **REVIEWED-PASS** = 轨 1 全落实 且 轨 2 无 High/Medium
- **REVIEWED-PARTIAL** = 轨 1 有缺口 或 轨 2 有 Medium，无 High
- **REVIEWED-FAIL** = 轨 1 大面积未落实 或 轨 2 有 High

### 迁移策略

- 历史 log **不动**
- 新流程从本次改完后下一次 /go 生效
- 本次改动（元应用）**手工走新流程的精神**：先手写本 PRE log，再改 4 份文件 + 1 份 conventions.md，再 POST 更新

## 计划动作清单

1. `.claude/commands/go.md` — 把 9 步流程替换进去，Step 1 新增 PRE log 登记子步骤 + 正文模板；Step 7 替换"写 log"为"POST log 更新"；renumber 2–9；镜像约束段落保留
2. `.agents/skills/go/SKILL.md` — 正文与 `.claude/commands/go.md` 逐字同步；frontmatter 的 `description` 微调反映 PRE/POST 新流程
3. `.claude/commands/after-check.md` — 新增 Step 0.5（加载 intent 基线）+ Step 5（回写 log）；Step 4 改为"对话输出完整双轨报告"；约束段的"只读不写"例外加上"log 摘要回写"
4. `.agents/skills/after-check/SKILL.md` — 正文同步；frontmatter description 微调反映双轨 + 回写 log
5. `ai_context/conventions.md` — §Logging 从单时点改为三时点契约（PRE / POST / REVIEW）；Cross-File Alignment 表新增一行："/go 或 /after-check 触发的改动 → docs/logs/ 的 PRE/POST/REVIEW 三段必须齐"
6. 本 log 文件（本次元应用自身的产物）

## 验证标准

- [ ] 4 份 skill 镜像文件正文（从 `# /go` 或 `# /after-check` 起往下）**逐字一致**（`diff` 除 frontmatter 外无差异）
- [ ] `.agents/skills/*/SKILL.md` 两份带 YAML frontmatter 合法（`name` / `description`）
- [ ] `ai_context/conventions.md` §Logging 更新后，旧"单时点 log"描述无残留
- [ ] Cross-File Alignment 表新增行存在
- [ ] 新 skill 正文中引用的 log 文件模板字段（背景 / 结论与决策 / 计划动作清单 / 验证标准 / 状态 / 已落地变更 / 与计划差异 / 验证结果 / 复查结论 / 复查时状态）命名一致，无错别字
- [ ] 本 log 文件的 POST 段在 /go 结束时已填写，状态设为 DONE
- [ ] `grep -rn "旧 \| legacy \| 已废弃 \| 原为"` 在本次改动文件里无残留（policy 合规）
- [ ] 无真实书名 / 角色名 / 剧情词串混入 skill 或 conventions.md
- [ ] commit 干净，非 master 分支按 Step 0 策略处理

## 执行偏差

无。两个细节登记为 POST 阶段的补充，不算偏离：

1. 额外更新了 `ai_context/instructions.md` §Logging (critical) 段，把"单时点 log"改成 PRE/POST/REVIEW 三时点契约。这份文件原来没列在计划里，但它的描述已被新合同直接推翻，属于 Cross-File Alignment 的延伸。
2. `ai_context/conventions.md` §Post-Change Checklist 第 2 项从"写 log with HHMMSS"改为"PRE/POST 同一份 log"，属于 §Logging 段落重构的自然连带。

---

<!-- 以下由 POST 阶段填写 -->

## 已落地变更

在 `git worktree /tmp/persona-engine-master/`（master 副本）改动 6 份文件 + 1 份新 log：

| 文件 | 变更 |
|------|------|
| `.claude/commands/go.md` | 8 步 → 9 步；新 Step 1 "PRE log 登记"（含完整模板）；原 Step 6 "写 log" 改为新 Step 7 "POST log 更新"；renumber 2–9；末尾镜像约束段保留 |
| `.agents/skills/go/SKILL.md` | 正文与 `.claude/commands/go.md` 逐字同步；frontmatter `description` 从"8 步"改为"10 步"（9 步 Step + 环境）并点出 PRE/POST log 机制 |
| `.claude/commands/after-check.md` | 新 Step 0.5 "强制加载 intent 基线"；Step 1 改为 Cross-File Alignment 对照（不做差集对账）；Step 2 标"双轨审计"；新 Step 4 "对话输出完整双轨报告"（含 Markdown 模板）；新 Step 5 "回写 log 摘要"；原 Step 5 "等待确认" → Step 6；约束段加"只读 + 单写例外"；镜像约束段保留 |
| `.agents/skills/after-check/SKILL.md` | 正文与 `.claude/commands/after-check.md` 逐字同步；frontmatter `description` 重写反映双轨 + intent 基线 + log 回写 |
| `ai_context/conventions.md` | §Logging 从"每次写一份 log"改为 PRE/POST/REVIEW 三时点契约（含三段字段清单 + 契约要点 4 条）；§Cross-File Alignment 表新增一行 "/go or /after-check triggered change"；§Post-Change Checklist 第 2 项更新 |
| `ai_context/instructions.md` | §Logging (critical) 段落重写为三时点版本 |
| `docs/logs/2026-04-23_144457_go-aftercheck-prepost-log-contract.md` | **本次元应用的 PRE log，/go 全程贯穿**（本段为 POST 回写） |

## 与计划的差异

对比 PRE 的"计划动作清单"6 项：

- 1–5 项全部按计划落实
- 第 6 项（本 log 文件自身）按计划落实
- **额外落实**：`ai_context/instructions.md` §Logging (critical) 段（见"执行偏差"说明，属于 Cross-File Alignment 延伸，非真正偏离）

无其他增删改。

## 验证结果

- [x] **4 份 skill 镜像文件正文逐字一致** — `diff` 结果除末尾镜像约束指向句（设计性不对称，各自指向对方）外 0 差异；正文段逐字 identical
- [x] **`.agents/skills/*/SKILL.md` 两份带 YAML frontmatter 合法** — 两份 `name` / `description` 均存在，结构正确
- [x] **`ai_context/conventions.md` §Logging 旧"单时点 log"描述无残留** — 原文第 9 行 "Every meaningful change → write a log" 已被三时点契约完整替换；grep 确认
- [x] **Cross-File Alignment 表新增行存在** — conventions.md:54 "/go or /after-check triggered change → docs/logs/ 的 PRE / POST / REVIEW 三段按时点写齐"
- [x] **新 skill 正文引用的 log 模板字段命名一致** — 背景/触发、结论与决策、计划动作清单、验证标准、执行偏差、已落地变更、与计划的差异、验证结果、Completed、复查结论、复查时状态 等字段在 go/after-check/conventions 三处命名统一
- [x] **本 log 文件的 POST 段在 /go 结束时已填写** — 本段即是
- [x] **无"旧/legacy/已废弃/原为"残留误伤** — grep 命中的全部是规则定义文本（指导如何检查旧逻辑），不是残留旧内容
- [x] **无真实书名/角色名混入 skill 或 conventions.md** — grep 命中仅在 PRE log（docs/logs/ 按 conventions §Generic Placeholders 显式豁免）
- [ ] **commit 干净，非 master 分支按 Step 0 策略处理** — 下一步 Step 8 执行；当前主 working tree 仍在 `extraction/<work_id>` 且有 S003 未提交脏，本次在 worktree 改，不触碰主 working tree，Step 8 里在 worktree commit 后删 worktree，主 working tree 保持原状

## Completed

- **Status**: DONE
- **Finished**: 2026-04-23 15:38:27 EDT

---

<!-- 以下由 /after-check 填写 -->

## 复查结论

（/after-check 填写）

## 复查时状态

（/after-check 填写）
