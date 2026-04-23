# /go — 方案落盘

按上文讨论执行；某步本次 N/A 就明说"跳过 Step X"。`$ARGUMENTS` 存在即本次改动焦点。

## 0. 环境 & 隔离
- `git branch --show-current`；项目硬规则：代码 / schema / prompt / docs / ai_context 变更**先进 master**，其他分支通过 `git merge master` 同步；大架构更改尤其要守。
- `pgrep -af persona_extraction` + 看 `works/*/analysis/progress/*.pid`；评估本次改动会不会让进程崩。
- 有冲突：`git worktree` 开 master 副本改；或推迟。
- 明确说出策略："在 master / worktree / 等进程结束"。

## 1. PRE log 登记（先登记再动手）
**任何代码 / schema / prompt / docs / ai_context / skill 改动之前**，先创建本次改动的 log 文件并写入 PRE 段。这是 `/after-check` 的 intent 基线来源，强制。

- 文件名：`docs/logs/{YYYY-MM-DD}_{HHMMSS}_{slug}.md`。HHMMSS 强制，`TZ='America/New_York' date '+%Y-%m-%d_%H%M%S'` 获取；slug 语义化英文短名
- 回显路径给用户（一行 `LOG: docs/logs/...md`），便于后续 `/after-check` 显式引用

PRE 段必须包含：

```markdown
# {slug}

- **Started**: {YYYY-MM-DD HH:MM:SS EDT}
- **Branch**: {/go 进入时的工作分支}
- **Status**: PRE

## 背景 / 触发
{会话上下文、用户原始需求、上游讨论链条摘要}

## 结论与决策
{/go 进来时已拍板的方案：选了哪个方向、改什么、不改什么}

## 计划动作清单
- file: {path} → {改动要点}
- ...

## 验证标准
- [ ] {如 Import 无报错}
- [ ] {如 jsonschema 通过}
- [ ] {如 grep 残留为 0}
- ...

## 执行偏差
（执行中追加；无偏差则写"无"）
```

写完 PRE 段**再进入 Step 2**。中途发现偏离计划 → 在 log 里追加 `## 执行偏差` 段落记新决定，**不默默改**。

## 2. 需求文档 `docs/requirements.md`
更新相关节，含流程图 / 示例。**新增流程图 / 示例仅当现有内容无法覆盖新逻辑时**，避免冗余。**不出现真实书名 / 角色 / 剧情**，用通用占位符；描述只写当前设计，不写"旧 / legacy / 已废弃 / 原为"。同步 `ai_context/requirements.md` + `decisions.md`。

## 3. 核心实现
按讨论改 schema、prompt template、架构代码、配置。对照 `ai_context/conventions.md` 的 Cross-File Alignment 表列出连带文件。

## 4. 轻量测试（仅有代码 / schema 变更时）
Import 检查 + 关键函数 smoke test；schema 改动跑 `jsonschema` 校验。有错立即修。

## 5. 文档对齐
同步 `ai_context/`（仅 durable truth）、`docs/architecture/`、相关 README。再查 `docs/todo_list.md`：新任务登记、已完成条目**清除**、状态变化更新。

## 6. 全库 review
并行扫描（可派 Agent）所有可能涉及的文件：需求、schema、代码、README、architecture、ai_context、prompts、目录结构。检查项：**残留旧逻辑、歧义、跨文件不一致、冲突、遗漏更新、bug、风险**；顺查有无混入真实书名或 legacy 字样。**发现即修**；太大则登记到 `docs/todo_list.md`。

## 7. POST log 更新（收尾前必填）
更新 **Step 1 创建的同一份 log**，追加 POST 段：

```markdown
<!-- POST 阶段填写 -->

## 已落地变更
{实际改了哪些文件、每份改了什么，文件 + 行号或 diff 摘要}

## 与计划的差异
{对比 PRE 的"计划动作清单"，新增 / 删除 / 修改了什么；无则写"无"}

## 验证结果
- [x] {PRE 验证标准 1} — {输出摘要}
- [ ] {PRE 验证标准 2} — {失败原因}
- ...

## Completed
- **Status**: DONE | BLOCKED
- **Finished**: {timestamp}
```

不要新建 log 文件；就地更新 PRE 段那份。

## 8. Git commit
`git status` 只剩本次改动；扫禁提路径（`sources/` 原文、数据库、embeddings、caches、真实 user packages）；message 风格对齐 `git log --oneline -10`；按逻辑单元分 commit；提交后 `git status` 确认干净，非 master 分支按 Step 0 策略回合。

## 9. 同步其他分支
`git branch --format='%(refname:short)'` 列出所有本地分支；对每个非 master 分支判断是否已含本次 master 改动（`git merge-base --is-ancestor master <branch>` → 0 即已同步）。未同步的分支：
- 若分支有正在运行的进程（如 `extraction/*`）或未完成工作：记录到 `docs/todo_list.md` 推迟同步，不强推
- 否则 `git checkout <branch> && git merge master`；冲突先停手，让用户决定；干净合并后 `git checkout master`
最后打印每个分支的同步状态（已同步 / 已合并 / 推迟原因）。

---

**镜像约束**：本文件和 `.agents/skills/go/SKILL.md` 正文保持同步——任一侧修改必须在同 commit 内镜像到另一侧。`.agents/skills/go/SKILL.md` 额外带 YAML frontmatter（`name` / `description`），正文（从一级标题 `# /go` 起往下）与本文件**逐字一致**。
