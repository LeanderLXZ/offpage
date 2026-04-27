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

1. Git preflight check（工作区干净、分支 = `extraction/{work_id}`）
2. **智能跳过**：若产物已在磁盘（world + 各角色 snapshot），直接跳到 3
3. 构建 prompt → 运行 1+2N 提取 agent（1 world + N char_snapshot + N char_support，全并行无先后依赖）
4. **程序化后处理**：生成 memory_digest + 生成 world_event_digest + 更新 stage_catalog
5. **Repair Agent**（统一检测+修复，详见 `docs/requirements.md §11.4`）：
   - Phase A：四层检查（L0 JSON 语法 → L1 schema → L2 结构 → L3 语义）
   - Phase B：修复循环，按 tier 逐层升级（T0 程序化 → T1 局部 LLM → T2 原文 LLM → T3 全文件重生成，T3 全局每文件最多 1 次）。每轮末嵌 **L3 gate** 对"本轮改过的语义问题文件"再跑一次 L3，防止谎报
   - Phase C：最终确认——优先复用最后一次 gate 的结果（无新增 LLM 调用）
   - 安全阀：回归保护、收敛检测、总轮次限制
   - 全部通过 → git commit；有 error 级别问题未解决 → stage ERROR

## 依赖

- Python >= 3.11
- `jsonschema`（**必需**）—— 所有机器的程序化门控强度必须一致；未装则
  import 时直接报错。详见 `docs/requirements.md §11.4`

```bash
pip install jsonschema   # 一次性，必需
```

## 配置

所有可调参数集中在 `automation/config.toml`，加载入口
`persona_extraction/config.py::load_config()`。覆盖优先级（高→低）：

```
CLI flag  >  config.local.toml  >  config.toml  >  代码默认值
```

`config.local.toml`（同目录、git-ignored）按键覆盖 `config.toml`，
适合在不同部署机调整阈值而不污染版本库。

主要分段：

- `[stage]` 章节数边界（target/min/max）
- `[phase0]` chunk 并发、L2 修复超时
- `[phase1]` stage_plan 出口验证重试上限
- `[phase3]` 提取 / 审校超时、`max_turns`
- `[phase4]` 章节并发、短路熔断阈值
- `[repair_agent]` 各 tier 重试次数、T3 全局上限、triage 接受上限、总轮数、per-file 并发度（`repair_concurrency`，默认 10）
- `[backoff]` 快速空失败退避序列
- `[rate_limit]` Token 限额暂停策略（reset 缓冲、DST 感知时区解析、
  解析失败 fallback、周限额上限/动作、probe leader 选举 TTL、probe
  会话累计等待硬停 `probe_max_wait_h`）
- `[runtime]` 默认 runtime 上限、心跳间隔、默认 backend
- `[logging]` `failed_lanes/` 保留天数
- `[git]` extraction 分支前缀、squash-merge 目标分支（默认 `library`）、auto squash-merge 开关

## 使用

所有命令从**项目根目录**运行：

```bash
cd /path/to/offpage
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
tail -f works/<work_id>/analysis/progress/extraction_logs/extraction.log

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

## 分支纪律

代码 / schema / prompt / docs / `ai_context/` 的修改一律在 `main` 提交，
然后从 extraction 分支 `git merge main` 同步；提取数据（baseline +
Phase 3+ 产物）只在 `extraction/{work_id}` 上 commit。详见
`ai_context/architecture.md §Git Branch Model`。

orchestrator 自动落实这条纪律：

- **进入**：`run_extraction_loop` / `run_full` 开头调 `create_extraction_branch`
  切到（或新建）`extraction/{work_id}`。
- **退出**：建分支 + baseline rerun + Phase 3 循环整体包在
  `try / finally: checkout_main(...)` 内，任何退出路径（DONE / BLOCKED /
  `--end-stage` / Ctrl+C / 异常 / `sys.exit`）工作树都回到 `main`。
- **Dirty guard**：`checkout_main` / `preflight_check` 都接受可选
  `scope_paths` 参数，orchestrator 传入 `["works/{work_id}/"]`——
  只有 scope 内（即 extraction commit 路径内）的脏文件才阻断切换 /
  拒绝启动；scope 外的脏改动（IDE 临时文件、其他无关本地改动等）
  被静默容许。无 scope 时退化为整树 clean 检查。保留"半 stage
  产物不跟到 `main`"的不变量，避免被无关脏文件拦停。
- **异常检测**：SessionStart Claude Code hook
  （`.claude/hooks/session_branch_check.sh`）在每次新会话启动时检测
  "非 main 分支 + 无 orchestrator 进程" 的异常组合并提示。
- **squash-merge**：全部 stage COMMITTED 后，`_offer_squash_merge` 交互式
  询问是否 squash-merge 到 `library`（默认目标，由 `[git].squash_merge_target`
  控制；`[git].auto_squash_merge=true` 时自动执行）。三分支模型下作品
  artefact 永久归档在本地 `library` 分支，**不回流 `main`**，保持远程
  仓库只承载框架。`library` 分支由 `_offer_squash_merge` 在首次 squash 时
  按需自动从 main 创建（lazy + idempotent），无需手工 `git branch
  library main` 初始化。
- **squash 后 dispose（交互）**：squash 成功后 `_offer_squash_merge` 紧接着
  追问 `Delete extraction/{work_id} branch and run 'git gc --prune=now'? [y/N]`
  （默认 N）。用户输入 `y` 才执行 `git branch -D extraction/{work_id}` +
  `git gc --prune=now`，回收历次 regen commit 占用的 blob；否则保留分支
  并打印手动命令提示。**分支删除是 destructive 操作**，即使
  `[git].auto_squash_merge=true` 也仍走交互路径，永远不会自动删分支。

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
│   ├── triage.py                   ← 源文件问题判定（引文逐字校验）
│   ├── notes_writer.py             ← SourceNote 原子追加到 extraction_notes/
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
    ├── validator.py                ← 程序化校验（Phase 2 baseline 校验）
    ├── post_processing.py          ← 程序化后处理（digest/catalog）
    ├── json_repair.py              ← Phase 0 JSON 修复
    ├── prompt_builder.py           ← 上下文感知的 prompt 组装
    ├── consistency_checker.py      ← 跨阶段一致性检查（Phase 3.5）
    ├── git_utils.py                ← Git 安全操作
    └── process_guard.py            ← PID 锁、内存监控、后台启动
```

## 进度文件

进度文件存储在 `works/{work_id}/analysis/progress/` 下，按用途分类放在子目录：

- `pipeline.json` — 流水线总进度（各 phase 完成状态）
- `phase0_summaries.json` — Phase 0 各 chunk 状态
- `phase3_stages.json` — Phase 3 各 stage 状态机
- `phase4_scenes.json` — Phase 4 各章节状态
- `extraction_logs/extraction.log{,.1,.2,...}` — orchestrator 主日志（`--background` 模式 stderr 重定向；`extraction_log_backup_count` 控制轮转保留数）
- `repair_logs/repair_{stage_id}_{slug(file)}.jsonl` — Phase 3 repair_agent 每文件结构化事件日志
- `failed_lanes/{stage_id}__{lane_type}_{lane_id}__{pid}.log` — 失败 lane 单独日志
- `rate_limit_pause.json` / `.lock` — 订阅 rate limit 暂停状态（`RateLimitController` 进程单例 + flock）

Phase 3 stage 状态机（详见 `persona_extraction/progress.py` 顶部 docstring）：

```
pending → extracting → extracted → post_processing → reviewing
                │                                          │
                └→ error ← failed                         ├→ passed → committed
                     │                                     │
                     └→ pending (--resume)                 └→ failed → error
```

无 stage 级重试（不存在 `retrying` 状态）：repair 循环由 `repair_agent`
内部吸收；`failed` 的唯一出边是 `error`，`error` 的唯一出边是 `pending`
（通过 `--resume`）。`passed → failed` 由提交顺序契约触发——`git commit`
未返回 SHA（空 diff 或失败）时撤回提交并回到 `failed`，再落到 `error`。

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
| T3 | file_regen | 大量 token | 全文件 LLM 重生成（最后手段，**全局每文件最多触发 1 次** `t3_max_per_file=1`） |

**三阶段运行**：Phase A 全量检查 → Phase B 修复循环（内嵌 **L3 gate**）
→ Phase C 最终确认。Phase B 每轮在 L0–L2 scoped recheck 之后，会对
"本轮被修改 + Phase A 有语义问题" 的文件集合再跑一次 L3，把语义结果
回灌进下一轮 issue 队列——避免 T1/T2/T3 谎报语义修复成功。Phase C
优先复用最后一次 gate 的结果，不再单独调用 L3。语义 LLM 成本 = Phase A
每文件 1 次 + Phase B 每轮最多 (被改的 L3 文件数) 次 + Phase C 0 次
（有 gate 复用时）。

**源文件问题 triage**（`triage_enabled=True`，默认开启）：某些 L3 残留其实是
源小说本身的 bug（作者矛盾、typo、名称/代称混用、世界规则冲突等），或者
L2 结构层发现字段条数不足且原文确实素材不够。两条 accept_with_notes 通道共用
单文件上限 `accept_cap_per_file=5`。

**Path A — L3 `source_inherent`（LLM）触发点**：
- **pre-T3**：若 `_run_fixer_with_escalation` 即将升级到 T3，先做一次 triage；
  全部接受则跳过 20 分钟的 T3
- **post-L3-gate**：每轮 L3 gate 出结果后，对 gate_blocking 再过一次 triage

**Path B — L2 `coverage_shortage`（程序，0 token）触发点**：
L2 `min_examples` 规则把 issue 降级为 `severity=warning + coverage_shortage=True`
并路由 `START_TIER=T2, MAX_TIER=T2`（跳过 T0/T1/T3）。T2 一次 source_patch
不足以补齐 → coordinator 调用 `Triager.build_coverage_shortage_verdict` 以
程序方式构造 `SourceNote`（`discrepancy_type="coverage_shortage"`），quote
取自该 stage 首章子串，0 LLM 调用。

接受的硬条件（程序校验，非 LLM 自述）：(1) issue 必须是 `semantic`（Path A）
或 `structural` + `coverage_shortage` flag（Path B）；(2) 引用 `chapter_number
+ line_range + 逐字 quote`，程序用 `chapter_text.find(quote) >= 0` 校验；
(3) 每文件接受上限 `accept_cap_per_file=5`（两条通道共用）；(4)
`discrepancy_type` 必须是闭集中之一（author_contradiction / typo /
name_mixup / pronoun_confusion / title_drift / time_shift / space_conflict
/ duplicated_passage / world_rule_conflict / death_state_conflict / logic_jump
/ coverage_shortage / other）。T2/T3 fixer prompts 带有 `source_inherent`
自报通道，可直接把证据交给 Path A triager 做 prior。接受的 issue 以
`SourceNote` 形式原子追加到 `{entity}/canon/extraction_notes/{stage_id}.jsonl`，
note_id 格式 `SN-S{stage:03d}-{seq:02d}`；stage 保持 COMMITTED，不新增状态。
**Runtime 不消费 extraction_notes/，仅审计。**

**T3_CORRUPTED 硬停**：T3 跑完后立即对被重写文件做 scoped L0–L2 检查；
发现任何 L0–L2 错误即中止 Phase B 并 FAIL，**不走 triage**——机械损坏
不可能是"源文件的错"。

代码：`repair_agent/`

### Phase 0 JSON 修复

Phase 0（章节归纳）仍使用 `persona_extraction/json_repair.py` 的三级修复
（L1 程序化 → L2 LLM → L3 全量重跑）。

### Phase 0 / Phase 1 / Phase 4 schema gate

每条 LLM 调用产物落盘后跑 jsonschema 校验，失败首条作为 prior_error
注入下一次 retry prompt（让 LLM 知道上次哪里 fail）。装置由各 phase 现有
retry 通路接住，不引入新模块：

| Phase | 校验装置 | retry 通路 |
|---|---|---|
| Phase 0 | `_chunk_validator()` in `orchestrator._summarize_chunk` ([schemas/analysis/chapter_summary_chunk.schema.json](../schemas/analysis/chapter_summary_chunk.schema.json)) | L3 全 chunk 重跑（max 1 次）；`build_summarization_prompt(prior_error=...)` 的 `{retry_note}` 槽注入 |
| Phase 1 | `_world_overview_validator()` / `_stage_plan_validator()` / `_candidate_characters_validator()` in `orchestrator.run_analysis` ([schemas/analysis/{world_overview,stage_plan,candidate_characters}.schema.json](../schemas/analysis/)) | 失败文件单独删除重生 + stage limit 违规合并到 `correction_feedback`；共享 `[phase1].exit_validation_max_retry` 预算 |
| Phase 4 | `_scene_split_validator()` in `scene_archive.validate_scene_split` ([schemas/analysis/scene_split.schema.json](../schemas/analysis/scene_split.schema.json)) | per-chapter 重跑（`[phase4].max_retries_per_chapter`）；`build_scene_split_prompt(prior_error=...)` 注入 |

详细决策依据 → `ai_context/decisions.md` #27b（Bounds-only-in-schema） + #27i（schema-gate-as-retry-trigger pattern）。

## 断点恢复

脚本可以在任何状态安全中断：

- `Ctrl+C` / `kill <PID>` → 保存当前进度、释放锁后退出
- `--max-runtime` 到期 → 当前 stage 结束后优雅停止；rate-limit 暂停时长
  **不计入** runtime
- **Rate limit / usage limit → 全局暂停**：写
  `works/{work_id}/analysis/progress/rate_limit_pause.json`，所有新 LLM
  请求阻塞到 reset；reset 后重发同一 prompt（**不消耗重试次数**）。
  解析失败时以最小 `claude -p "1" --max-turns 1` 探测；周限额等待 ≥
  `[rate_limit].weekly_max_wait_h`（默认 12h）→ 写
  `rate_limit_exit.log` 并 exit code 2。详见
  `docs/requirements.md` §11.13
- **Token/context limit → 不重试**（相同 prompt 必定再次超限），直接标记
  ERROR 并回滚，避免浪费重试配额
- 脚本崩溃 → 重启后加 `--resume` 从最后一个 committed stage 继续
- 提取失败 → 自动回滚未提交的文件变更（全仓库范围，不仅限于 `works/`）
- **Baseline 恢复**：`--resume` 时自动检测 Phase 2 baseline 是否完成，
  缺失则补跑，避免后续 stage 因缺少 identity.json 而全部失败
- **Baseline 出口验证**：Phase 2 完成后运行 `validate_baseline()`
  校验 schema + required 字段非空，阻断不合格的 baseline 进入 Phase 3
- **磁盘对账自愈**：每次启动加载 progress 后自动调用 `reconcile_with_disk()`
  对账（Phase 0/3/4 全覆盖）。规则：(1) 终态但产物缺失 → 回退 PENDING；
  (2) PENDING 但磁盘有产物 → 清掉产物（视为不完整的半成品）；
  (3) 任意中间态 → 清产物 + 回退。Phase 3 额外用 `git cat-file -e` 校验
  `committed_sha` 是否仍可达，reset/rebase 丢掉的 commit 视同产物缺失
- **Phase 3 progress 自愈**：若 Phase 1.5 已完成但 `phase3_stages.json`
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

Phase 3 全部 stage 提交后自动运行。包含 9 项程序化检查（零 token，含
`memory_digest.summary` ↔ timeline `digest_summary` 以及
`world_event_digest.summary` ↔ world `stage_events[i]` 两条 1:1 文本
等值 gate），可选 LLM 裁定标记项。产出 `consistency_report.json`，并在
extraction 分支上立即 commit（`phase3.5: consistency_report S###..S###`）。
有 error 级别问题时阻断 Phase 4，需人工处理后继续。target_map 样本数
检查使用 importance-based 阈值（主角≥5, 重要配角≥3, 其他≥1）。

代码：`persona_extraction/consistency_checker.py`

## Phase 4：场景切分

Phase 4 与 Phase 3 数据独立——使用独立 PID 锁 `.scene_archive.lock`，
可与 Phase 3 并行运行（`--start-phase 4`）。Phase 4 自身不做 git 操作；其中间目录
`works/{work_id}/analysis/scene_splits/` 和 lock 文件均为
本地忽略产物（**不得被 git track**）。
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
- 单次运行内 chapter 级 retry：FAILED 章节回插 retry_queue，下一次
  调度时携 prior_error 注入 prompt 重新切分。上限
  `[phase4].max_retries_per_chapter`（默认 2，总尝试数 = 1 + 该值）；
  超限升级为 ERROR，留待下一次 `--resume` 清零 retry_count 重新计数。
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
