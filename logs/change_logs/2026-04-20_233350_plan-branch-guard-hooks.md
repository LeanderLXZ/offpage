# 方案草案：Git 分支约定的文档可见性补齐 + SessionStart 分支提示 + orchestrator 收尾

**状态**：待审；执行前需用户确认。不是回顾性 log。

## 目标

把"代码走 master、提取数据走 extraction/*"这条约定从"只有规则文本"升级为"规则 + 收尾机制 + 会话级提示"三层，同时补齐 ai_context 可见性。

## 范围三块

- **A** 文档可见性（ai_context + conventions）
- **B2** SessionStart 分支提示（shell hook）
- **C** orchestrator 正常/异常退出统一切回 master

显式不做：PreToolUse 分支核验（B1 已去掉，误伤成本高于收益；会话级 B2 + 代码级 C 已足够）、自动切分支、自动 squash-merge、Edit/Write hook、任何 PostToolUse 分支修改。

## 文件清单

| # | 文件 | 动作 |
|---|---|---|
| A1 | `ai_context/architecture.md` | 新增 `## Git Branch Model` 节（插在 `## Automated Extraction Pipeline` 前） |
| A2 | `ai_context/conventions.md` | §Git 末尾加一句"规则落实：orchestrator 自动切换 + SessionStart 分支提示 hook（见 architecture §Git Branch Model）" |
| A3 | `ai_context/decisions.md` | 新增 decision：为什么只做 SessionStart hook 而不做 PreToolUse 分支核验 |
| B2 | `.claude/hooks/session_branch_check.sh` | 新文件，SessionStart shell 脚本 |
| B3 | `.claude/settings.json` | 注册 SessionStart hook |
| C1 | `automation/persona_extraction/orchestrator.py` | Phase 3 loop 退出分支（正常 / `[BLOCKED]` / 中断）后统一调 `checkout_master()` |
| C2 | `automation/persona_extraction/git_utils.py` | 新增 `checkout_master(project_root)` helper |

## Diff 草图

### A1 architecture.md 新节（约 14 行）

```
## Git Branch Model
- 静止态 = `master`；运行 orchestrator 时自动切到 `extraction/{work_id}`。
- 切换机制：`orchestrator.py:1170` 调 `create_extraction_branch`
  (`git_utils.py:102`)；不存在则 `-b` 新建。
- 收尾机制：Phase 3 loop 任何退出分支（DONE / BLOCKED / 中断 / 异常）
  统一 `checkout_master`（`git_utils.py`，见 C2）。
- 代码 / schema / prompt / docs / ai_context 改动 → 只在 master；
  通过 `git merge master` 带进 extraction 分支。
- 提取数据（`works/*/analysis/**` 下 stage_snapshots / memory_timeline /
  memory_digest / stage_catalog / world_event_digest / identity /
  manifest）→ 只在 extraction 分支 commit。
- 全部 stage COMMITTED 后由 `_offer_squash_merge` 提示人工 squash 回 master。
- 异常兜底：SessionStart hook (`.claude/hooks/session_branch_check.sh`)
  在新会话启动时检测"非 master 分支 + 无 orchestrator 进程"的异常组合并提示。
```

### A2 conventions.md §Git 追加

```
- 以上规则由 (1) orchestrator 在 Phase 3 loop 前/后自动切换、
  (2) SessionStart hook 会话启动时检测异常分支错位共同落实；
  参见 architecture §Git Branch Model。
```

### A3 decisions.md 新增条目（约 6 行）

```
### 不做 PreToolUse commit/push 分支核验
- 原因：orchestrator finally-checkout 已覆盖绝大多数场景；
  SessionStart hook 负责剩余"异常中断忘切回"的信号。
- 误伤成本：人工 hotfix 或混合 commit 合法场景会被拦截；
  每次 commit 多一层 shell 开销。
- 若未来 orchestrator 路径绕过率高，再补。
```

### B2 session_branch_check.sh 核心逻辑（bash，约 15 行）

```
1. branch=$(git branch --show-current)
2. [ "$branch" = "master" ] && exit 0          # 静止态正常
3. pgrep -f 'automation.persona_extraction' >/dev/null && exit 0   # 提取中正常
4. 否则打印到 stdout：
   "⚠ 当前在分支 '$branch' 但未检测到 orchestrator 进程——
    可能是上次异常中断，检查后 `git checkout master`。"
5. exit 0（SessionStart hook 的 stdout 进入会话上下文；非 0 会阻断启动）
```

### B3 settings.json 片段

```
"hooks": {
  "SessionStart": [
    {"hooks": [{"type": "command",
      "command": "bash .claude/hooks/session_branch_check.sh"}]}
  ]
}
```

注：若 `.claude/settings.json` 已有 `"hooks"` 字段，append SessionStart 数组；无则新增整节。

### C1 + C2 orchestrator 收尾

```
# git_utils.py 新增
def checkout_master(project_root: Path) -> bool:
    result = _git(["checkout", "master"], project_root)
    return result.returncode == 0

# orchestrator.py: Phase 3 loop 所有退出分支汇合处（第 1206 行附近）
try:
    ... 现有 all_done / stopped_by_limit 分支逻辑 ...
finally:
    checkout_master(self.project_root)
    logger.info("Returned to master branch")
```

注：`_offer_squash_merge` 内部本就落到 master，叠加 finally 幂等；中断路径
（`self._interrupted` / `_check_runtime_limit`）现在也能保证回 master。

## 验证方式

- **A**：`grep -n "Git Branch Model" ai_context/architecture.md` 命中；
  `grep "SessionStart" ai_context/conventions.md` 命中；
  decisions.md 新条目可见。
- **B2**：切到 `extraction/{work_id}` 后启新 Claude Code 会话，
  确认上下文开头有 ⚠ 行；切回 master 再启一次，确认完全静默；
  起一个 orchestrator 进程（sleep mock 即可）在 extraction 分支再启会话，
  确认也静默（有进程正常）。
- **C**：起一次 `--end-stage 1` 试跑；退出后 `git branch --show-current` 应是
  master；中途 Ctrl+C 同样应回 master；人为制造 extraction 失败路径后也应回 master。

## 回滚路径

- A/B2/B3/C 全部通过 `git revert` 单个 commit 回退，不触碰数据。
- B2 误伤（比如 pgrep 假阴）：注释 `.claude/settings.json` 的 SessionStart 项
  立即关闭；脚本文件保留。
- orchestrator finally-checkout 若与未来多阶段会话语义冲突：删 finally 块即可回到现状。

## 执行节奏（两 commit）

1. **commit-1 = A 全部**：纯文档，不改行为。
2. **commit-2 = C + B2 + B3**：代码侧 orchestrator finally-checkout + shell hook + settings 注册。
   C 与 B2 协同——C 保证正常退出回 master（大多数情况 B2 静默），B2 只在 C 失败
   或绕过 orchestrator 人工操作时才开口。

## 阻塞

无。等用户 `/go` 或明确批准后按此执行。
