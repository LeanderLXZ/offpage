# 自动化提取编排器

用脚本驱动 Claude Code CLI（或 Codex CLI）自动完成多阶段的 1+2N 并行提取（世界 + 角色快照 + 角色支持层全并行）。

## 架构

```
orchestrator.py    ← 主循环：分析 → 用户确认 → 提取循环
                    │
  ┌─────────────────┼──────────────────┐
  │                 │                  │
  ▼                 ▼                  ▼
提取 agent     程序化后处理        repair
(claude -p)    (digest/catalog     (统一检测+修复)
               0 token)            ┌──────────────┐
                                   │ L0–L3 检查    │
                                   │ T0–T2 修复    │
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
   - Phase B：单轮修复循环，按 issue 的 `(start_tier, max_tier)` rule 分层路由到三层就地修复器（T0 程序化 → T1 局部 LLM → T2 原文 LLM，无全文件重生成），每个 tier 至多 2 次尝试。每轮末嵌 **L3 gate** 对"本轮改过的语义问题文件"再跑一次 L3，防止谎报
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

所有可调参数集中在 `extraction/config.toml`，加载入口
`persona_extraction/core/config.py::load_config()`。覆盖优先级（高→低）：

```
CLI flag  >  config.local.toml  >  config.toml  >  代码默认值
```

`config.local.toml`（同目录、git-ignored）按键覆盖 `config.toml`，
适合在不同部署机调整阈值而不污染版本库。

主要分段：

- `[stage]` 章节数边界（target/min/max）
- `[phase0]` chunk 并发、summarize 子进程超时、L2 修复超时
- `[phase1]` stage_plan 出口验证重试上限
- `[phase2]` baseline lane fan-out 并发（`lane_concurrency`，默认 5）、
  输出缺失重跑上限（`output_missing_max_retry`）、per-lane repair 开关
  （`repair_enabled`，决策 #59 缩水版：T0/T1 + 程序 checker，不含
  T2/L3/triage）
- `[phase3]` 提取 / 审校超时、`max_turns`、`concurrency`（默认 **12**，
  覆盖 2 角色场景 sub-lane on 时峰值 `1 + 2×4 + 2 = 11`）、
  `char_snapshot_sub_lanes`（缺省 `true` — 单 char_snapshot lane 内部拆
  **4** 并行 sub-lane 跑同一份 prompt 模板的不同字段子集，merge 程序
  合并；prev snapshot 按 lane 切 4 个 slice 喂入避免每 sub-lane 读完整
  prev；CLI `--char-snapshot-sub-lanes` / `--no-char-snapshot-sub-lanes`
  覆盖；light_novel 模式 stage 字符数小可手动关；详见
  `docs/architecture/extraction_workflow.md` §6.2 sub-lane 字段归属表 +
  决策 #55）
- `[phase4]` 章节并发、短路熔断阈值
- `[repair]` 各 tier 重试次数（每 tier 封顶 2）、triage 接受上限、总轮数、per-file 并发度（`repair_concurrency`，默认 10）
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
python -m extraction.persona_extraction "<work_id>"

# 指定 backend 和 model
python -m extraction.persona_extraction "<work_id>" -b claude -m opus

# 预设参数（跳过交互选角色）
python -m extraction.persona_extraction "<work_id>" \
    -c 角色A 角色B \
    --end-stage 5

# 调整 Phase 0/Phase 4 并发数（默认 10）
python -m extraction.persona_extraction "<work_id>" \
    -c 角色A 角色B --concurrency 5
```

### 断点续跑

```bash
python -m extraction.persona_extraction "<work_id>" --resume
```

`--resume` 阶段无关：`run_full` 是 resume entry point，按 phase 顺序自检产物
（Phase 0 schema-gated 跳过已 done chunk / Phase 1 检测 stage_plan 等已落盘
产物 / Phase 1.5 用 preset / Phase 3 reconcile_with_disk + 从 stage_plan
self-heal phase3_stages.json）。`--resume` 本身只 silent 'Resume from existing
progress? [Y/n]' 这条交互确认；与磁盘上具体哪个 phase 已落盘无关。

### 使用 Codex

```bash
python -m extraction.persona_extraction "<work_id>" -b codex
```

### 混合（Claude 提取 + Codex 审校）

```bash
python -m extraction.persona_extraction "<work_id>" -b claude --reviewer-backend codex
```

### 后台运行（SSH 安全）

```bash
# 后台运行，SSH 断开后继续，最多跑 6 小时
python -m extraction.persona_extraction "<work_id>" \
    --resume --background --max-runtime 360

# 跟踪日志
tail -f works/<work_id>/analysis/progress/extraction_logs/extraction.log

# 停止（优雅退出，保存进度并释放锁）
kill <PID>
```

`--background` 阶段感知校验双分支：读 `works/<work_id>/analysis/progress/pipeline.json`
的 `phase_1_5` 状态——
- **未 done**：强制要求 `--characters`（跳过 `confirm_with_user` 的 character
  选择 stdin prompt；该 prompt 无 daemon-safe default，必须 preset）
- **已 done**：强制要求 `--resume` 或 `--characters` 二选一（避免 daemon
  撞 run_full 内 `'Resume from existing progress?'` 的 stdin 死锁——`--resume`
  silent 该 prompt，`--characters` 走 preset 旁路同样 silent）

`--end-stage` 不传 = 全跑（决策 #56）：CLI flag `default=None`，`confirm_with_user`
内 `Extract up to stage N` prompt 文案 `empty = all (no limit), 0 = baseline only`；
daemon EOFError 路径 `preset_end_stage = None` 兜底为"no limit"，与
`run_extraction_loop(max_stages=None)` 的合法语义一致。两分支共同保证 daemon
路径上**没有任何**可触发 traceback 的 stdin prompt。`--resume` 与 `--background`
正交：`--resume` 控制"silence the resume prompt"，`--background` 控制后台 daemonize。

### 运行时限制

```bash
# 最多跑 120 分钟后优雅停止
python -m extraction.persona_extraction "<work_id>" --resume --max-runtime 120
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
- **kill 的是整棵进程树**：子进程以 `start_new_session=True` 起在独立进程组，
  超时走 `killpg`。CLI backend 的 Bash 工具会派生继承管道的孙进程——只杀直接
  子进程会让它们攥着管道写端，收尾的 `communicate()` 就永远等不到 EOF，lane
  线程死锁（`--max-runtime` 非抢占式，救不了）。副作用：子进程不再接收终端
  Ctrl+C，停止运行请用 `kill <PID>`（见上方 §后台运行）。
- **停机（SIGINT / SIGTERM）会先杀在飞的子进程再放锁**：`terminate_all_children()`
  在 `_handle_interrupt` 里于 `lock.release()` **之前**跑。否则 lane 线程还阻塞在
  `communicate()` 上，进程要空转到子进程超时（≤ 3600s）才真正退出，而 PID 锁早已
  被删——那段时间里第二个 `--resume` 能启动并与之并发写同一 work tree。

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
extraction/
├── pyproject.toml
├── config.toml
├── README.md
├── persona_extraction/                       ← Python 包（CLI 入口 `python -m extraction.persona_extraction`）
│   ├── __init__.py / __main__.py
│   ├── cli.py                                ← CLI 入口
│   ├── orchestrator.py                       ← 主循环
│   ├── prompt_builder.py                     ← 上下文感知的 prompt 组装
│   ├── core/                                 ← 基础件
│   │   ├── config.py                         ← 配置加载（load_config）
│   │   ├── schema_loader.py                  ← schema $ref inline 化
│   │   ├── llm_backend.py                    ← Claude/Codex 后端抽象
│   │   ├── rate_limit.py                     ← Token 限额暂停（§11.13）
│   │   ├── git_utils.py                      ← Git 安全操作
│   │   ├── process_guard.py                  ← PID 锁、内存监控、后台启动
│   │   └── json_repair.py                    ← Phase 0 JSON 修复
│   ├── lifecycle/                            ← 横向状态机
│   │   ├── progress.py                       ← 进度追踪和状态机
│   │   ├── manifests.py                      ← works / world manifest 程序化写出
│   │   ├── lane_output.py                    ← Phase 3 lane 输出归并
│   │   └── failed_lane_log.py                ← 失败 lane 诊断日志
│   ├── phases/                               ← 相位特化
│   │   ├── scene_archive.py                  ← Phase 4 场景切分
│   │   ├── snapshot_merge.py                 ← char_snapshot 4 sub-lane 合并（决策 #55）
│   │   └── post_processing.py                ← 程序化后处理（digest/catalog）
│   ├── prompts/                              ← 提取的 prompt 模板
│   │   ├── summarization.md                  ← Phase 0 章节归纳
│   │   ├── analysis_foundation.md            ← Phase 1 lane: foundation (decision #54)
│   │   ├── analysis_stage_plan.md            ← Phase 1 lane: stage_plan (monolithic only)
│   │   ├── analysis_candidate_characters.md  ← Phase 1 lane: candidate_characters
│   │   ├── baseline_key_figures.md           ← Phase 2 lane A：key_figures 替换（先行，决策 #59）
│   │   ├── baseline_fixed_relationships.md   ← Phase 2 lane：fixed_relationships
│   │   ├── baseline_identity.md              ← Phase 2 per-char lane：identity + manifest
│   │   ├── baseline_target_baseline.md       ← Phase 2 per-char lane：target_baseline
│   │   ├── world_extraction.md               ← Phase 3 世界层提取
│   │   ├── character_snapshot_extraction.md  ← Phase 3 角色快照提取
│   │   ├── character_support_extraction.md   ← Phase 3 角色支持层提取
│   │   └── scene_split.md                    ← Phase 4 场景切分
│   └── tests/                                ← _smoke_*.py 集合
├── validation/                               ← 数据正确性框架（详见 validation/README.md）
│   ├── README.md
│   ├── __init__.py / types.py
│   ├── gates/                                ← 相位边界 validator（orchestrator 直调，不走 repair 循环）
│   │   ├── phase2_baseline.py                ← Phase 2 baseline 校验
│   │   └── phase3_5_consistency.py           ← Phase 3.5 跨 stage 一致性
│   └── shared/                               ← 纯函数原语（gates / repair.checkers 共享）
│       ├── importance.py                     ← importance_for_target / importance_min_examples
│       └── schema_tolerance.py               ← validate_with_length_tolerance / relaxed_schema_for_length
├── ingestion/                                ← 入库 gate
│   └── validator.py                          ← 源包 schema + 跨文件断言
└── repair/                                   ← 统一检测+修复系统
    ├── __init__.py                           ← 公共 API：run(), validate_only()
    ├── protocol.py                           ← 数据类：Issue, FileEntry, RepairConfig 等
    ├── coordinator.py                        ← 三阶段编排：check → fix → verify
    ├── tracker.py                            ← 跨轮次 Issue 追踪 + 安全阀
    ├── recorder.py                           ← repair_logs jsonl 事件落盘
    ├── field_patch.py                        ← json_path 字段级精确替换
    ├── context_retriever.py                  ← 原文定位（chapter_summaries → chapters）
    ├── triage.py                             ← 源文件问题判定（引文逐字校验）
    ├── notes_writer.py                       ← SourceNote 原子追加到 extraction_notes/
    ├── checkers/                             ← 四层检查器（L0–L3）
    │   ├── json_syntax.py                    ← L0：JSON 语法
    │   ├── schema.py                         ← L1：jsonschema 校验
    │   ├── structural.py                     ← L2：结构/业务规则
    │   ├── targets_keys_eq_baseline.py       ← L2：keys ⇔ target_baseline 双向断言
    │   └── semantic.py                       ← L3：LLM 语义审查
    ├── fixers/                               ← 三层修复器（T0–T2）
    │   ├── programmatic.py                   ← T0：程序化修复（0 token）
    │   ├── local_patch.py                    ← T1：局部 LLM 修复（不读原文）
    │   └── source_patch.py                   ← T2：原文辅助 LLM 修复
    └── tests/                                ← _smoke_*.py 集合
```

## 进度文件

进度文件存储在 `works/{work_id}/analysis/progress/` 下，按用途分类放在子目录：

- `pipeline.json` — 流水线总进度（各 phase 完成状态）
- `phase0_summaries.json` — Phase 0 各 chunk 状态
- `phase3_stages.json` — Phase 3 各 stage 状态机
- `phase4_scenes.json` — Phase 4 各章节状态
- `extraction_logs/extraction.log{,.1,.2,...}` — orchestrator 主日志（`--background` 模式 stderr 重定向；`extraction_log_backup_count` 控制轮转保留数）
- `repair_logs/repair_{stage_id}_{slug(file)}.jsonl` — Phase 3 repair 每文件结构化事件日志
- `failed_lanes/{stage_id}__{lane_type}_{lane_id}__{pid}.log` — 失败 lane 单独日志
- `rate_limit_pause.json` / `.lock` — 订阅 rate limit 暂停状态（`RateLimitController` 进程单例 + flock）

Phase 3 stage 状态机（详见 `persona_extraction/lifecycle/progress.py` 顶部 docstring）：

```
pending → extracting → extracted → post_processing → reviewing
                │                                          │
                └→ error ← failed                         ├→ passed → committed
                     │                                     │
                     └→ pending (--resume)                 └→ failed → error
```

无 stage 级重试（不存在 `retrying` 状态）：repair 循环由 `repair`
内部吸收；`failed` 的唯一出边是 `error`，`error` 的唯一出边是 `pending`
（通过 `--resume`）。`passed → failed` 由提交顺序契约触发——`git commit`
未返回 SHA（空 diff 或失败）时撤回提交并回到 `failed`，再落到 `error`。

## 检测与修复系统（Repair Agent）

Phase 3 的文件校验和修复由独立的 `repair` 模块负责。
各 phase 都通过统一接口调用，详见 `docs/requirements.md §11.4`。

**四层检查器**（L0–L3，分层依赖）：

| 层 | 名称 | 成本 | 检查内容 |
|---|------|------|---------|
| L0 | json_syntax | 0 token | 文件存在、UTF-8、JSON 解析、非空 |
| L1 | schema | 0 token | jsonschema 校验 |
| L2 | structural | 0 token | 业务规则（ID 格式、样本数、长度、一致性） |
| L3 | semantic | LLM | 事实准确性、逻辑一致性、跨阶段连续性。**LLM 调用失败 / 空响应 / 不可解析时不再视为 pass**——`SemanticReviewLLMUnavailable` 转成 blocking `semantic_unavailable`/`semantic_unparseable` issue，强制走修复路径而不是放行 |

**三层修复器**（T0–T2，按 rule 分层路由）：每个 issue 依类型带
`(start_tier, max_tier)` 路由信息（见 `protocol.route_tiers`），从
`start_tier` 起在其区间内逐层升级；每个 tier 至多 2 次尝试（第 2 次只
重打即时 re-verify 仍标记的字段），无全文件重生成层。

| 层 | 名称 | 成本 | 修复方式 |
|---|------|------|---------|
| T0 | programmatic | 0 token | 正则修 JSON、类型转换、ID 格式、缺失字段、`maxLength` 截断 |
| T1 | local_patch | 少量 token | 字段级 LLM 修复（不读原文） |
| T2 | source_patch | 中等 token | 字段级 LLM 修复（带原文章节） |

**三阶段运行**（单轮 Phase A→B→C，无 lifecycle 重置）：Phase A 全量检查
→ Phase B 修复循环（内嵌 **L3 gate**）→ Phase C 最终确认。Phase B 每轮
在 L0–L2 scoped recheck 之后，会对"本轮被修改 + Phase A 有语义问题"的
文件集合再跑一次 L3，把语义结果回灌进下一轮 issue 队列——避免 T1/T2
谎报语义修复成功。Phase C 优先复用最后一次 gate 的结果，不再单独调用
L3。语义 LLM 成本 = Phase A 每文件 1 次 + Phase B 每轮最多 (被改的 L3
文件数) 次 + Phase C 0 次（有 gate 复用时）。

**源文件问题 triage**（`triage_enabled=True`，默认开启）：某些 L3 残留其实是
源小说本身的 bug（作者矛盾、typo、名称/代称混用、世界规则冲突等），或者
L2 结构层发现字段条数不足且原文确实素材不够。两条 accept_with_notes 通道共用
单文件接受上限 `accept_cap_per_file=5`；磁盘 jsonl append-only。

**Path A — L3 `source_inherent`（LLM）触发点**：
- **post-cap（残留）**：capped tiers（T0–T2）跑完后、defer 之前，对残留的
  semantic issue 先做一次 triage，把源小说 bug 接受为 SourceNote
- **post-L3-gate**：每轮 L3 gate 出结果后，对 gate_blocking 再过一次 triage

**Path B — L2 `coverage_shortage`（程序，0 token）触发点**：
L2 `min_examples` 规则把 issue 降级为 `severity=warning + coverage_shortage=True`
并路由 `START_TIER=T2, MAX_TIER=T2`（跳过 T0/T1）。T2 一次 source_patch
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
/ coverage_shortage / other）。T2 fixer prompt 带有 `source_inherent`
自报通道，可直接把证据交给 Path A triager 做 prior。接受的 issue 以
`SourceNote` 形式原子追加到 `{entity}/canon/extraction_notes/{stage_id}.jsonl`，
note_id 格式 `SN-S{stage:03d}-{seq:02d}`；stage 保持 COMMITTED，不新增状态。
**Runtime 不消费 extraction_notes/，仅审计。**

**未决修复延后**（`[repair].defer_unresolved_semantic`，代码默认 false，本项目开）：
与 triage（源小说 bug）不同，这里处理"提取确有错但 capped tiers（T0–T2）
追不平"的残留。某 stage repair 收尾后，若**每个**失败文件残留的问题都可延后
——`error` 落在 `DEFERRABLE_CATEGORIES = {semantic, schema, structural,
cross_file}`，或是 `coverage_shortage` 薄内容残留（`severity=warning` 但仍
阻塞协调器，只看 severity 会让它因薄内容硬停机）——则不判 ERROR 停机：写台账
`works/{work_id}/analysis/deferred_repairs/{stage_id}.jsonl`（随 stage commit
提交），stage 当 PASS 继续。仍硬 ERROR 的两种：残留 `json_syntax`（文件不可
解析，阻断所有下游读取），以及 repair worker 崩溃。
判定**逐文件进行**而非把所有 issue 摊平——崩溃产生的合成结果 `issues=[]`
对摊平集合毫无贡献，按整池判会让崩溃文件搭兄弟文件可延后 issue 的顺风车
提交、且不进台账，Phase 3.5 收尾 pass 永远不会知道它。
台账留待 Phase 3.5 收尾修复 pass 逐条精准修（不重跑 stage）。判据 + 写出：
`persona_extraction/lifecycle/deferred_repair_log.py`。

代码：`repair/`

### Phase 0 / Phase 1 双模式调度

Phase 0/1 由 source manifest `structure_mode` 字段（`monolithic` / `light_novel`，
**必填**——schema required，缺省即校验失败；works manifest 在 Phase 1.5 从
source 拷字段，`read_structure_mode` 以 source 为权威，works/source 不一致
直接 raise）调度双路径——monolithic 走 token-budget chunking + LLM stage
边界发现；light_novel 走 1 sub-section = 1 chunk = 1 stage、stage_plan 由
orchestrator `_build_light_novel_stage_plan` 程序化 1:1 派生（zero LLM call）。

Phase 1 内部 fan-out 成独立 lane（详见决策 #52）：

- **monolithic = 3 lane 并行**：foundation / stage_plan / candidate_characters，每 lane 一次 `claude -p` + 预先裁剪的 chunks 子集 + 独立 schema gate + 独立 `prior_error` 注入式 retry（与 Phase 0 / Phase 4 同形态）。**foundation lane 输出 `works/<work_id>/world/foundation/foundation.json`**（决策 #54——foundation 由 phase 1 直接产到 world 域，phase 2 仅补 `major_factions[].key_figures`）；stage_plan + candidate_characters 仍输出 `works/<work_id>/analysis/`。
- **light_novel = 2 lane 并行 + 程序化 stage_plan**：foundation + candidate_characters 走 LLM lane；stage_plan 由 orchestrator `_build_light_novel_stage_plan` 直接落盘，**stage_plan lane 不调 LLM**
- per-lane retry 预算 = `[phase1].exit_validation_max_retry`（默认 2，per-lane 独立，不共享池）
- 单 lane fail 不影响其他 lane 已落盘产物；`--resume` 时 reconcile 跳过 schema-valid 产物，仅重跑失败 lane
- 裁剪 chunks 写到 `works/{work_id}/analysis/.phase1_lane_inputs/{lane}/chunk_NNN.json`（gitignored，run_analysis 退出时 cleanup）

详细规则与字段契约见
[../docs/architecture/extraction_workflow.md](../docs/architecture/extraction_workflow.md) §1-3
+ `ai_context/decisions.md` §27j/27k/27l/52。

### Phase 0 JSON 修复

Phase 0（章节归纳）仍使用 `persona_extraction/core/json_repair.py` 的三级修复
（L1 程序化 → L2 LLM → L3 全量重跑）。

### Phase 0 / Phase 1 / Phase 4 schema gate

每条 LLM 调用产物落盘后跑 jsonschema 校验，失败首条作为 prior_error
注入下一次 retry prompt（让 LLM 知道上次哪里 fail）。装置由各 phase 现有
retry 通路接住，不引入新模块：

| Phase | 校验装置 | retry 通路 |
|---|---|---|
| Phase 0 | `_chunk_validator()` in `orchestrator._summarize_chunk` ([schemas/analysis/chapter_summary_chunk.schema.json](../schemas/analysis/chapter_summary_chunk.schema.json)) | L3 全 chunk 重跑（max 1 次）；`build_summarization_prompt(prior_error=...)` 的 `{retry_note}` 槽注入 |
| Phase 1 | `_foundation_validator()` ([schemas/world/foundation.schema.json](../schemas/world/foundation.schema.json)) / `_stage_plan_validator()` / `_candidate_characters_validator()` per-lane in `orchestrator.run_analysis` fan-out ([schemas/analysis/{stage_plan,candidate_characters}.schema.json](../schemas/analysis/)) — foundation schema lives under `schemas/world/` per decision #54 (foundation 前移到 phase 1 + schema 合并入 world domain) | 失败 lane 把首条违规作为 `prior_error` 注入下一次重试 prompt（与 Phase 0 / Phase 4 同形态）；per-lane 独立 `[phase1].exit_validation_max_retry` 预算（不共享池）；用尽走 #48 length-tolerance 兜底 |
| Phase 2 | per-lane repair（schema checker + [repair/checkers/phase2_baseline_refs.py](repair/checkers/phase2_baseline_refs.py) 程序 checker；决策 #59 缩水版——T0/T1，L3/T2/triage 不开）+ 终点 `validate_baseline()`（[validation/gates/phase2_baseline.py](validation/gates/phase2_baseline.py)） | 输出缺失 → `[phase2].output_missing_max_retry` prior_error 重跑；schema / 引用违规 → repair T0/T1；终点 gate strict → #48 length-tolerance 兜底 |
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
  (2) Phase 0 终态但产物 partial / corrupt / schema-failing → 清产物 +
  回退 PENDING（与 skip 路径和 Phase-1 gate 共用同一份 schema-gated 完整性
  判据 `_chunk_passes_full_check`，确保半成品不能从任何一道关漏过）；
  (3) PENDING 但磁盘有产物 → 清掉产物（视为不完整的半成品）；
  (4) 任意中间态 → 清产物 + 回退。Phase 3 额外用 `git cat-file -e` 校验
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

代码：`extraction/validation/gates/phase3_5_consistency.py`

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
python -m extraction.persona_extraction "<work_id>" --start-phase 4

# 恢复断点
python -m extraction.persona_extraction "<work_id>" --start-phase 4 --resume

# 只处理前 5 个 stage 的章节，并发 20
python -m extraction.persona_extraction "<work_id>" \
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

代码：`persona_extraction/phases/scene_archive.py`
