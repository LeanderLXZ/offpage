# 自动化提取编排器

用脚本驱动 Claude Code CLI（或 Codex CLI）自动完成多阶段的 1+N 并行提取（世界 + 角色全并行）。

## 架构

```
orchestrator.py    ← 主循环：分析 → 用户确认 → 提取循环
                    │
  ┌─────────────────┼──────────────────┐
  │                 │                  │
  ▼                 ▼                  ▼
提取 agent     程序化后处理        并行审校通道
(claude -p)    (digest/catalog     (world + 各角色独立)
               0 token)            ┌──────────────┐
                                   │ 校验 → 审校   │
                                   │ → 修复(可选)  │
                                   └──────┬───────┘
                                          ▼
                                     提交门控
                                  (程序化, 0 token)
                                          │
                                   ┌──────┴──────┐
                                   ▼             ▼
                              git commit    失败 lane 独立重试
```

每个 stage 的流程：

1. Git preflight check（工作区干净、分支正确）
2. **智能跳过**：若产物已在磁盘（world + 各角色 snapshot），直接跳到 3
3. 构建 prompt → 运行 1+N 提取 agent（世界 + 各角色全并行，无先后依赖）
4. **程序化后处理**：L1 JSON 修复 + 生成 memory_digest + 生成 world_event_digest + 更新 stage_catalog
5. **并行审校通道**（world + 各角色各一条通道）：
   - 每条通道独立：程序化校验 → 语义审校 → 定点修复（如需）
   - 通道间并行运行，互不阻塞
6. **提交门控**（程序化，0 token）：确认全通道 PASS + 交叉一致性检查；
   失败时按 category 级联恢复（详见 `docs/requirements.md §11.4b 失败处理 B`）
7. **失败分级**（lane 独立重试优先，全量回滚为最后手段）：
   - 通道内可修复（schema 层或小范围字段错误）→ autofix → 定点修复 → 再审校 → 继续
   - 通道内不可修复（系统性偏差、修复瀑布走完仍 FAIL）→ **仅该 lane 回滚产物**
     + 该 lane 单独重提取（≤ `lane_max_retries`=2 次），已通过 lane 保留
   - 提交门控失败按 category 路由：
     - `catalog_missing` / `digest_missing` → **post_processing 重跑**（免费）+ 重新过门控
     - `snapshot_*` / `lane_review` → 仅该 lane 回滚重提取
       （与审校失败共享 `lane_retries` 配额）
     - 无 lane 归属或配额耗尽 → 全 stage rollback
   - 任一 lane 耗尽 `lane_max_retries` 仍失败 → **全 stage rollback**
     + 标记 FAILED → 进入 stage 级重试（≤ `max_retries`=2 次）

## 依赖

- Python >= 3.11
- `jsonschema`（**必需**）—— 所有机器的程序化门控强度必须一致；未装则
  import 时直接报错。详见 `docs/requirements.md §11.4`

```bash
pip install jsonschema   # 一次性，必需
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
    --end-stage 5

# 调整 Phase 0/Phase 4 并发数（默认 10）
python -m automation.persona_extraction "<work_id>" \
    -c 角色A 角色B --concurrency 5
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
tail -f works/<work_id>/analysis/progress/extraction.log

# 停止（优雅退出，保存进度并释放锁）
kill <PID>
```

`--background` 要求 `--resume` 或 `--characters`（后台无法交互）。

### 运行时限制

```bash
# 最多跑 120 分钟后优雅停止
python -m automation.persona_extraction "<work_id>" --resume --max-runtime 120
```

到达时限后会在当前 stage 结束时停止，不会中途打断。

## 进程保护

### 互斥锁

启动时自动检查是否已有正在运行的提取任务（通过 PID lockfile）。如果有，
拒绝启动并显示已有进程信息。锁文件位于：

```
works/{work_id}/analysis/.extraction.lock
```

进程正常退出或被 `kill` 时自动释放锁。如果进程异常死亡（如 OOM），下次
启动时会检测到死进程并自动清理过期锁。

### 子进程超时

- 提取 agent：3600 秒（60 分钟）超时后自动 kill
- 审校 agent：600 秒（10 分钟）超时后自动 kill
- 每个 stage 最多重试 2 次

### 进度监控

运行时每 30 秒显示心跳，包含：

- 已用时间
- 子进程 PID
- 子进程和编排器的内存占用（RSS）
- 分步耗时预估（从第 2 个 stage 开始）

## 目录结构

```
automation/
├── pyproject.toml
├── README.md
├── prompt_templates/               ← 提取和审校的 prompt 模板
│   ├── analysis.md
│   ├── world_extraction.md         ← 世界层提取（与角色并行）
│   ├── character_extraction.md     ← 角色层提取（与世界并行）
│   ├── semantic_review_world.md    ← 世界层语义审校（per-lane）
│   ├── semantic_review_character.md ← 角色层语义审校（per-lane）
│   ├── semantic_review.md          ← 统一审校兜底模板
│   ├── targeted_fix.md             ← 定点修复
│   ├── coordinated_extraction.md   ← reviewer / targeted-fix 共享的读取清单来源
│   └── scene_split.md
└── persona_extraction/             ← Python 包
    ├── __init__.py
    ├── cli.py                      ← CLI 入口
    ├── orchestrator.py             ← 主循环
    ├── llm_backend.py              ← Claude/Codex 后端抽象
    ├── progress.py                 ← 进度追踪和状态机
    ├── validator.py                ← 程序化校验（不花 token）
    ├── post_processing.py          ← 程序化后处理（digest/catalog）
    ├── review_lanes.py             ← 并行审校通道 + 提交门控
    ├── json_repair.py              ← 三级 JSON 修复（见下）
    ├── prompt_builder.py           ← 上下文感知的 prompt 组装
    ├── consistency_checker.py      ← 跨阶段一致性检查（Phase 3.5）
    ├── git_utils.py                ← Git 安全操作
    └── process_guard.py            ← PID 锁、内存监控、后台启动
```

## 进度文件

进度文件存储在 `works/{work_id}/analysis/progress/` 下：

- `pipeline.json` — 流水线总进度（各 phase 完成状态）
- `phase0_summaries.json` — Phase 0 各 chunk 状态
- `phase3_stages.json` — Phase 3 各 stage 状态机
- `phase4_scenes.json` — Phase 4 各章节状态

Phase 3 stage 状态机：

```
pending → extracting → extracted → post_processing → reviewing → passed → committed
              │                                          │
              └→ error                                   └→ failed → retrying → extracting
```

## JSON 自动修复

LLM 产出的 JSON 经常有格式问题（内容完整但解析失败）。管线内置三级修复策略，
在判定失败和重跑之前自动尝试：

| 级别 | 方法 | 成本 | 处理 |
|------|------|------|------|
| L1 | 程序化正则 | 0 token | 未转义内部引号、尾部逗号、截断、尾部垃圾 |
| L2 | LLM 修 JSON（只发坏 JSON，不重读原文，600s） | 少量 token | L1 无法处理的复杂格式问题 |
| L3 | 完整重跑（最多 1 次） | 全量 token | L1+L2 均失败时自动触发 |

L2 超时默认 600s（`repair_timeout` 参数可配置）。

集成位置：
- Phase 0：chunk 写后验证先 L1→L2 修复，仍失败则 L3 全量重跑；
  全部 chunk 完成后门控检查，有缺失阻断 Phase 1
- Phase 3：`validator.py` 的 `_load_json()` 自动修复 JSON，JSONL 逐行修复

代码：`persona_extraction/json_repair.py`

## 断点恢复

脚本可以在任何状态安全中断：

- `Ctrl+C` / `kill <PID>` → 保存当前进度、释放锁后退出
- `--max-runtime` 到期 → 当前 stage 结束后优雅停止
- Rate limit → 自动等待后重试（递增退避）
- **Token/context limit → 不重试**（相同 prompt 必定再次超限），直接标记
  ERROR 并回滚，避免浪费重试配额
- 脚本崩溃 → 重启后加 `--resume` 从最后一个 committed stage 继续
- 提取失败 → 自动回滚未提交的文件变更（全仓库范围，不仅限于 `works/`）
- **Baseline 恢复**：`--resume` 时自动检测 Phase 2.5 baseline 是否完成，
  缺失则补跑，避免后续 stage 因缺少 identity.json 而全部失败
- **Baseline 出口验证**：Phase 2.5 完成后运行 `validate_baseline()`
  校验 schema + required 字段非空，阻断不合格的 baseline 进入 Phase 3
- **磁盘对账自愈**：每次启动加载 progress 后自动调用 `reconcile_with_disk()`
  对账（Phase 0/3/4 全覆盖）。规则：(1) 终态但产物缺失 → 回退 PENDING；
  (2) PENDING 但磁盘有产物 → 清掉产物（视为不完整的半成品）；
  (3) 任意中间态 → 清产物 + 回退。Phase 3 额外用 `git cat-file -e` 校验
  `committed_sha` 是否仍可达，reset/rebase 丢掉的 commit 视同产物缺失
- **Phase 3 progress 自愈**：若 Phase 2 已完成但 `phase3_stages.json`
  缺失或损坏，从 `stage_plan.json` 重建（全部 stage 标 pending），避免
  落到 fresh-start 路径重新提示选角色 + 覆写 pipeline.json
- Resume 时自动重置 blocked stage（retry 耗尽的），无需手动编辑 progress
- **Progress 与 `--end-stage` 分离**：progress 始终包含完整 stage plan，
  `--end-stage` 仅控制本次执行范围（同 Phase 4 模式）
- **`--end-stage` 严格前缀语义**：Phase 3 命中 `--end-stage` 停止时，**不会**
  触发 Phase 3.5、squash-merge 提示或 Phase 4 —— 这些收尾步骤只在所有
  stage 均 `COMMITTED` 后执行。前缀运行结束时仅打印"继续运行即可完成"的提示
- **提交顺序契约**：stage 在 git commit 成功（拿到真实 SHA）后才迁移到
  `COMMITTED`；`git commit` 返回空 SHA（空 diff 或 commit 失败）则状态
  回退到 `FAILED`，避免产生"状态已 commit 但 git 里没有对应 object"的伪
  committed 漂移

## Phase 3.5：跨阶段一致性检查

Phase 3 全部 stage 提交后自动运行。包含 8 项程序化检查（零 token），
可选 LLM 裁定标记项。产出 `consistency_report.json`。有 error 级别问题时
阻断 Phase 4，需人工处理后继续。target_map 样本数检查使用
importance-based 阈值（主角≥5, 重要配角≥3, 其他≥1）。

代码：`persona_extraction/consistency_checker.py`

## Phase 4：场景切分

Phase 4 与 Phase 3 数据独立——使用独立 PID 锁 `.scene_archive.lock`，
可与 Phase 3 并行运行（`--start-phase 4`）。Phase 4 自身不做 git 操作；其中间目录
`works/{work_id}/analysis/scene_splits/` 和 lock 文件均为
本地忽略产物（**不得被 git track**），Phase 3 的 rollback 不会清掉它们。
每次启动通过 `reconcile_with_disk()` 校验 passed 章节的 split 文件是否
实际存在，缺失的自动重置为 pending；同时清掉 PENDING/中间态遗留的半成品。
前置条件仅为 `stage_plan.json`（Phase 1 产物）。

**运行方式**：

```bash
# 独立运行 Phase 4
python -m automation.persona_extraction "<work_id>" --start-phase 4

# 恢复断点
python -m automation.persona_extraction "<work_id>" --start-phase 4 --resume

# 只处理前 5 个 stage 的章节，并发 20
python -m automation.persona_extraction "<work_id>" \
    --start-phase 4 --end-stage 5 --concurrency 20
```

**工作流**：
- 每章一次 `claude -p`，LLM 标注场景边界 + 元数据（不输出 full_text）
- 程序根据行号从原文提取 full_text
- 多章并行执行（`--concurrency`，默认 10）
- 仅程序化校验（行号有效、不重叠、覆盖全章；alias 匹配可选——scene archive
  是 work-level 产物，不限于提取目标角色集）
- 全部完成后合并为 `works/{work_id}/retrieval/scene_archive.jsonl`
- `scene_id` 格式：`SC-S{stage:03d}-{seq:02d}`（如 `SC-S003-07`）；阶段号从
  `stage_plan.json` 查得（stage_plan 是唯一真源），seq 在每阶段内
  从 01 递增（上限 99）

**产出**：
- 最终：`works/{work_id}/retrieval/scene_archive.jsonl`（.gitignore）
- 中间：`works/{work_id}/analysis/scene_splits/`（每章一个 JSON，.gitignore）
- 进度：`works/{work_id}/analysis/progress/phase4_scenes.json`
- 锁：`works/{work_id}/analysis/.scene_archive.lock`

代码：`persona_extraction/scene_archive.py`
