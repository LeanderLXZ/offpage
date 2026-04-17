# 自动化提取编排器

用脚本驱动 Claude Code CLI（或 Codex CLI）自动完成多阶段的 1+2N 并行提取（世界 + 角色快照 + 角色支持层全并行）。

## 架构

```
orchestrator.py    ← 主循环：分析 → 用户确认 → 提取循环
                    │
  ┌─────────────────┼──────────────────┐
  │                 │                  │
  ▼                 ▼                  ▼
提取 agent     程序化后处理        repair_agent
(claude -p)    (digest/catalog     (统一检测+修复)
               0 token)            ┌──────────────┐
                                   │ L0–L3 检查    │
                                   │ T0–T3 修复    │
                                   │ 最终语义验证   │
                                   └──────┬───────┘
                                          ▼
                                     git commit
```

每个 stage 的流程：

1. Git preflight check（工作区干净、分支正确）
2. **智能跳过**：若产物已在磁盘（world + 各角色 snapshot），直接跳到 3
3. 构建 prompt → 运行 1+2N 提取 agent（1 world + N char_snapshot + N char_support，全并行无先后依赖）
4. **程序化后处理**：生成 memory_digest + 生成 world_event_digest + 更新 stage_catalog
5. **Repair Agent**（统一检测+修复，详见 `docs/requirements.md §11.4`）：
   - Phase A：四层检查（L0 JSON 语法 → L1 schema → L2 结构 → L3 语义）
   - Phase B：修复循环，按 tier 逐层升级（T0 程序化 → T1 局部 LLM → T2 原文 LLM → T3 全文件重生成）
   - Phase C：最终语义验证（仅 Phase A 有语义问题时触发）
   - 安全阀：回归保护、收敛检测、总轮次限制
   - 全部通过 → git commit；有 error 级别问题未解决 → stage ERROR

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
- Repair agent LLM 调用：600 秒（10 分钟）超时
- 修复循环总轮次限制（默认 5 轮），未解决 → stage ERROR

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
├── prompt_templates/               ← 提取的 prompt 模板
│   ├── analysis.md
│   ├── world_extraction.md              ← 世界层提取
│   ├── character_snapshot_extraction.md ← 角色快照提取
│   ├── character_support_extraction.md  ← 角色支持层提取
│   └── scene_split.md
├── repair_agent/                   ← 统一检测+修复系统
│   ├── __init__.py                 ← 公共 API：run(), validate_only()
│   ├── protocol.py                 ← 数据类：Issue, FileEntry, RepairConfig 等
│   ├── coordinator.py              ← 三阶段编排：check → fix → verify
│   ├── tracker.py                  ← 跨轮次 Issue 追踪 + 安全阀
│   ├── field_patch.py              ← json_path 字段级精确替换
│   ├── context_retriever.py        ← 原文定位（chapter_summaries → chapters）
│   ├── checkers/                   ← 四层检查器（L0–L3）
│   │   ├── json_syntax.py          ← L0：JSON 语法
│   │   ├── schema.py               ← L1：jsonschema 校验
│   │   ├── structural.py           ← L2：结构/业务规则
│   │   └── semantic.py             ← L3：LLM 语义审查
│   └── fixers/                     ← 四层修复器（T0–T3）
│       ├── programmatic.py         ← T0：程序化修复（0 token）
│       ├── local_patch.py          ← T1：局部 LLM 修复
│       ├── source_patch.py         ← T2：原文辅助 LLM 修复
│       └── file_regen.py           ← T3：全文件 LLM 重生成
└── persona_extraction/             ← Python 包
    ├── __init__.py
    ├── cli.py                      ← CLI 入口
    ├── orchestrator.py             ← 主循环
    ├── llm_backend.py              ← Claude/Codex 后端抽象
    ├── progress.py                 ← 进度追踪和状态机
    ├── validator.py                ← 程序化校验（Phase 2.5 baseline 校验）
    ├── post_processing.py          ← 程序化后处理（digest/catalog）
    ├── json_repair.py              ← Phase 0 JSON 修复
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

## 检测与修复系统（Repair Agent）

Phase 3 的文件校验和修复由独立的 `repair_agent` 模块负责。
各 phase 都通过统一接口调用，详见 `docs/requirements.md §11.4`。

**四层检查器**（L0–L3，分层依赖）：

| 层 | 名称 | 成本 | 检查内容 |
|---|------|------|---------|
| L0 | json_syntax | 0 token | 文件存在、UTF-8、JSON 解析、非空 |
| L1 | schema | 0 token | jsonschema 校验 |
| L2 | structural | 0 token | 业务规则（ID 格式、样本数、长度、一致性） |
| L3 | semantic | LLM | 事实准确性、逻辑一致性、跨阶段连续性 |

**四层修复器**（T0–T3，逐层升级）：

| 层 | 名称 | 成本 | 修复方式 |
|---|------|------|---------|
| T0 | programmatic | 0 token | 正则修 JSON、类型转换、ID 格式、缺失字段 |
| T1 | local_patch | 少量 token | 字段级 LLM 修复（不读原文） |
| T2 | source_patch | 中等 token | 字段级 LLM 修复（带原文章节） |
| T3 | file_regen | 大量 token | 全文件 LLM 重生成（最后手段） |

**三阶段运行**：Phase A 全量检查 → Phase B 修复循环 → Phase C 最终语义验证。
语义 LLM 最多调用 2 次（初检 + 终验），修复循环内只用 0-token 的 L0–L2 复检。

代码：`repair_agent/`

### Phase 0 JSON 修复

Phase 0（章节归纳）仍使用 `persona_extraction/json_repair.py` 的三级修复
（L1 程序化 → L2 LLM → L3 全量重跑）。

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
- Resume 时自动重置 ERROR stage → PENDING，无需手动编辑 progress
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
