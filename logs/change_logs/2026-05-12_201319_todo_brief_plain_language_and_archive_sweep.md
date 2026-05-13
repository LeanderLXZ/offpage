# todo_brief_plain_language_and_archive_sweep

- **Started**: 2026-05-12 20:57:01 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

会话上文用户问 `T-PHASE2-RECOVERY-RESET-FLAG` 是干啥，我判断这是过度工程（决策 #56 hard stop 路径已落地，daemon 撞 hard stop 概率本来就极低，再为它写 flag + 4 个 doc 同步性价比不够），用户认同要扔。然后用户提了两个连带需求：

1. **顺手再看下其他 todo 有没有可以扔的**——本会话上文我盘了一遍 11 条 brief，发现以下三条也是"提醒已存在于其他渠道、todo 行为只是冗余索引"：
   - `T-SIMULATION-MODE-MARKER`：`[simulation_runtime_mode]` 占位符已写在 CLAUDE.md / AGENTS.md 顶部 Worker-Mode Short-Circuit 段，开始写 simulation 时第一眼就看到
   - `T-CODEX-STDIN`：codex backend 未启用 + 本机无 codex CLI，代码 `llm_backend.py::CodexBackend.run` 顶上已有 NOTE 注释作为提醒
   - `T-CODEX-RATE-LIMIT`：同上同环境同提醒形式
2. **简介撰写要求改写**——index 里的 Brief 当前充满 schema 路径、函数名、决策编号、行号，用户希望"用尽量简单的话来描述问题，能让人容易听懂"。同时让我审查 `/todo` 和 `/todo-add` 两个 skill 文件本身要不要同步改。

会话中我已确认：

- **brief 风格的 SoT 在 `docs/todo_list.md` 顶部 File guide 内的"简介撰写要求"小节**（line 187 附近）
- `/todo` skill 只渲染 index，不写内容——无需改
- `/todo-add` skill 写 brief 时**指向 `docs/todo_list.md` "Index maintenance" 段作为唯一权威**，不在 skill 里复述规则——也无需改

因此本次落盘只动 `docs/todo_list.md` + `docs/todo_list_archived.md` 两份文件（加本 log），两个 skill 自动跟随。

## 结论与决策

**归档动作（4 条 → Abandoned）**：

| ID | 废弃原因 |
|---|---|
| `T-PHASE2-RECOVERY-RESET-FLAG` | 过度工程。决策 #56 hard stop 路径已落地、daemon 撞这条概率极低（baseline 抽错本来罕见 + 在 daemon 模式 + 已有 phase 3 committed 三重叠加），为它写 store_true flag + cleanup 路径 + 4 个 doc 同步性价比不够。手动 `rm -rf + commit` 是更小的 runbook；真撞上了切前台跑 `[y/N]` 也行。等真实需求验证后再立项。|
| `T-SIMULATION-MODE-MARKER` | 冗余提醒。`[simulation_runtime_mode]` 占位符已写在 `CLAUDE.md` / `AGENTS.md` 顶部 "Worker-Mode Short-Circuit" 段——simulation runtime 真开工时一定会读这两份入口文件、第一眼看到占位符就知道要注入；todo 行为只是同一信息的二次索引。真到要做时 1 行 `--append-system-prompt` 改动量微不足道，不需要 todo 提醒。|
| `T-CODEX-STDIN` | 冗余提醒。codex backend 未启用（默认 `--backend claude`），本机连 codex CLI 都没装无法实测。`automation/persona_extraction/llm_backend.py::CodexBackend.run` 顶上已有 NOTE 注释（"codex CLI still receives the prompt via argv ..."）作为提醒——切 codex 时一定会读该文件、注释自动跳出。todo 在 Discussing 段躺着只是噪声。|
| `T-CODEX-RATE-LIMIT` | 冗余提醒。同 T-CODEX-STDIN：codex backend 未启用、本机无 codex CLI 无法实测、代码侧已有相关注释。切 codex 时一并修。|

留下 9 条：1 In Progress + 2 Next + 6 Discussing。

**简介撰写要求改写**：

原 spec（line 187 附近）：

> 首句必含核心信息；再补 1–2 句关键背景（痛点 / 关键文件 / 实测数据 / 触发原因之一），让用户不点开正文也知道这是个什么事、为什么值得做。**总长 ≤ 150 字**——超过宁可砍背景也要保住首句。

新 spec：

> 用大白话说清"这是要解决什么问题"和"为什么值得做"。**避免堆砌代码名 / 函数名 / schema 路径 / 行号 / 决策编号**——除非那本身就是问题的核心，否则换成普通说法（"现在 phase 2 抽错了不会自动修，得手动重跑"，而不是"phase 2 baseline production 整体接入 repair_agent lifecycle"）。读者不点开正文也能听懂这是干啥、为啥要做。**总长 ≤ 150 字**——超过先砍细节，保住"是啥 + 为啥"。

**保留 9 条的 brief 全部重写为大白话**（详见 Step 3 改动清单的"逐条新 brief"段）。

**不改的**：

- 正文条目（"### [T-XXX]" 块）字段，包括上下文 / 改动清单 / 完成标准 / 依赖 / 待决策项——这些是工程级细节，给真开工时用，不是给"一眼看清单"用。本轮只调 index 表里的简介列。
- `/todo` 和 `/todo-add` 两个 skill 文件——SoT 已在 todo_list.md，skill 已指向那。
- `ai_context/decisions.md` / `next_steps.md` / `current_status.md` / `handoff.md`——本轮只动 todo 体系内部的归档与简介风格，不产生新 durable 决策、不影响项目状态快照、不影响下一会话的接力上下文。

## 计划动作清单

- file: `docs/todo_list.md`
  - 改 line 187 附近"简介撰写要求"段为新 spec（保留 ≤ 150 字硬上限，加"避免专业术语堆砌"具体禁忌 + 反例 + 正例）
  - **删除** 4 条归档项的 index 行（PHASE2-RECOVERY-RESET-FLAG 在 Next 段；SIMULATION-MODE-MARKER + CODEX-STDIN + CODEX-RATE-LIMIT 在 Discussing 段）
  - **删除** 4 条归档项的正文 `### [T-XXX]` 块（连带前后多余 `---` 分隔）
  - 保留 9 条 index 行的 Brief 列**全部重写**为新 spec 风格的大白话（In Progress 的 Title 列不动，那是简短中文短语，不是 Brief）
  - 刷新 Total 行：`Total: 13 → 9 — 🟢 In Progress 1 ｜ 🟡 Next 2 ｜ ⚪ Discussing 6`
- file: `docs/todo_list_archived.md`
  - 在 `## Abandoned` 段顶部追加 4 条瘦身条目（按归档格式：标题 · 废弃于 2026-05-12 + 1-2 句废弃原因 + 关联 log 链接）
  - 排序：4 条同日（2026-05-12）按 ID 字母序——CODEX-RATE-LIMIT < CODEX-STDIN < PHASE2-RECOVERY-RESET-FLAG < SIMULATION-MODE-MARKER

## 验证标准

- [ ] `docs/todo_list.md` index 段 4 条归档 ID 不再出现，9 条保留 ID 各出现一次
- [ ] `docs/todo_list.md` 正文段 4 条归档 ID 的 `### [T-XXX]` 块不存在；9 条保留 ID 的 `### [T-XXX]` 块依然完整
- [ ] `docs/todo_list_archived.md` `## Abandoned` 段含 4 条新归档（标题 + 废弃原因 + log 链接齐全）
- [ ] index 段 Total 行数字与三张子表实际行数一致（1 + 2 + 6 = 9）
- [ ] 9 条新 brief 全部 ≤ 150 字 且 不含 schema 文件路径 / 函数名 / 决策编号 / 行号等专业术语（除非那是问题核心）
- [ ] `/todo` skill 渲染索引正常（不解析正文、只读 index 段）：在新 SoT 上运行心智 dry-run 通过
- [ ] `grep -c "T-PHASE2-RECOVERY-RESET-FLAG\|T-SIMULATION-MODE-MARKER\|T-CODEX-STDIN\|T-CODEX-RATE-LIMIT" docs/todo_list.md` = 0
- [ ] `grep -c "T-PHASE2-RECOVERY-RESET-FLAG\|T-SIMULATION-MODE-MARKER\|T-CODEX-STDIN\|T-CODEX-RATE-LIMIT" docs/todo_list_archived.md` = 4

## 执行偏差

执行中追加：Step 6 跨文档对齐发现 3 处 live-doc 还在引用 4 条归档 ID 中的 `T-PHASE2-RECOVERY-RESET-FLAG`——`ai_context/decisions.md:494-496` + `decisions.md:516-517` + `docs/architecture/extraction_workflow.md:220-222`，全是"二期 todo `T-PHASE2-RECOVERY-RESET-FLAG`"形式的前向指针。归档后这些指针变成悬挂引用。已在 Step 6 一并修订：3 处"二期 todo" 指针改写为"破坏性动作走人工执行"的纯描述（不再指向不存在的 todo）；`decisions.md:531` 的 todo 登记列表里删掉 `T-PHASE2-RECOVERY-RESET-FLAG`，只保留仍 live 的 `T-LIGHTNOVEL-SCHEMA-ONEOF`。其余 3 条归档 ID 在 live-docs 里无引用（仅 `logs/review_reports/` 历史快照保留原文，按惯例不动）。

<!-- POST 阶段填写 -->

## 已落地变更

- `docs/todo_list.md`：
  - line 187 附近"简介撰写要求"段改为新 spec（强调大白话、避免代码名 / 函数名 / schema 路径 / 行号 / 决策编号等专业术语堆砌，加反例 + 正例，保留 ≤ 150 字硬上限）
  - index 段 Next 子表 3 → 2 行（删 `T-PHASE2-RECOVERY-RESET-FLAG`）；Discussing 子表 9 → 6 行（删 `T-CODEX-STDIN` / `T-CODEX-RATE-LIMIT` / `T-SIMULATION-MODE-MARKER`）
  - 保留 9 条 brief（In Progress 1 + Next 2 + Discussing 6）全部按新 spec 重写为大白话
  - Total 行：`13 → 9，Next 3 → 2，Discussing 9 → 6`
  - 正文段 4 条归档项的 `### [T-XXX]` 块连带 `---` 分隔符一并删除
- `docs/todo_list_archived.md`：`## Abandoned` 段顶部追加 4 条新归档（标题 · 废弃于 2026-05-12 + 1 段废弃原因 + 关联本 log 链接），按 ID 字母序：CODEX-RATE-LIMIT < CODEX-STDIN < PHASE2-RECOVERY-RESET-FLAG < SIMULATION-MODE-MARKER；与既有 2026-04-30 起的归档段用 `---` 分隔
- `ai_context/decisions.md`：3 处微调——line 494-496 删 "二期 todo `T-PHASE2-RECOVERY-RESET-FLAG`" 指针改为纯描述（撞 hard stop 后人工执行 / 切前台）；line 516-517 删 "(二期)" 改为 "破坏性动作走人工执行更稳"；line 531 todo 登记列表只保留 `T-LIGHTNOVEL-SCHEMA-ONEOF`，删 PHASE2-RECOVERY-RESET-FLAG
- `docs/architecture/extraction_workflow.md`：line 220-222 同样删 "二期 todo `T-PHASE2-RECOVERY-RESET-FLAG`" 指针改为纯描述
- `logs/change_logs/2026-05-12_201319_todo_brief_plain_language_and_archive_sweep.md`：本 log

## 与计划的差异

PRE 计划只动 `docs/todo_list.md` + `docs/todo_list_archived.md` 两份文件。Step 6 跨文档对齐时发现 3 处 live-doc 仍引用 `T-PHASE2-RECOVERY-RESET-FLAG` 作为"二期 todo"前向指针——归档后变成悬挂引用，必须一并修。执行中追加 `ai_context/decisions.md` + `docs/architecture/extraction_workflow.md` 两份的微调。这是符合本次 intent（todo 归档后清理悬挂指针）的自然延伸，不是 scope creep。

## 验证结果

- [x] `docs/todo_list.md` index 段 4 条归档 ID 不再出现，9 条保留 ID 各出现一次 — `grep -c` confirmed 0 / 9 occurrences
- [x] `docs/todo_list.md` 正文段 4 条归档 ID 的 `### [T-XXX]` 块不存在；9 条保留 ID 的 `### [T-XXX]` 块依然完整 — `grep "^### \[T-"` 列出 9 条全部齐全
- [x] `docs/todo_list_archived.md` `## Abandoned` 段含 4 条新归档（标题 + 废弃原因 + log 链接齐全） — 已验证 4 条按字母序追加在原 2026-04-30 段前 + `---` 分隔
- [x] index 段 Total 行数字与三张子表实际行数一致（1 + 2 + 6 = 9） — Python 脚本核对：In Progress 1 / Next 2 / Discussing 6 / Total 9 ✓
- [x] 9 条新 brief 全部 ≤ 150 字 且 不含 schema 文件路径 / 函数名 / 决策编号 / 行号等专业术语（除非那是问题核心） — 字数核对：41 / 127 / 110 / 118 / 142 / 131 / 122 / 140 / 139 全 ≤ 150；术语扫描人工通过
- [x] `/todo` skill 渲染索引正常（不解析正文、只读 index 段）：在新 SoT 上运行心智 dry-run 通过 — table 格式 + Total 行 + blockquote 全保留，skill 渲染路径不变
- [x] `grep -c "T-PHASE2-RECOVERY-RESET-FLAG\|T-SIMULATION-MODE-MARKER\|T-CODEX-STDIN\|T-CODEX-RATE-LIMIT" docs/todo_list.md` = 0 ✓
- [x] `grep -c "T-PHASE2-RECOVERY-RESET-FLAG\|T-SIMULATION-MODE-MARKER\|T-CODEX-STDIN\|T-CODEX-RATE-LIMIT" docs/todo_list_archived.md` = 4 ✓
- [x] live-docs（`ai_context/` + `docs/architecture/` 排除 logs/）对 4 条归档 ID 的引用清零 — 全库 grep 仅 review_reports/ 历史快照保留（按惯例不动）

## Completed

- **Status**: DONE
- **Finished**: 2026-05-12 21:04:01 EDT
