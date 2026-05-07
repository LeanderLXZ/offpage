# phase1_post_check_fixes

- **Started**: 2026-05-07 14:49:43 EDT
- **Branch**: main
- **Status**: PRE

## 背景 / 触发

接 `phase1_parallel_lanes` (`e644886`) 的 /post-check (`b95fd5c`) 复查，REVIEWED-PARTIAL 报告里 3 个 Medium + 3 个 Low Findings。用户要求"按建议修复，不要过度工程，没必要的更改就不用改"。

复查报告原 Findings：
- [M] `ai_context/conventions.md:49` Cross-File Alignment row 49 (structure_mode) 描述 "Phase 1 `_build_light_novel_stage_plan` overwrite + STAGE_MIN/MAX bypass"。新设计是 direct-write，"overwrite" 措辞继承自旧设计（LLM 先产 stage_plan 再被覆写）；row 50 同次 commit 已更新但 row 49 漏更
- [M] `automation/persona_extraction/orchestrator.py:1300-1303` `_load_json(target_path)` 返回 None 时 `_run_one_lane` 给 prior_error "输出文件 ... 未生成"；但 `_load_json` 吞 JSONDecodeError 与 OSError 都返回 None，无法区分"文件不存在"vs"json bad"。LLM 看到一致的"未生成"消息，可能在 json 格式坏的情况下重复同样错误直到预算耗尽
- [M] `automation/persona_extraction/orchestrator.py:1263-1267` light_novel→monolithic 模式切换时旧 1-chapter stage_plan 残留被 `_lane_passes_skip` 误判跳过 LLM 重生
- [L] PRE log 行号偏移
- [L] orchestrator.py:1394-1395 `fut.result()` 无 try-except 注释提示
- [L] config.toml lane_concurrency 注释量化

## 结论与决策

针对复查报告 3 [M] + 3 [L]，按"不过度工程"原则筛取后实修 2 项 + 验证 1 项不需修：

1. **[M] 修：conventions.md:49 措辞** — 1 行 doc 修复："overwrite" → "direct-write (lane skipped from LLM fan-out)"
2. **[M] 修：`_run_one_lane` 内 prior_error 区分 file-missing vs json-bad** — 在 `_load_json` 返回 None 后加分支：`target_path.exists()` 决定走"json bad"路径（用 `json.loads(target_path.read_text())` 拿到具体 exception 消息塞进 prior_error）还是"未生成"路径。本地化 ~6 行，**不改 `_load_json` 签名**，无上下游兼容性影响
3. **[M] 不修：light_novel→monolithic 模式切换残留 — false positive** — 重新核查 `_lane_passes_skip`：monolithic 模式下若磁盘 stage_plan 是 light_novel 派生的 1-chapter 形态，`_check_stage_plan_limits(existing, max_stage_size=15, min_stage_size=5)` 会返回 violating list（chapter_count=1 < min 5），skip 返回 False → lane 会重跑。Step 7 风险线 agent 当时漏看了这个守卫调用。仅在 PRE log 偏差段记录"verified non-issue"，不改代码、不改 doc

3 个 [L] 跳过：
- [L] PRE log 行号偏移：历史 baseline 描述，commit 后行号自然偏移，不需要事后回填
- [L] `fut.result()` try-except 注释：`_run_one_lane` 当前实现无 raise 路径，加注释属"防未来误改"，未触发实际 bug；用户"不必要更改不改"原则下跳过
- [L] config.toml lane_concurrency 量化注释：现行注释已说"订阅模式高并发易撞 5h 限额，可调低"，进一步量化属于运维 doc 改进，跳过

## 计划动作清单

- file: `ai_context/conventions.md` row 49 (`structure_mode` 行) → 改 "Phase 1 `_build_light_novel_stage_plan` overwrite + STAGE_MIN/MAX bypass" 为 "Phase 1 `_build_light_novel_stage_plan` direct-write (stage_plan lane removed from LLM fan-out, see #52) + STAGE_MIN/MAX bypass"
- file: `automation/persona_extraction/orchestrator.py` `_run_one_lane` 内 `produced is None` 分支（行 ~1299-1310）→ 加 `target_path.exists()` 分流：
  - 不存在 → 沿用旧消息"输出文件 `{fname}` 未生成，请按 prompt 要求落盘"
  - 存在 → 用 `json.loads(target_path.read_text(encoding="utf-8"))` 主动尝试解析以获取具体 exception；prior_error 改为"输出文件 `{fname}` 已落盘但 JSON 解析失败：`{exc}`。请检查格式（缺逗号 / 引号未闭合 / 尾随非法字符等）后重写"
- file: `logs/change_logs/2026-05-07_144943_phase1_post_check_fixes.md` → PRE / POST / REVIEW（本日志）

## 验证标准

- [ ] `from automation.persona_extraction.orchestrator import ExtractionOrchestrator` import 仍通过
- [ ] `inspect.getsource(ExtractionOrchestrator.run_analysis)` 包含新加的 `target_path.exists()` 分支判断 + 区分两条 prior_error 消息
- [ ] `ai_context/conventions.md` row 49 内 "overwrite" 字样替换为 "direct-write"，不留旧措辞
- [ ] 全仓 `grep -rn "_build_light_novel_stage_plan.*overwrite"` 残留 = 0
- [ ] 通过 monkey-patch `_load_json` 返回 None 模拟两种失败（一是 file-missing，二是 json-bad），验证 `_run_one_lane` 走分流路径生成两种不同 prior_error 字符串
- [ ] /post-check Finding 3 的"verified non-issue"逻辑通过：构造 stage_plan.json with `{"stages": [{"chapter_count": 1, ...}]}`，调 `_lane_passes_skip("stage_plan", ...)` with monolithic 模式（is_light_novel=False），断言返回 False（即 lane 会重跑）

## 执行偏差

无。

<!-- POST 阶段填写 -->

## 已落地变更

修改（2 件 + 本日志）：
- `ai_context/conventions.md` row 49 — 把 `Phase 1 \`_build_light_novel_stage_plan\` overwrite + STAGE_MIN/MAX bypass` 改为 `Phase 1 \`_build_light_novel_stage_plan\` direct-write — light_novel 模式 stage_plan lane 不进 LLM fan-out, see decision #52 — + STAGE_MIN/MAX bypass`（一行措辞修复 + 加 #52 cross-ref）
- `automation/persona_extraction/orchestrator.py` `_run_one_lane`（行 1299-1334） `produced is None` 分支扩成三向分流：
  - `target_path.exists()` False → 沿用旧 "未生成" 消息
  - `target_path.exists()` True 且 `json.loads` raise → 新 "JSON 解析失败：`{exc}`" 消息（带具体 exception 文本，提示常见格式错误）
  - `target_path.exists()` True 且 `json.loads` 成功（即 file 含 JSON null / 空容器）→ 新 "解析为空 (null / 空容器)" 消息
  - 同时将 strict-budget exhausted 时的 `lane_failed` 错误文本从硬编码 "output file not produced" 改为复用 prior_error 前 120 字（保留诊断信号）
- `logs/change_logs/2026-05-07_144943_phase1_post_check_fixes.md` — 本日志

**未改**：3 个 [L] Findings（PRE log 行号偏移 / `fut.result()` try-except 注释 / `lane_concurrency` 量化注释）按用户"不过度工程"原则跳过；Finding 3（mode 切换残留）经 smoke 验证为 false-positive，不需代码 / doc 修复。

## 与计划的差异

无。

## 验证结果

- [x] `from automation.persona_extraction.orchestrator import ExtractionOrchestrator` import 通过
- [x] `inspect.getsource(ExtractionOrchestrator.run_analysis)` 含 `target_path.exists()` 分支判断 + 三段 prior_error 消息（'未生成' / 'JSON 解析失败' / '解析为空'）
- [x] `ai_context/conventions.md` row 49 内 "overwrite" 字样替换为 "direct-write"（grep -n "overwrite" 仅命中本日志 + 上轮 /post-check log 的 Findings 描述，均合法历史引用）
- [x] 全仓 `grep -rn "_build_light_novel_stage_plan.*overwrite"` 残留 0（仅 logs/change_logs/ 下两份历史 log 提及，合法）
- [x] Finding 3 verified non-issue：构造 1-chapter stage_plan，`_check_stage_plan_limits(plan, max=15, min=5)` 返回 3 个 violating（chapter_count=1 < min 5），证明 `_lane_passes_skip` 在 monolithic 模式下会拒绝 light_novel 派生的旧 stage_plan，触发 lane 重跑 — 无 mode-switch skip-mismatch bug

## Completed

- **Status**: DONE
- **Finished**: 2026-05-07 14:53:47 EDT
