# phase0_recovery_sweep

- **Started**: 2026-05-06 16:31:55 EDT
- **Branch**: main (worktree at ../offpage-main，源会话所在分支
  `extraction/<work_id>`)
- **Status**: PRE

## 背景 / 触发

`<work_id>` phase 0 v2 + v3 两次跑 chunk_008 都撞 1800s wall-clock
timeout（v2 = C0176-C0200，v3 = C0141-C0160，章节范围不重叠但同样
失败）。诊断（前台 stream-json + verbose 跑 chunk_008 单独）锁定
根因：opus-4-7 effort=max 在"读 20 章 + 5 个 chunk-level 二级聚合
字段"这种多字段输出任务上触发**非确定性服务器端长思考**——claude
读完所有章节后产出一句 "I'll write the chunk..." 文本，然后进入
加密 thinking 模式 10+ min 不发任何 tool call，直至撞 1800s subprocess
timeout 被 kill。

ground truth 已验证：

- effort=max 实际**最终能完工**（前台跑 ~28 min wall 写出 schema valid
  chunk_008.json，但超过 orchestrator 1800s 上限）
- effort=high 同 chunk **~14 min 完工**（缩半），schema 同样 valid，
  summary 长度分布 101-114 + chunk-level 5 字段全合规
- 两版产出质量看不出差异

todo 条目 `T-PHASE0-RECOVERY-SWEEP` 已落 `docs/todo_list.md ## Next`
段（commit pending = 本次 /go 一并落盘）。`<work_id>` 的 chunk_008
当下已通过手工 hot-fix 把 phase0_summaries.json state failed→done
（effort=high 前台 diag 产出已 valid 文件在盘），让<character>立刻能进
phase 1；本次 /go 是为**未来作品**给 orchestrator 加自动救火出口，
不再依赖手工 hot-fix。

## 结论与决策

**精准兜底而非全局降级**：保留默认 effort=max 给绝大多数 chunk（多数
chunk 不触发长思考死锁，质量层面 max 略好），仅对 timeout/max_turns
失败 chunk 用 effort=high 单次 sweep 救火。

5 个设计点（与 user 讨论后拍板）：

1. **timeout 范围** D2：`error_message` 含 `'timed out'` OR `'error_max_turns'`
   都进 sweep（二者都是 agent 没在预算内收敛，effort=high 都可能救）
2. **实现位置** B：独立方法 `_run_recovery_sweep`（不是 inline 嵌入
   `run_summarization`），可独立 unit test
3. **backend effort 切法** B2：`LLMBackend.run` 加 `effort: str | None = None`
   per-call kwarg；sweep 时透传 `effort='high'`，不切换 backend 实例
4. **recovery 内并发** C2：复用 `phase0.concurrency=10`，
   `ThreadPoolExecutor(max_workers=concurrency)` 跑 sweep
5. **resume 行为** D1：加 `recovery_attempted: bool = False` 字段；
   sweep 只挑 `recovery_attempted=False` 的 chunk；resume 时
   `recovery_attempted=True` 的 chunk 跳过（不再二次救火）

显式不做的事：

- 不动 phase 3+ effort 默认值（保持 max；recovery 仅对 phase 0）
- 不引入 "recovery 失败再 sweep" 循环（user spec：只走一次流程）
- 不改 1800s timeout（effort=high 实测 14 min 远低于上限；不需要再调）
- 不动当下 chunk_008 hot-fix（已手工 done）

## 计划动作清单

- file: `automation/persona_extraction/llm_backend.py` →
  `LLMBackend.run` 加 `effort: str | None = None` kwarg；ClaudeBackend
  在 build CLI argv 时若 `effort` 非 None 则覆盖 `--effort <effort>`；
  CodexBackend 同步加 kwarg 哪怕暂不实现 effort（保持接口一致）
- file: `automation/persona_extraction/llm_backend.py` →
  `run_with_retry()` helper 加 `effort: str | None = None` kwarg 透传
  给 backend.run
- file: `automation/persona_extraction/orchestrator.py` →
  - `_summarize_chunk` 加 `_recovery_effort: str | None = None` 内部
    kwarg，在 `run_with_retry(...)` 调用处透传
  - 新增 `_run_recovery_sweep(self, phase0, summaries_dir, total_chunks)`
    方法：
    - 扫 `phase0.chunks` 找 `state == 'failed'` AND
      (error_message 含 `'timed out'` OR `'error_max_turns'`) AND
      `recovery_attempted == False`
    - `ThreadPoolExecutor(max_workers=phase0.concurrency)` 并发跑
      每个候选 chunk
    - 每个 chunk 调 `self._summarize_chunk(idx, total_chunks, start,
      end, summaries_dir, _recovery_effort='high')`
    - 成功：`state='done', error_message='', recovery_attempted=True,
      retry_count+=1, last_updated=now`
    - 失败：`state='failed', error_message='recovery (effort=high)
      failed: {msg}', recovery_attempted=True, retry_count+=1,
      last_updated=now`
    - 写盘 `phase0.save(self.project_root)`
  - `run_summarization` 在 main ThreadPoolExecutor 处理完所有 chunks
    之后（mark_done 之前）调 `_run_recovery_sweep`；mark_done 仍按
    "全部 done 才 mark" 的现有逻辑判断（recovery 后状态仍可能含
    failed，那种情况 mark_done 不会被触发）
- file: `automation/persona_extraction/progress.py` →
  `ChunkEntry` dataclass 加 `recovery_attempted: bool = False`；
  `to_dict` / `from_dict` 同步（`from_dict` 用 `.get('recovery_attempted',
  False)` 向后兼容旧 progress）
- file: `automation/persona_extraction/config.py` →
  `Phase0Config` 加 `recovery_effort: str = 'high'`（dataclass 新字段，
  仅在 sweep 触发时使用）
- file: `automation/config.toml` `[phase0]` 段 →
  加 `recovery_effort = "high"` + 中文注释（说明 timeout/max_turns
  sweep 用降级 effort 救火）
- file: `ai_context/decisions.md` →
  加 #49 durable 决策（phase 0 recovery sweep with downgraded effort）
  + 引用本 log
- file: `docs/architecture/extraction_workflow.md` →
  Phase 0 段加 recovery sweep 段落
- file: `docs/requirements.md` →
  Phase 0 描述同步 recovery sweep（取决于现有内容是否已涉及 phase 0
  失败处理；若是则补，否则不动）
- file: `docs/todo_list.md` →
  T-PHASE0-RECOVERY-SWEEP 移到 archived `## Completed`，Index Next
  3→2 / 汇总 15→14（在 commit 内一并完成）
- file: `docs/todo_list_archived.md` →
  `## Completed` 顶部插入 T-PHASE0-RECOVERY-SWEEP 瘦身条目

## 验证标准

- [ ] `python -c "from automation.persona_extraction.config import
      load_config; c=load_config(); assert c.phase0.recovery_effort=='high'"`
      不抛
- [ ] `python -c "from automation.persona_extraction.progress import
      ChunkEntry; e=ChunkEntry(chapters='C0001-C0020'); assert
      e.recovery_attempted == False"` 不抛
- [ ] `python -c "from automation.persona_extraction.progress import
      ChunkEntry; e=ChunkEntry.from_dict({'chapters':'C0001-C0020',
      'state':'pending','retry_count':0,'error_message':'',
      'last_updated':''}); assert e.recovery_attempted == False"`
      不抛（向后兼容：旧 dict 缺 recovery_attempted 字段时 default False）
- [ ] `python -c "from automation.persona_extraction.llm_backend
      import LLMBackend; import inspect; assert 'effort' in
      inspect.signature(LLMBackend.run).parameters"` 不抛
- [ ] `python -c "from automation.persona_extraction import
      orchestrator; assert hasattr(orchestrator.ExtractionOrchestrator,
      '_run_recovery_sweep')"` 不抛
- [ ] orchestrator + scene_archive + post_processing +
      repair_agent.coordinator 全部 import 通过
- [ ] config.toml 静态可解析，phase0 块含 `recovery_effort: 'high'`
- [ ] `_smoke_l3_gate` 4 场景仍全过（确认 length-tolerance 改动
      未被本次破坏）
- [ ] 写一个 `_smoke_recovery_sweep.py` 类似 _smoke_l3_gate 的 stub
      场景测试：构造一个 phase0_summaries.json 含 1 个 timeout failed
      chunk + 1 个 max_turns failed chunk + 1 个其它 failure（不该
      被 sweep）+ 1 个 already-recovery_attempted chunk（应跳过），
      mock backend.run 返回成功，验证 sweep 后只动该动的 2 个，且
      recovery_attempted 都置 True

runtime 验证（在真实作品上 sweep 实际触发 + 完工）由后续会话/loop
处理，不在本 commit 范围内。

## 执行偏差

无（落地 1:1 对应 PRE 计划清单；smoke test 比 PRE 列的 4 case 还多一个
"_recovery_effort 透传到 _summarize_chunk kwargs 验证" 在 mock 内 inline
assert，不算偏离）

<!-- POST 阶段填写 -->

## 已落地变更

- `automation/persona_extraction/progress.py:208-243` — `ChunkEntry`
  加 `recovery_attempted: bool = False`；`to_dict` / `from_dict`
  双向同步（`from_dict.get('recovery_attempted', False)` 向后兼容
  旧 progress 文件）
- `automation/persona_extraction/config.py:44` — `Phase0Config` 加
  `recovery_effort: str = "high"`
- `automation/config.toml:46-54` — `[phase0]` 段加 `recovery_effort
  = "high"` + 7 行中文注释（说明 sweep 触发条件 + 与 effort=max 主流程
  的关系 + ground truth 14 min vs 28 min）
- `automation/persona_extraction/llm_backend.py:222-231` —
  `LLMBackend.run` 抽象签名加 `effort: str | None = None` kwarg + 详细
  docstring 引用 #49
- `automation/persona_extraction/llm_backend.py:255-281` —
  `ClaudeBackend.run` 加同名 kwarg + 局部变量 `active_effort = effort
  if effort is not None else self.effort` 用于构造 `--effort` argv
- `automation/persona_extraction/llm_backend.py:437-446` —
  `CodexBackend.run` 加同名 kwarg（接口对齐；codex CLI 暂无 effort
  flag → 注释说明并静默忽略）
- `automation/persona_extraction/llm_backend.py:603-634` —
  `run_with_retry` 加 `effort: str | None = None` kwarg + docstring
  注 + `backend.run(... effort=effort)` 透传
- `automation/persona_extraction/orchestrator.py:477-510` —
  `_summarize_chunk` 加 `_recovery_effort: str | None = None` 内部
  kwarg + docstring 说明用途；`run_with_retry(... effort=_recovery_effort)`
  透传
- `automation/persona_extraction/orchestrator.py:534, 561, 600` — 3 处
  L3 retry 递归调用 `self._summarize_chunk(... _recovery_effort=
  _recovery_effort)` 透传（JSON fail / schema fail / partial-count
  fail 三条 retry 路径）
- `automation/persona_extraction/orchestrator.py:477-573` 之前
  插入新方法 `_run_recovery_sweep(self, phase0, summaries_dir,
  total_chunks, chunks)` ~75 行：filter `state=='failed'` AND error
  含 `'timed out'` / `'error_max_turns'` AND `recovery_attempted==False`
  → ThreadPoolExecutor max_workers=self.concurrency 并发 → 调
  `_summarize_chunk(_recovery_effort=recovery_effort)` → 不论成败置
  `recovery_attempted=True, retry_count+=1`，成功 state→done /
  error_message='', 失败 state→failed / error_message='recovery
  (effort=high) failed: ...'
- `automation/persona_extraction/orchestrator.py:962-969` — 在
  `run_summarization` 主循环 ThreadPool 之后 + gate 检查之前调
  `self._run_recovery_sweep(phase0, summaries_dir, total_chunks,
  chunks)`；gate 仍按 `_chunk_passes_full_check` 重新扫盘判失败（
  recovery 后状态自然 reflected）
- `automation/persona_extraction/_smoke_recovery_sweep.py` 新建文件
  ~150 行，4 场景 stub 测试（A 候选过滤 / B 成功 / C 失败 / D
  no-candidate no-op）；mock `_summarize_chunk` 验证 `_recovery_effort`
  透传 + state 转换 + recovery_attempted 永远置 True
- `ai_context/decisions.md:340` — 加 #49 durable 决策（recovery sweep
  with downgraded effort，附 v2/v3 chunk_008 实测数据 + plumbing 锚点）
- `ai_context/architecture.md:171` — Key Design 段加 "Phase 0 recovery
  sweep" bullet
- `docs/architecture/extraction_workflow.md:60-67` — Phase 0 段加
  recovery sweep 段落
- `docs/requirements.md:2454-2459` — `phase0_summaries.json` 描述加
  `recovery_attempted` 字段语义说明
- `docs/todo_list.md` — 删除 Next 段 T-PHASE0-RECOVERY-SWEEP block；
  Index Next 子表 3→2；汇总 15→14
- `docs/todo_list_archived.md:76-79` — `## Completed` 顶部插入
  T-PHASE0-RECOVERY-SWEEP 瘦身条目（标题 + 1 行摘要 + log 链接）

## 与计划的差异

无新增 / 删除；3 处 L3 retry 递归调用透传 `_recovery_effort` 是 PRE
"`_run_recovery_sweep` 调 `_summarize_chunk(... _recovery_effort='high')`"
的隐含细节（PRE 计划已经写出 _summarize_chunk 加 kwarg 但未明确列
3 处 L3 retry 递归同步），落地时为完整正确传递把所有 3 处都补了。

## 验证结果

- [x] `python -c "from automation.persona_extraction.config import
      load_config; c=load_config(); assert c.phase0.recovery_effort
      == 'high'"` 不抛 — OK 输出 `'high'`
- [x] `python -c "from automation.persona_extraction.progress import
      ChunkEntry; e=ChunkEntry(...); assert e.recovery_attempted
      == False"` 不抛 — OK
- [x] backward-compat：旧 progress dict 缺 `recovery_attempted` 字段
      `from_dict` default False — OK
- [x] `to_dict` round-trip 保留 `recovery_attempted` — OK
- [x] `LLMBackend.run` / `ClaudeBackend.run` / `CodexBackend.run`
      / `run_with_retry` 全部 `effort` kwarg in signature — OK
- [x] `ExtractionOrchestrator._run_recovery_sweep` 方法存在 — OK
- [x] `_smoke_recovery_sweep` 4 场景全过 (A/B/C/D)
- [x] `_smoke_l3_gate` 4 场景全过（无回归 length-tolerance）
- [x] orchestrator + scene_archive + post_processing +
      repair_agent.coordinator import 全过

runtime 验证（在真实作品上 sweep 实际触发 + 完工）由后续会话/loop
处理；本 commit 不依赖 runtime gate。

## Completed

- **Status**: DONE
- **Finished**: 2026-05-06 16:45:21 EDT
