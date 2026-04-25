# extraction-disposable-and-phase4-remap

- **Started**: 2026-04-25 03:14:06 EDT
- **Branch**: main（worktree `../offpage-main`，主 checkout 留在 `extraction/我和女帝的九世孽缘`，clean）
- **Status**: DONE
- **LOG**: `logs/change_logs/2026-04-25_031406_extraction-disposable-and-phase4-remap.md`

## 背景 / 触发

会话上下文：

1. 用户提出问题：当前流程下 extraction 分支上每次失败 regen 都被 commit，长期会堆积"废 commit"占用空间。
2. 用户实际需求拆成两条：
   - **Need 1**：现在的 phase 1/2/3 产物 0 历史价值，要丢弃（重来）。
   - **Need 2**：将来 extraction → library 合并时只 merge 最终产物，不带历史 regen commit。
3. 我读了 `ai_context/`（conventions / architecture / current_status / decisions / instructions）后发现：
   - **Need 2 的 squash merge 策略已经写进 ai_context**（`decisions.md` #26 / `conventions.md` §Git / `architecture.md` §Git Branch Model），但**漏了一条隐含规则**——squash 完之后必须 `git branch -D extraction/{work_id}` + `git gc --prune=now` 才能让旧 regen commit 真正变 unreachable 并被回收。否则 extraction 分支只要存在，所有 regen blob 仍占盘。这条记为 **R1**。
   - **Phase 0 / Phase 4 产物本来就 git-ignored**（`works/*/analysis/chapter_summaries/`、`works/*/retrieval/scene_archive.jsonl`），所以"git 历史只 track phase 0 + 4"在物理上**已经成立**——git 里没有 phase 0 / 4 产物可以"保留"。Need 1 的 git scope 实际是删 phase 1/2/3/3.5 的 tracked 产物。
   - **Phase 4 的 stage 赋值是程序级的**——LLM 部分只依赖 chapter（split scenes + 抽 summary / time / location / characters / full_text），`stage_id` 和 `SC-S###-##` 里的 `S###` 是 chapter → stage_plan range 的程序映射。新 stage_plan 一出来，遍历 scene_archive.jsonl 重 map 即可，0 token 0 LLM。这是"extraction 分支可丢弃"的另一支撑事实。

## 结论与决策

本次 /go scope **只做 Need 2 的 doc 补全**，不动 extraction 分支数据：

- **R1 落入三处** durable truth：`decisions.md` #26 / `conventions.md` §Git / `architecture.md` §Git Branch Model，补一句 squash 后 `git branch -D` + `git gc --prune=now` 的流程。
- **Phase 4 remap 性质**写进 `architecture.md` §Automated Extraction Pipeline → Phase 4 描述里，作为一条架构性质（"stage assignment is program-cheap; remappable against new stage_plan without re-running per-chapter LLM"）。

**Need 1 单独走，不在本次 /go 范围**：原因是 extraction 分支上的破坏性数据删除需要逐路径 confirmation，不符合 /go 的 main-first + 一次问询模型。本次 /go 完成后会另行给出 `git ls-files` 实测的 phase 1/2/3 路径列表给用户 confirm。

**未做的事（明示）**：

- 不改 `automation/persona_extraction/orchestrator.py` 的 `_offer_squash_merge` 让它一并 offer 分支删除 / gc——是代码改动，超 /go scope，登记为后续 todo。
- 不写 phase 4 stage 重映射工具（程序级 utility）——同样登记为后续 todo。
- 不动 extraction 分支上任何文件（数据删除属 Need 1）。
- 不改 schemas / prompts / 代码。

## 计划动作清单

- file: `ai_context/decisions.md` #26 → 在现有"Squash-merge to library"段落末尾追加一句 R1
- file: `ai_context/conventions.md` §Git → 在 Flow rules 列表里追加一条 R1
- file: `ai_context/architecture.md` §Git Branch Model → Flow 列表追加一条 R1
- file: `ai_context/architecture.md` §Automated Extraction Pipeline → Phase 4 描述末尾追加 remap property
- file: `docs/todo_list.md` → 登记两条后续 todo：
  1. orchestrator `_offer_squash_merge` 增加分支删除 + gc 选项
  2. phase 4 scene_archive.jsonl 程序级 stage 重映射 utility（chapter → 新 stage_plan range）

## 验证标准

- [ ] `git diff --stat` 只动 4 个 ai_context 文件 + `docs/todo_list.md`
- [ ] R1 文字在三处一致（同一句话或同一意思）
- [ ] `decisions.md` #26 / `conventions.md` §Git / `architecture.md` §Git Branch Model 之间无矛盾
- [ ] Phase 4 remap 描述与原有 §Retrieval #39 / §Automated Extraction Pipeline 的 Phase 4 段落兼容、无重复
- [ ] `docs/todo_list.md` 新增条目格式与既有项一致
- [ ] 文档不出现真实书名 / 角色名 / 地名（用 `<work_id>` 占位）
- [ ] commit message 风格对齐 `git log --oneline -10`

## 执行偏差

- 计划清单原写"R1 落入 `decisions.md` / `conventions.md` / `architecture.md`"。Step 5 grep 发现 `docs/architecture/extraction_workflow.md:488` 和 `docs/requirements.md:2053` 已经写了"extraction 分支 squash 完可删除"——R1 的删分支这一半已在那里，只缺 `git gc --prune=now` 这一步。所以扩了 scope：在这两处把"可删除"扩写为"必须 `git branch -D` + `git gc --prune=now`"。**有意不动 `automation/README.md:197-203`**，因为它描述 orchestrator 当前实现（`_offer_squash_merge` 只 offer squash 本身、不 offer 分支删除 + gc），R1 的自动化部分已登记为 T-EXTRACTION-BRANCH-DISPOSE todo，等代码落地一并改 README，避免现在加上去就构成 doc-vs-code drift。

<!-- POST 阶段填写 -->

## 已落地变更

- [ai_context/decisions.md:81](ai_context/decisions.md) #26：在 squash 段末追加 R1（`git branch -D` + `git gc --prune=now` + "disposable scratchpad" 性质）
- [ai_context/conventions.md:102](ai_context/conventions.md) §Git Flow rules：在 squash 条目和 library merge main 条目之间插入新 R1 条目
- [ai_context/architecture.md:143](ai_context/architecture.md) §Git Branch Model：在 `_offer_squash_merge` 条目和 library merge main 条目之间插入 R1 条目
- [ai_context/architecture.md:161](ai_context/architecture.md) §Automated Extraction Pipeline → Phase 4：在 CLI `--start-phase 4` 后追加 stage assignment 是程序级 + scene_archive 可纯程序 remap 的描述
- [docs/architecture/extraction_workflow.md:485-490](docs/architecture/extraction_workflow.md)：把"extraction 分支可删除"扩写为"必须 `git branch -D` + `git gc --prune=now` 回收 blob"
- [docs/requirements.md:2048-2055](docs/requirements.md)：同上扩写
- [docs/todo_list.md](docs/todo_list.md) "下一步"段插入两条新 todo：
  1. **T-EXTRACTION-BRANCH-DISPOSE** — orchestrator `_offer_squash_merge` 追加分支删除 + gc 选项
  2. **T-PHASE4-STAGE-REMAP** — phase 4 scene_archive.jsonl 程序级 stage 重映射 utility（chapter → 新 stage_plan range）
  插在 T-WORLD-SNAPSHOT-S001-S002-MIGRATE 与 T-CHAR-SNAPSHOT-13-DIM-VERIFY 之间，与既有条目格式一致

## 与计划的差异

- 多动了 `docs/architecture/extraction_workflow.md` + `docs/requirements.md`（见"执行偏差"段说明，是发现既有相关描述后顺手对齐，不是 scope 扩张）
- `automation/README.md` 有意不动（同上）

## 验证结果

- [x] `git diff --stat` 6 文件：`ai_context/architecture.md`、`ai_context/conventions.md`、`ai_context/decisions.md`、`docs/architecture/extraction_workflow.md`、`docs/requirements.md`、`docs/todo_list.md` — 与"计划 + 偏差"一致
- [x] R1 文字在三处 ai_context + 两处 docs 一致（核心动作 `git branch -D` + `git gc --prune=now` + "disposable scratchpad" 性质完全一致；CN/EN 表述按文件语言匹配）
- [x] `decisions.md` #26 / `conventions.md` §Git / `architecture.md` §Git Branch Model 之间无矛盾（核对完，全部说"squash → 删分支 → gc"，没有任何一处说"保留分支"）
- [x] Phase 4 remap 描述兼容原 §Retrieval #39（#39 描述 retrieval artifacts 不入 git；新增的 remap 性质独立，不冲突）；§Automated Extraction Pipeline → Phase 4 内无重复
- [x] `docs/todo_list.md` 新增两条 todo 字段齐全（上下文 / 改动清单 / 验证 / 完成标准 / 预估 / 依赖）；位置在"下一步"段、与既有条目格式一致
- [x] `git grep '我和女帝' -- ':!logs/'` = 0 命中，文档无真实书名泄漏

## Completed

- **Status**: DONE
- **Finished**: 2026-04-25 03:14:06 EDT（写就 timestamp 持平 PRE，反映本次 /go 是同一会话内连续推进）
