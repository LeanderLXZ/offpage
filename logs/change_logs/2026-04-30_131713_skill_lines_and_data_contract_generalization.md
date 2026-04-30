# skill_lines_and_data_contract_generalization

- **Started**: 2026-04-30 13:17:13 ET
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

本会话连续四轮迭代了 `/go` / `/post-check` / `/full-review` 三个 skill：

1. `/post-check` Step 3 加入「风险线」（第 4 条审计线），区分「实现线（连得上吗）」vs「风险线（做的事对吗）」
2. `/post-check` Step 3 顶部加「轨 vs 线」一行解释（轨=审计视角×2 / 线=扫描分工×4，正交）
3. `/full-review` 工作方式同样新增「风险线」第 3 条
4. `/go` skill 重划 Step 3 / Step 6 / Step 7 职责：
   - Step 3 = 内容创作（把讨论结论第一次写进文档）
   - Step 6 = 跨文档对齐 + todo_list 维护（查漏补缺、不做内容创作）
   - Step 7 = 全库多线 review（4 条线并行；findings 不直接写 todo_list，只列「建议登记到 todo_list」清单）
   - 各 step 名字泛化（Step 0 中文化、Step 1 加 worktree 隔离副标题、Step 4 列出主要产物、Step 5 smoke / schema 校验、Step 6 / Step 7 / Step 8 重命名）

以上四轮都是会话内已逐条经用户确认 / 加固的迭代，工作区目前 dirty（6 文件未提交）。

本轮（第 5 轮）的触发：用户提问「`schemas/` 是不是本项目特有的？skill 想泛化是不是要改 schema 相关描述？」并对方案给出两条决策：

1. **路径**：`ai_context/skills_config.md` 新增 `## Data contract directories` 节（可空缺：很多项目没有独立 data-contract 目录）
2. **校验工具**：Step 5 不再写死 `jsonschema` 命令，改为泛化表述（按项目对应校验工具走）

## 结论与决策

**目标**：把 skills 文案里的 "schema" 偏置剥离，改为通过 `skills_config.md` 注入路径 + 泛化口径描述，使 skills 在没有 `schemas/` 目录的项目（如量化交易系统）也能直接复用。

**两层抽象**：

- **路径层**：在 `ai_context/skills_config.md` 新增 `## Data contract directories` 节（覆盖 schema / proto / openapi / pydantic models / SQL DDL 等数据契约目录）。每个 skill 引用该节而不是硬写 `schemas/`。该节可为 `(none)`，对应 step 自动 degrade
- **名词层**：`schema` 这个英文词保留（已是泛化术语），但首次出现处加一句"含 JSON Schema / proto / OpenAPI / Pydantic / SQL DDL 等"，让其他项目读到不觉得"这是别人的事"。Step 5 `jsonschema` 工具名改为"按项目对应校验工具"

**不改的**：

- skill 文案里 "schema" 这个词本身保留
- `ai_context/conventions.md` 的 Cross-File Alignment 表（提到 schema 是 generic 数据契约维度，本来就不偏置某一种）
- 本项目实际有的 `schemas/` 目录路径（仅在 skills_config.md 显式登记）

## 计划动作清单

- file: `ai_context/skills_config.md` → 在 `## Source directories` 之后、`## Example artifact directories` 之前 新增 `## Data contract directories` 节，登记本项目的 `schemas/` 路径
- file: `.claude/commands/go.md` → Step 0 引用清单加 `## Data contract directories`；Step 5 `jsonschema` 改泛化表述；Step 7 规范线把 `schemas/` 改为引用 skills_config.md 的节；frontmatter 描述里 "schema" 保留但配上下文
- file: `.agents/skills/go/SKILL.md` → 镜像同步以上改动（含 frontmatter `description` 字段同步）
- file: `.claude/commands/post-check.md` → Step 0 引用清单加 `## Data contract directories`；Step 3 规范线把 `schemas/` 改为引用 skills_config.md 节；Step 4 检查项 "schema" 字眼加首次出现注释
- file: `.agents/skills/post-check/SKILL.md` → 镜像同步
- file: `.claude/commands/full-review.md` → Step 0 引用清单加 `## Data contract directories`；工作方式列表把 `schemas/` 改为引用 skills_config.md 节；规范线 / 重点检查项里的 schemas 引用同样改；frontmatter 描述加上下文
- file: `.agents/skills/full-review/SKILL.md` → 镜像同步

## 验证标准

- [ ] `ai_context/skills_config.md` 含 `## Data contract directories` 节，标题精确匹配，`schemas/` 路径登记
- [ ] 三对 skill 文件（go / post-check / full-review）正文 byte-for-byte 镜像一致：`diff <(.claude 版本正文) <(.agents 版本正文)` 退出 0
- [ ] 三对 skill 文件里**不再有硬写的 `schemas/` 路径作为扫描目标**（出现在示例 / 历史描述 / Cross-File Alignment 抄录里则保留），统一引用 `skills_config.md` `## Data contract directories`
- [ ] Step 5 不再硬写 `jsonschema` 命令，改为按项目实际工具的泛化表述
- [ ] grep `schemas/` 在三对 skill 文件里 0 命中（或仅命中"项目历史 / 示例"上下文，不命中扫描指令）
- [ ] `ai_context/conventions.md` 的 Cross-File Alignment 表如包含 "schema" 维度，仍保留（generic 数据契约，不偏置）

## 执行偏差

无（计划清单 7 个文件全数动到位；Step 1 就 dirty 工作区策略偏离表格规则，已在对话中说明并选择 main 原地，将上几轮 skill 编辑一并纳入 scope，不算计划偏差）。

<!-- POST 阶段填写 -->

## 已落地变更

合计动了 8 个文件（含 PRE log 自身，跨本轮 + 上几轮会话内连续 skill 编辑；本轮新增改动以 ★ 标注）：

- ★ `ai_context/skills_config.md` — 在 `## Source directories` 之后、`## Example artifact directories` 之前插入新节 `## Data contract directories`，登记 `schemas/`，附说明（含 JSON Schema / proto / OpenAPI / Pydantic / SQL DDL；`(none)` 时 degrade）
- ★ `ai_context/conventions.md` — Cross-File Alignment 表第 48 行 anchors 列表补 `data-contract`
- `.claude/commands/go.md` + `.agents/skills/go/SKILL.md`（镜像）：
  - Step 0 引用清单加 `## Data contract directories`（★ 本轮）
  - Step 2 PRE 模板验证标准示例 `jsonschema` 改为 `数据契约校验`（★ 本轮）
  - Step 3 → "把讨论结论落到文档（内容创作）"：内容创作专用，写入禁止串改、连带感先记 PRE 偏差段（上几轮）
  - Step 4 → "实现代码 / schema / prompt / 配置"（上几轮）
  - Step 5 → "Smoke 测试 + 数据契约校验"：泛化校验工具表述（★ 本轮）
  - Step 6 → "跨文档对齐 + todo_list 维护"：查漏补缺式同步、ai_context durable + todo_list 归档+Index 刷新；新规则"Step 7 review 期间发现的新问题不在本步登记"（上几轮）
  - Step 7 → "全库多线 review（并行）"：4 条线（规范/实现/风险/结构），Findings 双轨处理（小问题发现即修，大问题"建议登记到 todo_list"，不自写）（上几轮）
  - Step 7 规范线 `schemas/` → 引用 skills_config.md 节（★ 本轮）
  - Step 0 / Step 1 / Step 5 / Step 8 名字泛化（上几轮）
  - frontmatter description 11 步顺序串同步（上几轮）
- `.claude/commands/post-check.md` + `.agents/skills/post-check/SKILL.md`（镜像）：
  - Step 0 引用清单加 `## Data contract directories`（★ 本轮）
  - Step 3 顶部加「轨 vs 线」一行解释（上几轮）
  - Step 3 新增第 3 条 风险线（上几轮）
  - Step 3 规范线 `schemas/` → 引用 skills_config.md 节（★ 本轮）
- `.claude/commands/full-review.md` + `.agents/skills/full-review/SKILL.md`（镜像）：
  - Step 0 引用清单加 `## Data contract directories`（★ 本轮）
  - 工作方式列表 / 规范线 / 实现线 fallback exclusion / 重点检查项 把 `schemas/` 全数引用 skills_config.md 节（★ 本轮）
  - 工作方式审计线列表新增第 3 条 风险线（上几轮）
- ★ `logs/change_logs/2026-04-30_131713_skill_lines_and_data_contract_generalization.md` — 本轮 PRE/POST log

## 与计划的差异

- 计划清单的 7 个改动文件全数命中
- 额外动到 1 个文件：`ai_context/conventions.md` Cross-File Alignment 表第 48 行——Step 6 跨文档对齐校验时发现的合理补漏（计划里没列，但属于"新增 skills_config.md 节必带的 anchor 同步"），登记在此

## 验证结果

- [x] `ai_context/skills_config.md` 含 `## Data contract directories` 节，`schemas/` 路径登记 — 已确认（Read 验证 + ls schemas/ 验证目录在）
- [x] 三对 skill 文件正文 byte-for-byte 镜像一致 — 三对 diff = 0
- [x] 三对 skill 文件不再硬写 `schemas/` 路径 — `grep -ln 'schemas/' .claude/commands/*.md .agents/skills/*/SKILL.md` 无命中
- [x] Step 5 不再硬写 `jsonschema` 命令 — Step 5 改为按项目工具的泛化表述+多种例子（jsonschema 仅作为 JSON Schema 的工具示例之一）
- [x] grep `schemas/` 在三对 skill 文件 0 命中 — 已通过
- [x] `ai_context/conventions.md` Cross-File Alignment 表保留 schema 维度并新增 data-contract anchor

## Completed
- **Status**: DONE
- **Finished**: 2026-04-30 13:37:35 ET
