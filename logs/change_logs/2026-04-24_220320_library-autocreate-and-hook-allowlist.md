# library-autocreate-and-hook-allowlist

- **Started**: 2026-04-24 22:03:20 EDT
- **Branch**: master
- **Status**: PRE

## 背景 / 触发

上一轮 /post-check（REVIEWED-PARTIAL）发现两条 Medium 命中：

1. **library 分支无自检** — `_offer_squash_merge` 调 `squash_merge_to(target='library', ...)`；`squash_merge_to` 在 git_utils.py 直接 `git checkout target_branch`，分支不存在则失败返回 None。新克隆 / 新工作环境若没预先 `git branch library master`，第一次 squash 静默失败。
2. **`session_branch_check.sh` 仅特判 master** — 三分支模型下 `library` 是合法的归档分支，但 hook 把任何非 master 都视为可能"遗弃"，会对 library 误警告。

附带 [M] #2（README 缺初始化指引）：用户选了"自动创建"路线后，README 也需要一句说明，让用户预期"library 是按需自动建的"。

## 结论与决策

按用户拍板的 **lazy + idempotent 自动创建**方案：

- `_offer_squash_merge` 入口先检测目标分支是否存在；不存在则**从 master 创建**并打印一行说明，幂等（已存在则跳过）。不在 orchestrator 启动时建，也不引入新 CLI 子命令。
  - 创建用 `git branch <target> master`，从 master HEAD 起点。如果用户改了 `[git].squash_merge_target`，按那个名字建。
  - 创建失败（极少：磁盘 / 权限 / 名字非法）则报错跳过 squash，不静默——保留现行"squash_merge_to 失败返回 None"的语义包络。
- `session_branch_check.sh` 把 `library` 加进合法分支白名单：与 master 同等待遇（只打印 banner、不警告）。**注意**：此 hook 本就检测 `pgrep -f automation.persona_extraction`，所以 extraction/* 在跑时也不警告——library 加白名单后路径变为：master / library → banner；非 master/library 且无 orchestrator → warning。
- `automation/README.md` Git Branch Model 节加一句"library 分支首次 squash 时由 orchestrator 按需自动从 master 创建（lazy + idempotent）"。

不做：
- 不改 ai_context/conventions.md / architecture.md / decisions.md / docs/requirements.md / docs/architecture/extraction_workflow.md：上一次 /go 已经把三分支模型的"语义层"全部对齐，本次只是补"实现层"自检 + hook 白名单 + README 注脚，不动语义。
- 不写 unit test：repo 下没有 `tests/` 目录，且本次改动是少量 git CLI 包装，验证靠 import smoke + 手工 dry-run。

## 计划动作清单

- file: `automation/persona_extraction/git_utils.py` → 新增 helper `ensure_branch_from_master(project_root, branch) -> bool`：分支不存在则从 master 创建；存在则 no-op；返回是否最终存在。失败 logger.error。
- file: `automation/persona_extraction/orchestrator.py` `_offer_squash_merge` → 在打印 squash 前调用 `ensure_branch_from_master(self.project_root, target)`，失败则报错并 return；成功且实际创建过则打印 `[setup] target branch '{target}' created from master.` 一行说明。
- file: `automation/persona_extraction/orchestrator.py` 顶部 import → 加 `ensure_branch_from_master`。
- file: `.claude/hooks/session_branch_check.sh:16` → 把 `[ "$branch" = "master" ]` 改成同时识别 `master` 与 `library`（也走 banner 路径）。注释同步说明三分支模型下 library 是合法停留位。
- file: `automation/README.md` Git Branch Model 节 → 加一句"`library` 分支由 orchestrator 在首次 squash 时按需自动从 master 创建（lazy + idempotent），无需手工初始化"。

## 验证标准

- [ ] `python3 -c "from automation.persona_extraction.git_utils import ensure_branch_from_master; print('OK')"` import 成功
- [ ] `python3 -c "from automation.persona_extraction.orchestrator import ExtractionOrchestrator; print('OK')"` import 成功
- [ ] `bash -n .claude/hooks/session_branch_check.sh` 语法通过
- [ ] 手工触发 dry：`git branch -D library; python -c "from pathlib import Path; from automation.persona_extraction.git_utils import ensure_branch_from_master as f; print(f(Path('.'), 'library'))"`，应输出 True 且 `git branch --list library` 重新有该分支；二次跑同函数应输出 True 且不重复创建
- [ ] 手工触发 hook 在 master / library 分支均不报"abandoned"警告；在 extraction/* 无 orchestrator 时报警告（保持原行为）

## 执行偏差

执行中拆出一个独立的 `branch_exists(project_root, branch) -> bool` helper，
让 `_offer_squash_merge` 能在调 `ensure_branch_from_master` 之前先判定
"分支是否已存在"，以决定是否打印 `[setup] target branch ... created` 一行
反馈。原 PRE 设想直接让 ensure 函数返回三态，但实测下来 helper 拆得更干净
也更易测试。同时 Step 6 grep 时发现 `automation/README.md:73` `[git]` 配置
表描述未含 `squash_merge_target`，与 `docs/requirements.md` 表格不一致，
顺手补上——属本次直接对齐范围。

<!-- POST 阶段填写 -->

## 已落地变更

`automation/persona_extraction/git_utils.py:273-294` — 新增两个 helper：

- `branch_exists(project_root, branch) -> bool` — 通过 `git rev-parse --verify --quiet refs/heads/{branch}` 探测，0 即存在
- `ensure_branch_from_master(project_root, branch) -> bool` — 不存在则 `git branch {branch} master`；幂等；失败 logger.error 后返回 False

`automation/persona_extraction/orchestrator.py`：
- 顶部 import 加 `branch_exists` 和 `ensure_branch_from_master`
- `_offer_squash_merge` 入口：先 `existed = branch_exists(...)`；调 `ensure_branch_from_master`，失败则打印 `[ERROR] Cannot ensure target branch...`并 return；成功且 `not existed` 时打印 `[setup] target branch '{target}' created from master.` 一行说明
- 后续 squash 流程不变

`.claude/hooks/session_branch_check.sh:19` — `if [ "$branch" = "master" ]` → `if [ "$branch" = "master" ] || [ "$branch" = "library" ]`；文件头注释同步说明三分支模型 master / library 都是合法停留位

`automation/README.md:201-203` — § squash-merge 段尾追加："`library` 分支由 `_offer_squash_merge` 在首次 squash 时按需自动从 master 创建（lazy + idempotent），无需手工 `git branch library master` 初始化。"

`automation/README.md:73` — `[git]` 配置概述行加入 `squash-merge 目标分支（默认 library）`（与 docs/requirements.md `[git]` 表格一致）

## 与计划的差异

PRE 列了 4 项；POST 拆出 `branch_exists` 一个 helper（实现层细化，无语义变化）+ 加了 1 项 `automation/README.md:73` 配置概述行的小补漏，已在"执行偏差"段记录。

## 验证结果

- [x] `python3 -c "from automation.persona_extraction.git_utils import branch_exists, ensure_branch_from_master; ..."` 成功
- [x] `python3 -c "from automation.persona_extraction.orchestrator import ExtractionOrchestrator"` 成功
- [x] `bash -n .claude/hooks/session_branch_check.sh` 语法通过
- [x] dry-run idempotent：library 已存在 → ensure 返回 True，二次跑也返回 True，无重复创建
- [x] dry-run create-on-missing：分支 `library-test-tmp` 不存在 → ensure 返回 True 且 `git branch --list` 显示新建；测试后已删
- [ ] 手工触发 hook 在 master / library 分支均不报"abandoned"（语法已过，行为靠 if 条件命中——不便于全自动测试，留给下次 SessionStart 时观察）

## Completed

- **Status**: DONE
- **Finished**: 2026-04-24 22:05:58 EDT
