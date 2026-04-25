# Orchestrator 运维增强与首批提取完成

日期：2026-04-07

## 变更概要

本次会话完成了两大类工作：编排器运维功能增强，以及首批提取的端到端验证。

## 1. 首批提取完成

- 作品：<work_id>
- batch_001（阶段01_九世复活·<location_a>初遇）通过完整流程：
  提取 → 程序化校验 → 语义审校 → git commit（eed29f7）
- 产出：世界快照、<character_a>/<character_b>角色快照和 memory_timeline
- 确认 40 batch 规划（此前 ai_context 误记为 36）
- batch_002 因 SSH 断开超时失败，已回滚到干净状态

## 2. 编排器运维增强

### 新增文件

- `automation/persona_extraction/process_guard.py`
  - PID lockfile 互斥（同一作品同时只允许一个提取进程）
  - `/proc/{pid}/status` RSS 内存读取
  - `--background` 后台启动（`start_new_session=True` 存活 SSH 断开）

### 修改文件

- `automation/persona_extraction/llm_backend.py`
  - `subprocess.run` → `subprocess.Popen` + 心跳线程
  - 每 30s 显示 PID、已用时间、子进程和编排器内存（RSS）
  - `LLMResult` 新增 `pid`、`duration_seconds` 字段

- `automation/persona_extraction/orchestrator.py`
  - `ProgressTracker` 新增分步耗时追踪（extraction/validation/review/commit）
  - batch 头部显示分步 ETA 预估和内存
  - `--max-runtime` 支持：在 batch 间检查总耗时，超限优雅停止
  - PID 锁集成 + SIGTERM handler
  - 修复 commit 顺序：先 transition(COMMITTED) + save，再 git commit，
    确保 progress 文件状态与 git commit 一致

- `automation/persona_extraction/cli.py`
  - 新增 `--background`、`--max-runtime` 参数
  - 启动前 PID 锁检查 + git 工作区预检

- `.gitignore` — 排除 `.extraction.lock` 和 `extraction.log`

## 3. 文档更新

- `docs/requirements.md` — 新增 §11.8 运行保障（后台运行、进程互斥、
  自我保护、进度可观测）；§11.6 明确 squash merge
- `docs/architecture/extraction_workflow.md` — 新增运行保障段落；
  明确 squash merge；修复乱码
- `ai_context/current_status.md` — 更新 Phase 3 进度、40 batches、
  orchestrator 新功能描述
- `ai_context/handoff.md` — 续接点改为 --resume，CLI 示例含
  --background/--max-runtime
- `ai_context/decisions.md` — #25 补充 squash merge
- `ai_context/architecture.md` — 补充 squash merge
- `automation/README.md` — 新增后台运行、运行时限制、进程保护章节

## 关键设计决策

- 后台运行用 `Popen(start_new_session=True)` 而非 nohup/screen，
  无外部依赖
- PID 锁在进程死亡后自动清理（检测 `/proc/{pid}` 是否存在）
- `--max-runtime` 在 batch 间检查而非打断进行中的 batch，保证数据一致性
- progress 文件在 git commit 前写入 committed 状态，确保回滚后状态一致
