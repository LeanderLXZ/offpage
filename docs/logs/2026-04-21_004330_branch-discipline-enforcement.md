# 分支约定落实：orchestrator finally-checkout + SessionStart 异常提示

## 动机

`ai_context/conventions.md §Git` 规定"代码走 master、提取数据走
`extraction/{work_id}`"，但落实靠人的自律：orchestrator 只在启动时切到
extraction 分支，未保证退出时切回 master；ai_context 也没有任何一处描述
这套分支模型，读文档的人/AI 必须读代码才能验证约定。结果：上次提取异常退
出（`[ERROR] char_snapshot 某角色 extraction failed`）后工作树留在
extraction 分支也能被视为正常状态，难以分辨"是在提取中"还是"提取崩
了"。本次补齐文档与两条机械约束。

## 改动

### ai_context（纯文档）
- `ai_context/architecture.md` 新增 `## Git Branch Model` 小节（置于
  `## Automated Extraction Pipeline` 前）：描述静止态 = master、运行态
  自动切 extraction、退出兜底 checkout_master、SessionStart hook 信号、
  代码/数据分离规则。
- `ai_context/conventions.md §Git` 末尾追加 "Enforcement" 项，点到
  orchestrator finally-checkout 与 SessionStart hook 两条落实机制。
- `ai_context/decisions.md` 新增 26a：解释为什么不做 PreToolUse
  commit/push 核验（误伤成本 > 边际收益）。

### 代码
- `automation/persona_extraction/git_utils.py`：新增 `checkout_master(
  project_root) -> bool`，幂等非破坏性。已在 master 直接返回；`git
  checkout master` 失败（如 uncommitted 冲突）返回 False 并 log，不抛
  异常——这是 best-effort 清理。
- `automation/persona_extraction/orchestrator.py`：
  - 导入 `checkout_master`。
  - `run_extraction_loop`：把从 `create_extraction_branch` 到
    `tracker.print_summary()` 的整段包进 `try / finally:
    checkout_master(...)`。覆盖所有退出路径——正常 DONE、BLOCKED、
    `--end-stage` 提前停、`self._interrupted` 中断、`_check_runtime_
    limit` 超时、未捕获异常、`sys.exit(1)`（建分支失败）。
  - `run_full`：把从 `create_extraction_branch` 到 `run_extraction_
    loop` 调用的整段包进同样的 try/finally，防 `run_baseline_
    production` / `commit_stage` 中间崩掉留在 extraction 分支。
    内层 `run_extraction_loop` 自带 finally 时外层冗余但幂等。

### Claude Code hook
- `.claude/hooks/session_branch_check.sh`：新文件，SessionStart hook。
  - 在 master → `[git] branch: master`，静默。
  - 在非 master + 有 orchestrator 进程 → `[git] branch: X
    (orchestrator running — extraction in progress)`，静默。
  - 在非 master + 无 orchestrator 进程 → `[git] branch: X  ⚠ no
    orchestrator process detected — possibly abandoned after crash;
    check and 'git checkout master'`。
  - 退出码恒为 0（非 0 会阻断 Claude Code 启动）。
- `.claude/settings.json`：把原来 SessionStart 内联 bash 替换成
  `bash .claude/hooks/session_branch_check.sh`。新脚本是原行为的超集
  （保留 branch banner + 加 orchestrator 检测）。

### 计划文档
- `docs/logs/2026-04-20_233350_plan-branch-guard-hooks.md`：执行前的
  方案草稿，记录两轮迭代（先含 PreToolUse 分支核验 B1 → 讨论后删除
  B1 + 改 bash → 三 commit 缩两 commit）。保留作为设计历史。

## 验证

- Import 检查：`checkout_master` 从 git_utils 能导入；
  `ExtractionOrchestrator.run_extraction_loop` 与 `run_full` 源码中
  同时出现 `finally:` 与 `checkout_master`。
- `checkout_master` 在 master 分支跑一次：branch 不变、ok=True。
- shell hook `bash -n` syntax OK；当前 master 跑一次输出
  `[git] branch: master`。
- `.claude/settings.json` `json.load` 通过；`hooks` 下保留 PreToolUse
  + SessionStart 两项。

## 未做（明确不在本次范围）

- PreToolUse `git commit`/`git push` 分支 × 路径核验 hook：讨论后决定
  不做，理由见 decisions.md 26a。若未来绕过 orchestrator 的 commit
  错分支案例变多，再补。
- `validator.py:94` 注释里的旧 example 名（遗留具体角色名）：与本次
  分支主题无关，未触碰；登入 todo 较合适，但本次就不登记了。
- `run_full` 在前半段（Phase 0/1/2 confirm 阶段）还没切到 extraction
  分支，这段未包 try/finally。目前不会有分支残留问题，故不加。

## 影响范围

- 行为：orchestrator 正常或异常退出后工作树 100% 回到 master；hook
  每次会话启动多 5 ms（bash + git branch + pgrep）。
- 数据：无。
- 兼容性：`run_extraction_loop` / `run_full` 签名未改；外部调用方
  （`python -m automation.persona_extraction`）行为无感知变化。
