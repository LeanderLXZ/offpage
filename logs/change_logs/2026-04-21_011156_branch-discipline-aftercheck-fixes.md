# /after-check 后续修正：F1–F5 全部收口

## 动机

昨夜落地 "orchestrator finally-checkout + SessionStart hook" 后的 `/after-check`
报告（conversation 内存，未归档）识别出 5 条 findings：F1（`main` vs
`master` 命名分裂）、F2（baseline rerun 在分支切换之前）、F3（`checkout_master`
无 dirty guard）、F4/F5（extraction_workflow.md + decisions.md item 26 仍说
`main`）。用户决定全部修掉。

## 改动

### F3 — `checkout_master` 加 dirty-tree guard
- `automation/persona_extraction/git_utils.py`：`checkout_master` 在切换前
  `git_status(project_root).clean` 判定，非 clean 时打 warning 并保持原分支，
  返回 `False`。防止 SIGINT / exception 中断后，未跟踪的半 stage 产物
  （`works/*/analysis/**/阶段XX_*.json`）跟着 `git checkout master` 漂移到
  master。文档同步到 docstring。

### F2 — baseline rerun 块移入 try/finally
- `automation/persona_extraction/orchestrator.py` `run_extraction_loop`：
  把 `create_extraction_branch` 调用提前到原 baseline 块之上，整个"建分支
  → baseline 重跑 → `--end-stage 0` 提前 return → ERROR 重置 → banner → while
  loop"全部装进同一个 try 块，finally 仍是 `checkout_master`。
- 影响：`--resume` 场景下 baseline 重跑的 commit 现在落在 extraction 分支
  而非 master，符合 "extraction data 只进 extraction 分支" 的硬规则。
- `--end-stage 0` 早 return 也走 finally，一并回 master（原行为在此路径不
  checkout_master，现在统一）。
- `run_full` 无需改动（其内部 baseline 已在原 try 内走 `run_baseline_production`
  → `commit_stage`，并通过自身 finally 回 master；`run_extraction_loop` 被
  `run_full` 调进来时 `phase_2_5` 已 done，新加的 baseline 块自动 skip）。

### F1 — 代码侧 `main` → `master`
- `automation/persona_extraction/orchestrator.py` `_offer_squash_merge`：
  docstring、用户可见打印（交互提示、手动 fallback 示例）、`squash_merge_to`
  调用的目标分支参数，一律改为 `master`。仓库里从未存在过 `main` 分支，
  原代码真跑会 `git checkout main` 失败。
- `automation/persona_extraction/` 剩余 `\bmain\b` 都是 "main character" /
  "main thread" / `def main()`，无关分支。

### F4 — `docs/architecture/extraction_workflow.md`
- 运行保障段 `squash merge 回 main` → `squash merge 回 master`。
- 新增一条"分支纪律落实"子项，点到 try/finally + `checkout_master` dirty
  guard + SessionStart hook，指向 `ai_context/architecture.md §Git Branch Model`。

### F5 — `ai_context/decisions.md` item 26
- 原 "squash-merge to main" → "squash-merge to `master`"，同时显式标注
  extraction 分支名 `extraction/{work_id}`。与 item 26a（昨夜新增）完全对齐。

### 顺带收口
- `ai_context/architecture.md §Git Branch Model` 更新两处：
  1. Exit mechanism 描述扩写 extraction work 范围 = 建分支 + baseline rerun
     + Phase 3 loop（匹配 F2 新布局）。
  2. 新增 dirty-tree guard 子条（匹配 F3）。
  3. Extraction-data 范围明确包含 baseline（`world/foundation/`、
     `characters/*/canon/identity.json`、`fixed_relationships.json`），防止
     将来读者误读为"只有 Phase 3+ 产物属于 extraction 分支"。
- `ai_context/architecture.md` Phase 3 summary 段：`squash-merge to main` →
  `squash-merge to 'master'`。
- `ai_context/current_status.md` "Git integration" 一行：同上。

## 验证

- `python3 -c "import ast; ast.parse(open('automation/persona_extraction/orchestrator.py').read())"`
  通过。
- `inspect.getsource(ExtractionOrchestrator.run_extraction_loop)` 结构检查：
  `try:` → `create_extraction_branch` → baseline 检查块 → ... → `finally:`
  + `checkout_master` 顺序正确。
- `inspect.getsource(ExtractionOrchestrator._offer_squash_merge)` 无 `main`
  分支引用，`master` 出现多次。
- `from automation.persona_extraction.git_utils import checkout_master`
  成功；当前 master + dirty tree 下 `checkout_master(Path.cwd()) == True`
  （已在 master，直接返回 True，不触发 guard，符合语义）。
- `grep -rn '\bmain\b' docs/architecture/ ai_context/ automation/ | grep
  branch-related` 无 residual。

## 未做（明确不在本次）

- F6 `automation/README.md` 未提新机制：影响面窄，user 明确说 F1–F5，本次
  不动。可登记到 todo_list.md 作为 known gap。
- `run_full` 前半段（Phase 0/1/2 confirm 阶段）不在 try/finally 内：目前不会
  有分支残留（那段仍在 master），故不加。
- `checkout_master` dirty 时返回 False 的上游处理：当前 orchestrator finally
  忽略返回值（best-effort 语义），不会因此抛；用户看 log 自己决策。若未来
  希望 finally 失败即 raise，再加一层。

## 影响范围

- 行为：`--resume` 触发 baseline 重跑时 commit 落到 extraction 分支（符合规约）；
  SIGINT/异常中断后 dirty tree 不再被自动带回 master（用户需手工 `git
  checkout master`，但会有 warning 指引）；`--end-stage 0` 早 return 现在也
  会 checkout_master。
- 数据：无。
- 兼容性：`run_extraction_loop` / `run_full` / `checkout_master` 函数签名未改；
  外部调用方（`python -m automation.persona_extraction`）行为无感知变化，
  仅分支归属更正。
