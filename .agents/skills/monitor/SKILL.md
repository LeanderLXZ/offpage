---
name: monitor
description: 后台进程进度监控 — 以固定间隔（默认 5min，argument 可指定如 3min/10min）定期汇报 persona_extraction / simulation / 批量脚本的 PID、进度、错误、吞吐、ETA、异常。只读不改：发现问题先查清原因给信息+建议，不 kill、不重启、不改配置，等用户决定后再让 /go 执行。支持带场景说明（如 "phase 3 提取目标角色 X/Y"）定位关注点。用户说"监控一下"、"monitor 5min ..." 时触发。
---

# /monitor — 后台进程进度监控

以固定间隔监控正在运行的后台任务（通常是 `persona_extraction` / simulation / 批量脚本），定期向用户汇报进度、错误、效率、预估完成时间。**只读不改**：发现问题先查清原因，向用户提供信息与建议，不着急动手。

`$ARGUMENTS`：刷新间隔 + 可选场景说明。例：
- `/monitor` → 默认 5 分钟
- `/monitor 3min` → 3 分钟
- `/monitor 5min 现在从 phase 3 开始跑提取，目标角色 X、Y，后台并行默认` → 5 分钟 + 场景上下文

解析规则：首个 token 形如 `{N}min` / `{N}s` / `{N}m` / 纯数字（按分钟） → 间隔；其余为场景描述。缺省 5 分钟。

## 0. 场景登记

- 打印："监控间隔 = {N}min；场景 = {场景说明或 'unspecified'}"
- 场景描述里若提到具体 phase / 目标 / 并行数 → 记下，后续汇报时以此判断是否偏离预期
- 询问是否有任何额外信号需要关注（如特定日志路径、特定 PID、特定 work 目录）—— 用户给就记下，不给就按默认扫

## 1. 识别被监控的进程与产物

首轮先盘点，之后每轮都刷一遍：

- `pgrep -af persona_extraction`（或场景提到的其他脚本）列出 PID + 命令行
- `works/*/analysis/progress/*.pid` / `works/*/analysis/progress/*.json` 看进度文件
- `works/*/analysis/logs/` 最新一份日志 tail 若干行
- simulation 场景加扫 `users/*/sessions/` / simulation 相关目录
- 用户指定的自定义路径优先

## 2. 单轮汇报内容

每轮输出一个紧凑汇报块，字段固定：

1. **Timestamp**：`TZ='America/New_York' date '+%H:%M:%S'`
2. **Processes**：PID + 命令摘要 + 运行时长（`ps -o etime= -p <PID>`）；若某 PID 消失 → 标红 "gone"
3. **Progress**：每个 work / 目标的当前阶段 / 完成比例（从 progress 文件或日志解析）
4. **Errors**：近一轮日志里有没有 `ERROR` / `Traceback` / `failed` / `retry exhausted`；有则摘录关键行 + 文件路径 + 行号
5. **Throughput**：与上一轮对比的推进量（如 chunks 处理数、tokens 消耗、文件数）；算瞬时速率
6. **ETA**：按最近 1–3 轮的速率外推剩余时间；样本不够 → 标注"样本不足"
7. **Anomalies**：推进停滞、速率骤降、内存 / GPU 异常、临时文件堆积、PID flapping —— 任何值得注意的

## 3. 发现问题时的处理

- **不要改文件、不要 kill 进程、不要重启**
- 先定位：日志行号、相关 work 目录、涉及的 schema / prompt / 代码文件
- 给出 **信息 + 建议**：这是什么错、可能的原因、建议的下一步（重试 / 调参 / 换策略 / 先观察），标注"建议"不是"已执行"
- 严重错误（全部进程挂掉 / 数据损坏 / 无限重试）→ 立即打断常规汇报节奏，单独高优告警一次，等用户指示
- 用户明确批准才动手，否则继续只读监控

## 4. 循环节奏

- 首轮立刻跑一次汇报
- 之后每 N 分钟一轮；两轮之间保持安静，不要刷屏
- 用户主动打断（提问 / 指令）→ 立即响应，完事后恢复节奏
- 用户说"停"/"结束监控"/`/stop` 类意图 → 停止并打印最终汇总（总运行时长、最终状态、本次监控期间发生的 anomaly 列表）
- 进程全部结束 → 主动打印"全部进程已结束"+ 最终汇总，停止循环

## 约束

- **只读不写**：不 kill、不重启、不改 config、不删日志、不动产物
- 问题只报不修；修改由用户决定后走 `/go`
- 汇报要紧凑，不要重复未变化的背景信息；只报新增 / 变化 / 异常
- 速率 / ETA 算法要标注样本量，别给假数字
- 场景未提到的进程 / 目录 → 发现异常可以顺带报一句，但不抢占主场景

---

**镜像约束**：本文件和 `.claude/commands/monitor.md` 正文保持同步——任一侧修改必须在同 commit 内镜像到另一侧。本文件额外带 YAML frontmatter（`name` / `description`），正文（从一级标题 `# /monitor` 起往下）与 `.claude/commands/monitor.md` **逐字一致**。
