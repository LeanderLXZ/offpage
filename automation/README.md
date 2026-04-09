# 自动化提取编排器

用脚本驱动 Claude Code CLI（或 Codex CLI）自动完成多批次的 1+N 分层提取（世界 → 角色并行）。

## 架构

```
orchestrator.py    ← 主循环：分析 → 用户确认 → 提取循环
                    │
  ┌─────────────────┼──────────────────┐
  │                 │                  │
  ▼                 ▼                  ▼
提取 agent      reviewer agent     程序化校验
(claude -p)     (claude -p)        (Python/jsonschema)
                    │
               ┌────┴────┐
               ▼         ▼
          定点修复    全量回滚
         (局部问题)  (系统性问题)
```

每个 batch 的流程：

1. Git preflight check（工作区干净、分支正确）
2. 构建 prompt（含文件清单、前批参照、schema 引用）
3. 运行提取 agent（`claude -p`，无人值守）
4. **JSON 修复**（如果输出格式有问题，先尝试自动修复再决定是否重跑）
5. 程序化校验（JSON schema + 结构完整性，不花 token）
6. 语义审校（独立 agent 检查质量和一致性）
7. **失败分级**：
   - 局部问题（≤5 个具体字段错误）→ 定点修复 agent → 再校验 → commit
   - 系统性问题（文件缺失/结构错误/理解偏差）→ rollback + 全量重试

## 依赖

- Python >= 3.11
- `jsonschema`（可选，用于程序化校验。不装也能跑，只是跳过 schema 校验）

```bash
pip install jsonschema   # 一次性，可选
```

## 使用

所有命令从**项目根目录**运行：

```bash
cd /path/to/persona-engine
```

### 完整流程（从分析到提取）

```bash
# work_id 即 sources/works/ 下的目录名
python -m automation.persona_extraction "<work_id>"

# 指定 backend 和 model
python -m automation.persona_extraction "<work_id>" -b claude -m opus

# 预设参数（跳过交互选角色）
python -m automation.persona_extraction "<work_id>" \
    -c 角色A 角色B \
    --end-batch 5
```

### 断点续跑

```bash
python -m automation.persona_extraction "<work_id>" --resume
```

### 使用 Codex

```bash
python -m automation.persona_extraction "<work_id>" -b codex
```

### 混合（Claude 提取 + Codex 审校）

```bash
python -m automation.persona_extraction "<work_id>" -b claude --reviewer-backend codex
```

### 后台运行（SSH 安全）

```bash
# 后台运行，SSH 断开后继续，最多跑 6 小时
python -m automation.persona_extraction "<work_id>" \
    --resume --background --max-runtime 360

# 跟踪日志
tail -f works/<work_id>/analysis/incremental/extraction.log

# 停止（优雅退出，保存进度并释放锁）
kill <PID>
```

`--background` 要求 `--resume` 或 `--characters`（后台无法交互）。

### 运行时限制

```bash
# 最多跑 120 分钟后优雅停止
python -m automation.persona_extraction "<work_id>" --resume --max-runtime 120
```

到达时限后会在当前 batch 结束时停止，不会中途打断。

## 进程保护

### 互斥锁

启动时自动检查是否已有正在运行的提取任务（通过 PID lockfile）。如果有，
拒绝启动并显示已有进程信息。锁文件位于：

```
works/{work_id}/analysis/incremental/.extraction.lock
```

进程正常退出或被 `kill` 时自动释放锁。如果进程异常死亡（如 OOM），下次
启动时会检测到死进程并自动清理过期锁。

### 子进程超时

- 提取 agent：3600 秒（60 分钟）超时后自动 kill
- 审校 agent：600 秒（10 分钟）超时后自动 kill
- 每个 batch 最多重试 2 次

### 进度监控

运行时每 30 秒显示心跳，包含：

- 已用时间
- 子进程 PID
- 子进程和编排器的内存占用（RSS）
- 分步耗时预估（从第 2 个 batch 开始）

## 目录结构

```
automation/
├── pyproject.toml
├── README.md
├── prompt_templates/          ← 提取和审校的 prompt 模板
│   ├── analysis.md
│   ├── world_extraction.md    ← 世界层提取 (Phase A)
│   ├── character_extraction.md ← 角色层提取 (Phase B, 并行)
│   ├── coordinated_extraction.md ← (legacy, 保留兼容)
│   └── semantic_review.md
└── persona_extraction/        ← Python 包
    ├── __init__.py
    ├── cli.py                 ← CLI 入口
    ├── orchestrator.py        ← 主循环
    ├── llm_backend.py         ← Claude/Codex 后端抽象
    ├── progress.py            ← 进度追踪和状态机
    ├── validator.py           ← 程序化校验（不花 token）
    ├── json_repair.py         ← 三级 JSON 修复（见下）
    ├── prompt_builder.py      ← 上下文感知的 prompt 组装
    ├── consistency_checker.py ← 跨批次一致性检查（Phase 3.5）
    ├── git_utils.py           ← Git 安全操作
    └── process_guard.py       ← PID 锁、内存监控、后台启动
```

## 进度文件

自动生成在 `works/{work_id}/analysis/incremental/extraction_progress.json`。

状态机：

```
pending → extracting → extracted → reviewing → passed → committed
              │                       │
              └→ error                └→ failed → retrying → extracting
```

## JSON 自动修复

LLM 产出的 JSON 经常有格式问题（内容完整但解析失败）。管线内置三级修复策略，
在判定失败和重跑之前自动尝试：

| 级别 | 方法 | 成本 | 处理 |
|------|------|------|------|
| L1 | 程序化正则 | 0 token | 未转义内部引号、尾部逗号、截断、尾部垃圾 |
| L2 | LLM 修 JSON（只发坏 JSON，不重读原文） | 少量 token | L1 无法处理的复杂格式问题 |
| L3 | 完整重跑 | 全量 token | 内容确实缺失时才触发 |

集成位置：
- Phase 0：chunk 跳过检查和写后验证均先尝试修复
- Phase 3：`validator.py` 的 `_load_json()` 自动修复 JSON，JSONL 逐行修复

代码：`persona_extraction/json_repair.py`

## 断点恢复

脚本可以在任何状态安全中断：

- `Ctrl+C` / `kill <PID>` → 保存当前进度、释放锁后退出
- `--max-runtime` 到期 → 当前 batch 结束后优雅停止
- Rate limit → 自动等待后重试（递增退避）
- **Token/context limit → 不重试**（相同 prompt 必定再次超限），直接标记
  ERROR 并回滚，避免浪费重试配额
- 脚本崩溃 → 重启后加 `--resume` 从最后一个 committed batch 继续
- 提取失败 → 自动回滚未提交的文件变更（全仓库范围，不仅限于 `works/`）
- **Baseline 恢复**：`--resume` 时自动检测 Phase 2.5 baseline 是否完成，
  缺失则补跑，避免后续 batch 因缺少 identity.json 而全部失败
- **REVIEWING 中断恢复**：恢复到 REVIEWING 状态时先验证提取产物仍在磁盘，
  文件缺失则自动回退重新提取
- Resume 时自动重置 blocked batch（retry 耗尽的），无需手动编辑 progress
- **Progress 与 `--end-batch` 分离**：progress 始终包含完整 batch plan，
  `--end-batch` 仅控制本次执行范围（同 Phase 4 模式）

## Phase 3.5：跨批次一致性检查

Phase 3 全部 batch 提交后自动运行。包含 8 项程序化检查（零 token），
可选 LLM 裁定标记项。产出 `consistency_report.json`。有 error 级别问题时
阻断 Phase 4，需人工处理后继续。

代码：`persona_extraction/consistency_checker.py`

## Phase 4：场景切分

Phase 4 与 Phase 3 完全独立——前置条件仅为 `source_batch_plan.json`
（Phase 1 产物）。

**运行方式**：

```bash
# 独立运行 Phase 4
python -m persona_extraction "我和女帝的九世孽缘" -r .. --start-phase 4

# 恢复断点
python -m persona_extraction "我和女帝的九世孽缘" -r .. --start-phase 4 --resume

# 只处理前 5 个 batch 的章节，并发 20
python -m persona_extraction "我和女帝的九世孽缘" -r .. \
    --start-phase 4 --end-batch 5 --concurrency 20
```

**工作流**：
- 每章一次 `claude -p`，LLM 标注场景边界 + 元数据（不输出 full_text）
- 程序根据行号从原文提取 full_text
- 多章并行执行（`--concurrency`，默认 10）
- 仅程序化校验（行号有效、不重叠、覆盖全章、alias 匹配）
- 全部完成后合并为 `works/{work_id}/rag/scene_archive.jsonl`
- `scene_id` 格式：`scene_{chapter}_{seq}`（如 `scene_0015_003`）

**产出**：
- 最终：`works/{work_id}/rag/scene_archive.jsonl`（.gitignore）
- 中间：`works/{work_id}/analysis/incremental/scene_archive/`（进度 + splits）

代码：`persona_extraction/scene_archive.py`
