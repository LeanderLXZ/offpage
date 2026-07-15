# fix(prompt_builder): 修复 restructure 遗留的 5 处扁平化惰性 import

**时间**: 2026-07-15 05:00 EDT
**类型**: 代码缺陷修复（阻断 Phase 3 端到端运行）
**分支**: main（代码修复落 main，随后 merge 进 extraction 分支）

## 症状

Phase 3 首次端到端运行时崩溃退出，0/53 stage 提交。`world` + 2 个
`char_support` lane 正常跑完，但两个 `char_snapshot` lane 一进
`build_char_snapshot_prompt` 即 `ModuleNotFoundError: No module named
'extraction.persona_extraction.lane_output'`，异常穿过两层
`ThreadPoolExecutor.result()` 冒泡到主线程，orchestrator 走
`finally: checkout_main` 退出。

## 根因

包结构 restructure（commit 5d9ef6f）把模块下沉到子包：

- `lane_output` → `lifecycle/lane_output.py`
- `snapshot_merge` → `phases/snapshot_merge.py`

orchestrator 顶层 import 已更新（`from .lifecycle.lane_output import`），
但 `prompt_builder.py` 内 5 处**函数体内的惰性 import**（为避开 import
循环而下沉到函数内）未同步。惰性 import 在模块加载期不执行，只有真正跑到
char_snapshot 代码路径才触发——而 Phase 3 此前从未端到端跑过，所以
AST / import-time smoke 全绿仍漏过。

## 改动

`extraction/persona_extraction/prompt_builder.py` 5 处 import 路径修正：

| 行 | 旧 | 新 |
|---|---|---|
| 845 | `from .lane_output import prev_snapshot_slice_path` | `from .lifecycle.lane_output import ...` |
| 846 | `from .snapshot_merge import SUB_LANE_NAMES` | `from .phases.snapshot_merge import ...` |
| 896 | `from .snapshot_merge import (...)` | `from .phases.snapshot_merge import (...)` |
| 1071 | `from .lane_output import prev_snapshot_slice_path` | `from .lifecycle.lane_output import ...` |
| 1072 | `from .snapshot_merge import SUB_LANE_NAMES` | `from .phases.snapshot_merge import ...` |

## 验证

- 全包 grep `from \.(lane_output|snapshot_merge|...) import`（排除子包路径）→
  除本 5 处外无其他扁平化残留。
- AST parse ok；惰性 import 目标符号（`prev_snapshot_slice_path` /
  `SUB_LANE_NAMES` / `FIELD_ALLOCATION` / `SHARED_KEY_SUBKEYS`）全部可解析；
  `prompt_builder` 模块加载 ok。

## 数据面影响

无。崩溃时 0 stage 提交，phase 2 baseline（extraction 分支 16 文件）完好。
崩溃 finally 的 checkout_main 把 extraction 分支追踪的 baseline 从工作树移除
（正常 git 行为），main 提交历史始终干净（仅 `works/README.md`）。3 个未
gitignore 的孤儿半成品 S001 产物（world snapshot + 2 memory_timeline）在
重跑前清理。
