# effort-gate-validation-run

- **时间**: 2026-07-20 13:36 EDT
- **分支**: main（提取跑在 `extraction/{work_id}`）
- **类型**: VALIDATION（无代码改动，纯实测验证）

## 背景

决策 #65（effort 分档 + 模型切 opus-4-8 + `semantic_timeout_s` 900）与决策 #66/#67
（L3 gate 定点复检 + 未触碰文件语义 issue 携带）的代码分两次落地，但两者的**完成
标准都要求「跑 ≥1 完整 stage 与基线对比」**，此前一直未做。本次跑 S004 补上。

跑法：`--resume --background --max-runtime 120 --end-stage 4`，即只跑 S004 一个
stage 后自动停。启动前先把 19 个 commit 从 `main` merge 进 `extraction/{work_id}`
——否则提取会用旧代码跑，测了等于没测。

## 结果

### stage 级对比

| stage | 提取 | repair | 总计 | defer | 配置 |
|---|---|---|---|---|---|
| S001 | 36m32s | 27min | 63min | 4 条 | opus-4-7 / max / 全文 gate |
| S002 | 25m23s | 31min | 56min | 0 条 | 同上 |
| S003 | 35m15s | 38min | 73min | 4 条 | 同上 |
| **S004** | **19m01s** | **8m04s** | **27min** | **0 条** | opus-4-8 / xhigh / scoped gate |

比最快基线快 52%，比最慢快 63%。成本 $44.25（38 calls）vs 基线 ~$52.6/stage，降 16%。

### 决策 #65 —— 提取侧双峰消失

S004 的 11 条提取 lane 全部收在 **348–1141s**：

```
char_snapshot:B:char_social  1141s      char_snapshot:A:char_decision  667s
char_support:A                868s      char_snapshot:B:char_decision  606s
char_snapshot:B:char_internal 748s      char_snapshot:A:char_internal  593s
char_support:B                745s      char_snapshot:B:char_expression 562s
char_snapshot:A:char_social   688s      world                          348s
char_snapshot:A:char_expression 685s
```

对比 `effort=max` 时代的三次爆掉样本 **2127s / 2192s / 2115s**（挤得异常紧、
中招 lane 随机）——本轮最慢 1141s，**无一接近 2100s**。且最慢者是
`char_snapshot:*:char_social` 而非此前三次都中招的 `char_support`，即从「随机爆掉」
回到了正常负载差异。`world` 也从历史 p50 439s 降到 348s。

子进程命令行确认新配置生效：`--model claude-opus-4-8 --effort xhigh`。

### 决策 #66/#67 —— gate 定点化终结打地鼠

**round 结局**（5 个文件进 repair）：

```
Round 1 result: resolved=1, persisting=0, introduced=0   × 4 个文件 → PASS
Round 1 result: resolved=4, persisting=1, introduced=0   ← 5-issue 文件
Round 2 result: resolved=0, persisting=1, introduced=0   → 停在 round 2，FAIL
```

对比基线 S003 的病态模式（`resolved=1, persisting=0, introduced=1` 连续 4 轮 →
跑满 `total_round_limit=5` 判 FAIL）：**`introduced` 全线归零**。证实此前那个
「修一个冒一个」的循环，根因就是全文复检的审校抖动，不是修复真的搞坏了什么。

**安全阀恢复工作**——这是本次验证最重要的附带发现。那个 5-issue 文件停在 round 2
而非跑满 5 轮：两轮 `persisting=1` 指纹相同 → `is_stalled()` 触发 → 诚实停手。
基线时代 `persisting` 恒为 0，`is_regression` / `is_stalled` **两阀全盲**。现在
`persisting` 有值了，说明 scoped gate 不是「看不见问题所以都 PASS」，它照样抓得住
真没修好的东西——原先担心的「假 PASS」风险被 #67 的 carried 机制兜住。

**gate 耗时**：27 条 repair lane 最慢 319s，绝大多数落在 **9–20 秒**；基线全文
gate 是 276–567s。日志措辞也从 `re-checking N file(s) modified this round` 变成
`scoped per file to touched + carried semantic path(s)`。

### 三类故障归零

S004 全程：`timed out` 0 / `Invalid JSON` 0 / `truncated` 0 / `unavailable` 0。

- `truncated` 归零 → 决策 #70（Phase A 不再截断）生效
- `Invalid JSON` 归零 → `e39c5fa`（容忍多个顶层数组）生效
- `timed out` 0 且最慢 repair lane 319s → `semantic_timeout_s=900` 余量充足

## 证据边界（不要过度外推）

- **n=1**。单 stage 不能排除运气；S004 本身可能比 S001/S003 轻
- S004 只有 **5 个文件**进 repair，`Invalid JSON` 的 0 次不足以证明根因已彻底
  消除（基线是 3 stage / 2 次）
- 但四个观测点同向改善，且每一项都有机制解释（不是玄学），证据强于「碰巧」

## 外推

53 stage × 27min ≈ **24 小时**（原 33 小时估计的 3/4），成本 ≈ **$2,345**。

## 影响的 todo

- `T-GATE-SCOPED-RECHECK` —— 5 项完成标准全部满足，归档
- `T-EFFORT-TIER-TUNING` —— 此前已归档，本次补上它缺的实测验证
