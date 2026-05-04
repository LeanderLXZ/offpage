# phase0_summarize_timeout_bump

- **Started**: 2026-05-04 15:46:22 EDT
- **Branch**: main (worktree at ../offpage-main，源会话所在分支
  `extraction/<work_id>`)
- **Status**: PRE

## 背景 / 触发

跑 `<work_id>` Phase 0 summarization runtime 验证（537 章 → 22 chunks，
并发 10）时，wave 1 全部 10 个 chunk 在 ~10 min 处被
`subprocess.TimeoutExpired` 杀掉（日志 `[FAIL] chunk_NNN: claude -p
timed out`）。监控期内只观测到 1 个 chunk 实际写盘成功（看到落盘
`chunk_003.json`，但被本次回滚清掉）；其余 21 个走完 timeout 后
orchestrator 起 wave 2 同配置重试，必然再次 timeout，只能整批 kill 回滚。

诊断锁定到 `automation/persona_extraction/orchestrator.py:502`
phase 0 summarization 调 `run_with_retry(..., timeout_seconds=
get_config().phase3.review_timeout_s, ...)`：

1. 数值上 `phase3.review_timeout_s = 600s`，对 phase 0 的工作量来说
   太紧——每 chunk 25 章 + per-summary 100–150 字 ×25 + 5 个
   chunk-level 二级聚合字段（`T-PHASE0-CHUNK-SCHEMA-EXPAND` 刚扩）
   + opus-4-7 effort=max + max-turns=50，wave 1 10/10 撞 600s 上限说明
   600s 不是边缘 case。
2. 语义上把 phase 0 的 summarization 超时挂在 `phase3.review_timeout_s`
   上是历史遗留耦合：`review_timeout_s` 名义上服务 phase 3 reviewer
   的短链 LLM 校审（默认 600s 合适），phase 0 summarize 借用这个键
   仅因数值历史偶合 600s。

## 结论与决策

**仅做最小 timeout 提升**，不做 effort/max-turns 调整、不做并发调整：

- `automation/persona_extraction/config.py` `Phase0Config` 加新字段
  `summarize_timeout_s: int = 1800`（独立于 `json_repair_l2_timeout_s`，
  后者是 L2 修复短链，保持 600s 不动）
- `automation/config.toml` `[phase0]` 段加 `summarize_timeout_s = 1800`
  + 中文注释（说明 chunk 25 章 + chunk-level 5 个二级字段写盘 + opus
  effort=max 单 chunk wall 经验值）
- `automation/persona_extraction/orchestrator.py:502`
  `timeout_seconds=get_config().phase3.review_timeout_s` →
  `timeout_seconds=get_config().phase0.summarize_timeout_s`
- `phase3.review_timeout_s` 保持 600s 不动（phase 3 reviewer 短链
  没有这次的 timeout 问题，不动它）

显式不做的事：

- 不动 `phase3.extraction_timeout_s`（已经 3600s）
- 不动 effort=max / max-turns=50（这次诊断结论是 timeout 太紧，
  不是模型/turn 预算问题）
- 不动 phase 0 并发（10 已合理，并发越高越容易撞 5h 限额，且 timeout
  是 per-chunk 不是 wall 级，并发不解决问题）

## 计划动作清单

- file: `automation/persona_extraction/config.py` →
  `Phase0Config` 加 `summarize_timeout_s: int = 1800`
- file: `automation/config.toml` → `[phase0]` 段加
  `summarize_timeout_s = 1800` + 中文注释
- file: `automation/persona_extraction/orchestrator.py` → line 502
  `timeout_seconds` 来源 `phase3.review_timeout_s` →
  `phase0.summarize_timeout_s`
- file: `automation/README.md` → 「子进程超时」段把 phase 0 summarize
  超时数值与口径说明同步（如果该段提到具体数字 600s）
- file: `ai_context/architecture.md` → Phase 0 段如显式提到 summarize
  超时数值则同步；只提"子进程超时"无数字则不动
- file: `ai_context/decisions.md` → 加一条 durable 决策：
  phase 0 summarize 超时独立于 phase3.review_timeout_s + 1800s 的来由
- file: `docs/extraction_workflow.md` / `docs/requirements.md` /
  `docs/schema_reference.md` → grep 是否有"600s" / "10 分钟" /
  "phase3.review_timeout_s" 描述涉及 phase 0；有则同步
- file: `docs/todo_list.md` → 新增「next」段或「完成」段记录这次
  hot-fix（小尾巴小到不必登 in-progress）

## 验证标准

- [ ] `python -c "from automation.persona_extraction.config import
      load_config; c = load_config('/home/leander/Leander/offpage-main');
      assert c.phase0.summarize_timeout_s == 1800; print('OK', c.phase0)"`
      返回 OK
- [ ] `python -c "from automation.persona_extraction import
      orchestrator"` import 不抛
- [ ] `grep -n "phase3.review_timeout_s" automation/persona_extraction/
      orchestrator.py` 不再出现在 phase 0 summarize 调用点
      （line 502 附近），可保留在其它合法用点（line 1069 等）
- [ ] `grep -RnE "600s.*phase 0|phase 0.*600s|review_timeout.*phase\s*0"
      docs/ ai_context/ automation/README.md` 不再有过期描述
- [ ] config.toml 静态可解析（`python -c "import tomllib; tomllib.load(
      open('automation/config.toml','rb'))"` 不抛）

## 执行偏差

无（实际改动与计划一一对应；docs/todo_list.md 改动方向调整为
"加入 todo_list_archived.md `## Completed` 段"——本任务从未上 todo
队列，没有 in-progress 条目可移段，所以直接归档而非走"In Progress
→ Completed"流程，与 PRE log "新增「next」段或「完成」段记录" 等价
不算偏差）

<!-- POST 阶段填写 -->

## 已落地变更

- `automation/persona_extraction/config.py:42` — `Phase0Config` 加
  `summarize_timeout_s: int = 1800`（与 `concurrency` / `json_repair_l2_timeout_s`
  并列）
- `automation/config.toml:36-41` — `[phase0]` 段加 `summarize_timeout_s = 1800`
  + 5 行中文注释（25 章 + 5 个 chunk-level 字段 + opus-4-7 effort=max
  单 chunk wall ≥600s 的经验值，1800s 留 3× 余量）
- `automation/persona_extraction/orchestrator.py:502` —
  `_summarize_chunk` 的 `timeout_seconds` 由
  `get_config().phase3.review_timeout_s` 改为
  `get_config().phase0.summarize_timeout_s`
- `automation/README.md:62` — 配置分段表 `[phase0]` 行加 "summarize
  子进程超时"
- `docs/architecture/extraction_workflow.md:608-609` — 子进程硬超时
  描述加 "Phase 0 summarize 1800s"，阈值控制段补 `[phase0]`
- `docs/requirements.md:2214` — 同上硬超时描述同步
- `docs/requirements.md:2500` — 配置分节表 `[phase0]` 行加 "summarize
  子进程超时"
- `ai_context/decisions.md:338` — `## Configuration & Runtime
  Resilience` 段加 #47 durable 决策
- `docs/todo_list_archived.md:76-79` — `## Completed` 段顶部插入
  `T-PHASE0-SUMMARIZE-TIMEOUT-BUMP` 条目（标题 + 1 行摘要 + log 链接）

## 与计划的差异

无新增 / 删除（PRE 计划动作 9 项与已落地一一对应）；docs/todo_list.md
未改动（hot-fix 从未上正向队列，直接落 archived；详见上方"执行偏差"段）。

## 验证结果

- [x] `python -c "from automation.persona_extraction.config import
      load_config; c = load_config(); ..."` 返回 `phase0:
      Phase0Config(concurrency=10, summarize_timeout_s=1800,
      json_repair_l2_timeout_s=600)`
- [x] `python -c "from automation.persona_extraction import
      orchestrator"` import 通过
- [x] `grep -n "phase3.review_timeout_s" automation/persona_extraction/
      orchestrator.py` 命中 1 处（line 1994，Phase 3 repair_agent，
      合法保留），phase 0 summarize 调用点（line 502）已切走
- [x] `grep -RnE "600s.*phase ?0|phase ?0.*600s|review_timeout.*phase\s*0"
      docs/ ai_context/ automation/README.md` 仅命中 ai_context/
      decisions.md:338 即新增 #47 自身（描述当前设计含历史借用对照
      所必须），无其它过期描述
- [x] config.toml 静态可解析（`tomllib.load` 通过），phase0 块为
      `{'concurrency': 10, 'summarize_timeout_s': 1800,
      'json_repair_l2_timeout_s': 600}`

## Completed

- **Status**: DONE
- **Finished**: 2026-05-04 15:52:44 EDT
