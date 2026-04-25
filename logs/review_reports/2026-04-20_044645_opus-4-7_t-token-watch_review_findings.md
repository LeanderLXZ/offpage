# T-TOKEN-WATCH 落地后全仓对齐审计 findings

**时间**：2026-04-20 04:46 (America/New_York)
**Review 模型**：Claude Opus 4.7（`claude-opus-4-7`）
**范围**：commit d79dc7f 之后全仓 review（`ai_context/` / `docs/` / `schemas/` /
`prompts/` 规范线 + `automation/` / `simulation/` 实现线 + `works/` /
`users/_template/` 样例产物线）
**目的**：定位 T-TOKEN-WATCH + 单源 TOML config 落地后仍存在的 bug /
冲突 / 歧义 / 过时描述 / 未兑现承诺，便于后续按优先级处理

**本文件仅为 findings 记录，未修任何代码。**

---

## Findings（按严重性分组）

### HIGH（真实 bug / 严重不一致）

#### H1. `paused_seconds_total` 多 lane 并发累加 → `--max-runtime` 扣除量虚高

**结论**
`rate_limit.py:375` 的 `self._paused_seconds_total += slept` 在
ThreadPoolExecutor 的每个 worker 独立执行，N 个 lane 同时撞同一次暂停
时会把"同一段挂钟等待"累加 N 遍。

**为何是问题**
`orchestrator.py:309` 的 `_check_runtime_limit` 做
`elapsed_s -= self._rate_limit.paused_seconds_total`。
10 lane × 30 分钟暂停 → `paused_seconds_total = 300` 分钟，但真实等待
只有 30 分钟。`--max-runtime 360` 在经历一次 rate-limit 后实际容忍到
660+ 分钟，设计意图（"排除等待时间"）与实现直接偏差。

**证据**
- `automation/persona_extraction/rate_limit.py:375`
- `automation/persona_extraction/orchestrator.py:299-318`
- `automation/persona_extraction/orchestrator.py:1449-1464`（证明
  `wait_if_paused` 会被并发 worker 调用）

**修复方向**
累加器改为"只由记录 pause 的那一个 lane 累加"，或用进程锁保护，
或改成 `max(pause_intervals)` 合并。

---

#### H2. `ai_context/current_status.md` 与 `phase3_stages.json` 实际状态不一致

**结论**
`current_status.md:6` 与 :32 写 "Phase 3 pending — no stages committed
yet"，但 `works/<work_id>/analysis/progress/phase3_stages.json`
中 `阶段01_<location_a>初遇` state=`committed`, committed_sha=`dc1d058`；
阶段 02 已是 ERROR。git log 对应 `dc1d058 阶段01_<location_a>初遇: 分层提取完成`。

**为何是问题**
`current_status.md` 是新 session 入场文档。"no stages committed yet"
会误导后续 AI 认为 Phase 3 完全没开跑，做出错误的续跑 / 覆盖决策。

**证据**
- `ai_context/current_status.md:5-7` 和 `:31-33`
- `works/<work_id>/analysis/progress/phase3_stages.json`（前
  30 行含 2 个有状态条目）
- `git log --oneline` 中的 `dc1d058`

**修复方向**
改成 "Phase 3 in progress; 1/10 stages committed, 1 ERROR, 8 pending"。

---

#### H3. weekly 硬停 `sys.exit(2)` 从 worker 线程发出 → 主进程不直接退

**结论**
`rate_limit.py:369` 在 weekly 路径直接 `sys.exit(WEEKLY_EXIT_CODE)`。
若这是从 ThreadPoolExecutor 里 `run_with_retry` 的 worker 发出，
`SystemExit` 只在该 worker 线程抛，被 executor 吞入 future，**主进程
继续**。

**为何是问题（已降权）**
`orchestrator.py:1447` 的 pre-launch gate 在主线程。下一个批次进入前
会再次触发 gate，那次 `sys.exit` 才会真正退主进程。因此**最终仍会退**，
但："当前批次剩余 worker 继续跑 → 每个 worker 也会撞 weekly → 每个
worker 都触发一次 sys.exit（仅杀自己） → 重复日志 / 延迟退出"。
不是致命，但违反"干净退出"契约。

**证据**
- `automation/persona_extraction/rate_limit.py:358-369`
- `automation/persona_extraction/orchestrator.py:1447`
- `automation/persona_extraction/scene_archive.py:840-862`

**修复方向**
worker 抛自定义异常（非 `SystemExit`）或设 `threading.Event`；由主线程
（gate / 主循环 / `as_completed`）统一 bubble 成 `sys.exit(2)`。

---

### MEDIUM（真实风险、非灾难）

#### M1. probe-fallback 无硬上限，Anthropic 长宕机会无限等

**结论**
`wait_if_paused` 在 `reason="unknown"` + `strategy="probe"` 时循环：
sleep `parse_fallback_sleep_s`（默认 1800s）→ probe → 若仍限则
`new_resume = now + 1800s` 继续。每轮 `wait_s` 只 30min，永远不会达到
weekly hard-stop 的 `weekly_max_wait_h*3600 = 43200s` 阈值；
`--max-runtime` 又把 pause 扣掉了，**probe 循环没有退出条件**。

**为何是问题**
cron / background 长跑下，若 Anthropic 真的长时不可用（或 stderr 永远
无法解析为已知格式），进程可能挂数天静默。

**证据**：`automation/persona_extraction/rate_limit.py:348-418`

**修复方向**
- 给 probe 加 `merged_count` 硬上限（≥ `weekly_max_wait_h * 2` 即退）；或
- 累计 `slept` 超某阈值时升级成 weekly exit

---

#### M2. 时区缩写固定偏移 → DST 切换日可能偏 1 小时

**结论**
`rate_limit.py:84-90` 把 "PT" 硬编到 `-7*60`（即 PDT），"ET" 到 `-4*60`
（EDT）。`resume_buffer_s=60` 注释宣称吸收 DST 不明——但这是 60 秒，
不是 60 分钟。若 Anthropic 在冬季返回 "Resets at 08:00 PT" 而本地真实
是 PST（-8），代码算成 PDT（-7），会**早 1 小时**解除暂停，直接撞回限额。

**证据**：`automation/persona_extraction/rate_limit.py:80-90`

**修复方向**
- 模糊缩写（PT/MT/CT/ET）查 DST 窗口决定偏移；或
- 无法消解时直接回落 probe

---

#### M3. `works/README.md` 未记录三个新产物

**结论**
`works/README.md:59-66` 列 progress/ 下期望文件，但缺：
- `rate_limit_pause.json`（T-TOKEN-WATCH 暂停契约文件）
- `rate_limit_exit.log`（周限额退出日志）
- `failed_lanes/{stage_id}__{lane_type}_{lane_id}__{pid}.log`（T-LOG 已
  落地的 lane 级诊断目录）

**为何是问题**
新维护者看到 progress/ 里的陌生文件不知作用、可能误清理——尤其
`failed_lanes/` 是 `[logging].failed_lanes_retention_days` 控制的诊断
文件，被误删会销毁失败现场。

**证据**：`works/README.md:55-68`

---

#### M4. config 加载声称支持 env 覆盖，代码未实现

**结论**
`automation/config.toml:8` 注释与 `automation/README.md` 的配置段
声称优先级 "CLI > 环境变量 > 本文件 > 代码默认"。但
`automation/persona_extraction/config.py:192-227` 只合并 TOML +
config.local.toml。整个 `persona_extraction/` 包里 env 相关 grep 仅命中
`llm_backend.py:44` 的 `CLAUDE_PATH`，与 config 无关。

**为何是问题**
典型"文档说 A，代码做 B"：承诺存在但未兑现。部署若依赖
`PERSONA_CONCURRENCY=5` 之类 env 会静默失效。

**证据**
- `automation/config.toml:7-12`
- `automation/persona_extraction/config.py:192-227`
- `automation/README.md` 配置段

**修复方向**：要么实现 env 覆盖（简短），要么从文档删掉该层声明。

---

#### M5. `ai_context/next_steps.md` 可能未反映 TODO 最新状态（推断）

**结论**
`docs/todo_list.md` 的"立即执行"已清空、T-SCENE-CAP 在"下一步"等提升；
但 `ai_context/next_steps.md` 的 Highest Priority 叙事可能仍指向
Phase 0/1 推进。新 session 入场若先读 next_steps 会误判重点。

**证据**：规范线 agent 报告 `ai_context/next_steps.md:5-9`，**推断，
未现场逐字核验**。

---

### LOW

- **L1. `get_config()` 单例无锁**（`config.py:237-242`）：理论可双加载；
  CPython GIL + 纯文件读取幂等，实际风险极低。
- **L2. TOML 非 table 节静默 warning**（`config.py:220-224`）：人为 TOML
  写错会降级到默认值仅打 warning，不 raise；可能隐藏配置错误。
- **L3. `ai_context/requirements.md` 未同步 §11.13**：handoff 已建议读
  `docs/requirements.md`，问题不大；可选补压缩摘要。
- **L4. `_LockHandle.__exit__` 关 fd 无 try/except**
  （`rate_limit.py:503-509`）：上下文管理器通常只调一次，实际风险低。

---

## False Positives（agent 报了但不成立）

这些在 audit 中被标为问题，但经现场核验不成立，记录在此避免下次再误报：

- **"scene_fulltext_window 未在 automation/config.toml 中定义"**：
  该参数是 simulation 层运行时参数，`automation/config.toml` 只管提取
  流水线。simulation 尚未实现（`current_status.md:135`），参数缺失是
  by design。
- **"own_controller 让 Phase 4 standalone 与 orchestrator 的 controller
  数据分散"**：代码逻辑是 `if get_active_rl() is None: ... own_controller
  =True`（`scene_archive.py:663-666`），两条路径互斥，不会并存。
  finally 里正确 None-out。
- **"rate_limit_pause.json 缺 schemas/ 下的 .schema.json"**：其它
  progress 文件（`pipeline.json` / `phase3_stages.json` / `phase4_scenes
  .json`）也都没有 JSON Schema——仓库一贯把 progress 文件交给代码
  dataclass 管理，不入 `schemas/`。单独要求它加 schema 与既有实践不一致。
- **"pause 文件跨 flock/fsync 的 race"**：`_atomic_write_json` 在 flock
  持有中执行 `os.replace`，不存在"flock 释放后还在 rename"的窗口。

---

## Open Questions（需产品/架构决策）

1. **paused_seconds_total 语义**：设计意图是"一次 pause 扣一次挂钟
   时长"还是"每个 lane 各自的等待时长之和"？两种都符合字面的"排除
   等待时间"，结果相差一个数量级。
2. **probe 无限循环可接受性**：是否一定要超时退出，还是可接受 Anthropic
   整段不可用时无限挂起由用户 Ctrl-C？默认 cron/background 场景建议
   加硬上限。
3. **env var 覆盖层是否真要做**：若不做，删文档；若做，影响面小。

---

## Alignment Summary

| 层 | 对齐度 | 主要缺口 |
|---|---|---|
| `ai_context/` ↔ `docs/` | ~95% | Phase 3 进度描述滞后（H2）、next_steps 可能未同步（M5） |
| `docs/requirements.md` ↔ `automation/config.toml` | ~98% | 对齐良好；env 层是空承诺（M4） |
| `automation/config.toml` ↔ 代码 | ~98% | 单源配置整洁落地；get_config 单例微瑕（L1） |
| `rate_limit.py` ↔ 设计契约 §11.13 | ~85% | **并发累加 bug（H1）**、weekly sys.exit 线程问题（H3）、probe 无上限（M1）、DST（M2） |
| `works/README.md` ↔ 实际产物 | ~80% | 三个新目录/文件未写进 README（M3） |
| `schemas/` ↔ 代码产物 | 与既有惯例一致 | — |
| `prompts/` ↔ decisions §44 | 对齐 | — |

**最不对齐**：`rate_limit.py` 的并发正确性（H1 是最值得处理的问题，
语义偏差大、每次触发即失效）、`works/README.md` 的产物列表、
`ai_context/current_status.md` 的 Phase 3 进度。

---

## Residual Risks

1. **rate-limit 压力测试缺失**：5 个 smoke test 都是 mock 时钟的单线程
   串行场景；真实 10-lane 并发撞限、worker 内 weekly exit、probe 循环
   这些路径都没被真机验证。H1/H3/M1 在真实运行触发前可能都还没暴露。
2. **cron/background 长跑没有看门狗**：若 probe 无限 + `--max-runtime`
   被扣减无效，进程可能挂几天不退。建议上层 systemd/cron 加 hard-kill。
3. **`config.local.toml` 误提交风险**：`.gitignore:53` 已覆盖，但无 CI
   兜底；未来 force-add 仍会漏。
4. **`failed_lanes/` 清理未接入**：`[logging].failed_lanes_retention_days
   =30` 已定义，但 startup hook 没实现，日志会无限增长。

---

## 建议落地顺序

| 序 | 项 | 优先度 | 工作量 |
|---|---|---|---|
| 1 | H1: paused_seconds_total 并发累加 | 最高（语义直接错） | 小（加锁） |
| 2 | H2: current_status.md Phase 3 描述 | 高（误导后续 AI） | 1 行 |
| 3 | H3 + M1: weekly sys.exit 从 worker + probe 无上限 | 中高（同一块代码，一起改） | 中 |
| 4 | M3: works/README.md 补 3 条产物 | 中 | 纯文档 |
| 5 | M4: env 覆盖，做 or 删注释 | 中（等产品决策） | 小 |
| 6 | M2: DST | 低（仅切换日触发） | 小 |
| 7 | M5 / L1 / L2 / L3 / L4 | 低 | 视情况 |
