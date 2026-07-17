# effort-tier-tuning

- **Started**: 2026-07-17 07:20:38 EDT
- **Branch**: main
- **Type**: GO
- **Status**: PRE

## Background / Trigger

用户指令：`T-EFFORT-TIER-TUNING /go`。任务条目见 `docs/todo_list.md`
§Next `[T-EFFORT-TIER-TUNING]`。

2026-07-16 挂机跑 phase 3（S001–S003 committed）后做的耗时归因结论：
**`effort=max` 的双峰思考是速度的头号成因，与任何代码改动无关**。

- 全 lane 生成速度恒定 44–68 tok/s（`logs/runs/*.jsonl` 的 `duration_s` ÷
  `output_tokens`）——耗时 ≈ 输出 token ÷ 56，飘的是输出量不是速度。
- 输出 ~96% 是思考不是产物（某 `char_support` lane 烧 124,159 out_tok /
  18 turns 只产出 14KB 文件；同 stage 另一角色同 lane 用 50,357 tok 产出
  更大的 20KB 文件）。
- 爆掉样本挤得异常紧：2127s / 2192s / 2115s——是**双峰**（正常 ~850–1200s
  vs 爆掉 ~2100s），不是长尾。中招的 lane 随机（S001 是 Character A 爆，
  S003 换成 Character B 爆而 A 只跑 991s；`world` lane 也出现过 1523s vs
  自身 p50 439s）。

这与**决策 #49 在 phase 0 上的诊断完全同构**（「opus-4-7 effort=max …随机
触发服务端超长 thinking」），且 #49 已实证 effort=high 下 ~14 分钟完工、
schema 合法、质量等同。

两个附带发现：

1. `cli.py` 的 `--effort` choices 里没有 `xhigh`——那是 Opus 4.7 新增、
   位于 `high` 与 `max` 之间的档位，官方明确说它是「most coding and
   agentic use cases 的最佳设置」（也是 Claude Code 自身默认值）；官方对
   `max` 的评价是「可能过度思考、收益递减」。即使底层 `claude` CLI 支持，
   本项目也传不进去。
2. 默认模型是 `claude-opus-4-7`；Opus 4.8 是当前 Opus 旗舰，4.7 → 4.8 无
   任何 breaking change（纯 model-ID 切换）。官方对 4.8 的迁移建议是「从
   `high` 起步并迭代，而不是反射性地上 `xhigh`」。

超时侧：决策 #64 把 L3 语义审校超时解耦到 `[repair].semantic_timeout_s
= 1200` 之后，本轮**首次取得未删失的真实尾部 = 743s**（此前数据在 600s
处被砍、真实值未知）。1200 给了 1.6× 余量，可以有据地收紧。

## Conclusion and decisions

四件一起落（都是参数 / 接线，不改任何语义），目的是**用一个 stage 量出
xhigh 到底有没有杀掉双峰**——那是全部提速估计的依据。

1. `--effort` 加 `xhigh` 档位，默认 `max` → `xhigh`。
2. 默认模型 `claude-opus-4-7` → `claude-opus-4-8`。
3. repair 的 `_llm_call` 增加 `effort` 参数并透传给 `run_with_retry`；
   **方案 A（用户 2026-07-17 拍板）**：effort 由各调用点自己传，与现存
   `timeout` 的形态完全一致。L3 gate 复检 / T1 / T2 / triage 传
   `effort="medium"`；Phase A 全量语义检查不传，吃 backend 默认。
4. `[repair].semantic_timeout_s` 1200 → 900（实测未删失尾部 743s，900 给
   1.2× 余量）。

**读代码时发现两处 todo 未覆盖但必须一起改的连带项**（否则本轮直接崩）：

- `orchestrator.py` 有**两个** `_llm_call` 闭包（phase 2 line 2110 /
  phase 3 line 3288）。phase 2 的缩水版 repair（决策 #59）也走 T1
  `local_patch`，只改 phase 3 那个 → phase 2 一调 T1 就 `TypeError`。
  两个闭包都要加 `effort` 参数。
- `extraction/repair/tests/` 的全部 llm_call stub 签名是
  `(prompt, timeout=600)`，不接 `effort`。调用点一传 `effort="medium"`
  即 `TypeError`——而 `_smoke_l3_gate` 正是本轮完成标准之一。stub 签名
  需一并放宽。

**暂不做的事**（用户 2026-07-17 拍板）：

- 不动 target 数量。实测 per-target 字段只占 stage_snapshot 的 26%，
  20→10 只省 ~13%；且头号瓶颈 `char_support` 产出的 `memory_timeline`
  根本没有 per-target 字段（它是事件数组），砍 target 对它零影响。
- 不拆 `char_support`。瓶颈是双峰不是内容量，拆成 4 路每路照样可能爆。
- 不用 fast mode（需要 API，不采用）。
- 与 T-GATE-SCOPED-RECHECK 必须分两次 `/go`——那条改审校语义，混在一起
  就分不清耗时变化是 effort 降档还是复检变窄造成的（单变量）。

## Planned action list

- file: `extraction/persona_extraction/cli.py:101` → `--effort` 的
  `choices` 加 `"xhigh"`；`default` 由 `"max"` 改为 `"xhigh"`；help 同步
- file: `extraction/persona_extraction/cli.py:97` → `--model` 的
  `default` 由 `"claude-opus-4-7"` 改为 `"claude-opus-4-8"`；help 同步
- file: `extraction/persona_extraction/orchestrator.py:3288`（phase 3
  repair 的 `_llm_call` 闭包）→ 增加 `effort: str | None = None` 参数，
  透传给 `run_with_retry(..., effort=...)`
- file: `extraction/persona_extraction/orchestrator.py:2110`（phase 2
  repair 的 `_llm_call` 闭包）→ 同上（计划外连带项，见上）
- file: `extraction/repair/checkers/semantic.py` → `check` / `_review_file`
  接受 `effort` 并透传；L3 gate 复检传 `effort="medium"`（Phase A 不传）
- file: `extraction/repair/coordinator.py:421` → L3 gate 的
  `pipeline.run_layer(..., layer=3)` 传 `effort="medium"`
- file: `extraction/repair/fixers/local_patch.py:106` → T1 传
  `effort="medium"`
- file: `extraction/repair/fixers/source_patch.py:122` → T2 传
  `effort="medium"`
- file: `extraction/repair/triage.py:370` → triage 传 `effort="medium"`
- file: `extraction/repair/tests/_smoke_l3_gate.py` +
  `_smoke_triage.py` → llm_call stub 签名放宽以接受 `effort`（计划外
  连带项，见上）
- file: `extraction/config.toml` `[repair]` → `semantic_timeout_s`
  1200 → 900，取值依据注释改写
- file: `extraction/persona_extraction/core/config.py::RepairAgentConfig`
  → `semantic_timeout_s` 默认值 1200 → 900；注释内取值依据改写为「实测
  未删失尾部 743s，900 给 1.2× 余量」
- file: `ai_context/decisions.md` + `docs/decisions.md` → #64 就地修订
  `semantic_timeout_s` 取值；新增一条 effort 分档决策
- file: `extraction/README.md` §配置分段 + §子进程超时 → 数字同步
- file: `docs/requirements.md` §11.8 自我保护 + 配置分节表 → 数字同步
- file: `docs/architecture/extraction_workflow.md` §子进程硬超时 → 数字
  同步
- file: `docs/todo_list.md` → 条目移出到 `docs/todo_list_archived.md`
  §Completed + 刷新 Index

## Validation criteria

- [ ] `python -c "import extraction.persona_extraction.cli"` 等 import
      smoke 无 error
- [ ] `--effort xhigh` 能被 argparse 接受（`--help` 里出现 `xhigh`，
      且 default 显示 `xhigh`）
- [ ] `--model` default 为 `claude-opus-4-8`
- [ ] `load_config().repair.semantic_timeout_s == 900`
- [ ] `_smoke_l3_gate` 全过（stub 已接 `effort`，无 TypeError）
- [ ] `_smoke_4_lane_merge_and_slice` 全过
- [ ] repair 的四类调用（L3 gate / T1 / T2 / triage）在代码层可确认传了
      `effort="medium"`，且 Phase A 全量检查不传
- [ ] grep 残留：`1200` 在 `[repair].semantic_timeout_s` 语境下 = 0；
      `claude-opus-4-7` 作为默认值 = 0
- [ ] `_smoke_triage` HEAD 即坏（T-SMOKE-TRIAGE-BROKEN，正交）——本轮不
      要求它过，但要确认失败原因与本改动无关

**延后到实跑**（非本次 `/go` 的验收项，需要挂机一个完整 stage）：
跑至少 1 个完整 stage 与本轮基线对比（基线 S001 36min / S002 25min /
S003 35min）：提取墙钟、是否仍出现 ~2100s 爆掉样本、产物 schema 是否仍
合法、defer 债是否未增加。

## Execution deviations

1. **两处计划外连带改动**（PRE 已预先声明，非执行中新发现）：
   `orchestrator.py` 的 phase 2 `_llm_call` 闭包、`extraction/repair/tests/`
   的 7 处 llm_call stub 签名（`_smoke_l3_gate` 3 处 + `_smoke_triage`
   4 处）。两者都是「不改即崩」，非扩张。
2. **额外改了 `config.toml` 的 `[phase0].recovery_effort` 注释**（计划清单
   未列）。该注释原文写「主流程默认 max 保留质量 + sweep 用 high 救撞墙」，
   本轮把主流程默认改成 `xhigh` 后这句话直接变成假话；档位列举
   `（low/medium/high/max）` 也缺 `xhigh`。属 `conventions.md` §只描述当前
   设计的必修项，不是新功能。`recovery_effort` 的**取值本身不变**（`high`
   相对新默认 `xhigh` 仍是降档，#49 语义成立）。
3. `semantic.py` 的 `check_scoped` 也一并加了 `effort` 参数（计划清单只列
   了 `check` / gate 复检）。它与 `check` 共用 `_review_file`，签名不一致会
   留下一个「同一个 checker 两条路径行为不同」的坑。它目前仍是零调用方的
   死代码（决策 #62 记载），本轮不动其死代码状态。
4. **复审阶段追加 4 处注释修复**（Step 5 findings，全部一行级）：偏差 #2
   识别的「主流程默认 max」失效句在**三个副本**里，初次只修了
   `config.toml:49` 一处，复审补修
   `docs/architecture/extraction_workflow.md`（同句）与
   `core/llm_backend.py:321/348`（档位枚举缺 `xhigh` + 同句「max → high
   降档」）；`config.toml:41` 的 1800s 取值依据、`docs/decisions.md` #64
   的「今日 L3（opus + effort=max…）」现在时断言、`docs/todo_list.md:912`
   的「#64 把超时提到 1200s」（#64 本轮已改写为 900s）一并脱敏 / 更正。

<!-- POST phase fills in -->

## Landed changes

四件计划内改动全部落地（effort 加 `xhigh` 档并改默认、模型切
`claude-opus-4-8`、repair 的 effort 透传按方案 A 接线、`semantic_timeout_s`
1200 → 900），外加 PRE 预先声明的两处「不改即崩」连带项与复审补修。
文件级细节即 commit diff，不在此重复枚举。

**本轮只改参数与接线，未改任何提取 / 修复语义。** 提速幅度尚未验证 ——
需挂机跑 ≥1 个完整 stage 与基线对比，见下方「延后到实跑」。

## Diff from plan

对照 PRE §Planned action list：

- **新增**（3 项，均见 §Execution deviations）：phase 2 的第二个 `_llm_call`
  闭包、7 处 smoke stub 签名、`config.toml [phase0].recovery_effort` 注释；
  复审阶段另追加 4 处一行级注释 / 数字更正。
- **删除**：无。
- **修改**：`semantic.py` 的透传面比计划稍宽（`check_scoped` 也接了
  `effort`，见偏差 #3）。

## Validation results

- [x] import smoke —— `cli` / `orchestrator` / `repair.*` 全部 import 无 error
- [x] `--effort xhigh` 被 argparse 接受 —— `--help` 显示
      `{low,medium,high,xhigh,max}`，default `xhigh`。**底层依赖已实证**：
      `claude --help` 输出 `--effort <level> … (low, medium, high, xhigh,
      max)`，非纸面推断
- [x] `--model` default = `claude-opus-4-8`
- [x] `load_config().repair.semantic_timeout_s == 900`（toml 与 dataclass
      默认值一致）
- [x] `_smoke_l3_gate` 全过（3 场景，无 `TypeError`）
- [x] `_smoke_4_lane_merge_and_slice` 全过
- [x] repair 四类调用（L3 gate / T1 / T2 / triage）传 `effort="medium"`，
      Phase A 全量检查不传 —— 代码层确认 + 复审独立核对
- [x] grep 残留 = 0：`semantic_timeout_s` 语境下的 `1200`、作为默认值的
      `claude-opus-4-7`（剩余命中均为 `logs/` / 归档 / 决策溯源等合法历史）
- [x] `_smoke_triage` HEAD 即坏且与本改动正交 —— 在 HEAD 的干净 worktree
      跑对照，失败点逐字相同（`scenario_a_pre_t3_accept` 的
      `assert result.accepted_notes`，`triage calls=0`），是 `AssertionError`
      而非 `TypeError`。符合 T-SMOKE-TRIAGE-BROKEN 的已知结论

**复审**：Code 维度零真缺陷（链路核对基于实际签名，非假设；`run_layer` 的
kwargs 广播已证实安全 —— 全仓仅 `SemanticChecker` 是 layer 3，其余 extra
checker 均为 layer 2 且都带 `**kwargs`；`pipeline.json` 不持久化 effort /
model，resume 路径不会读到历史值撞 choices 校验）。Surface 维度 5 条
findings 全部就地修复（见偏差 #4），决策对 lockstep 逐位核对通过、
todo Index 与正文无漂移。

**延后到实跑（非本轮验收项）**：跑 ≥1 个完整 stage 与基线对比（S001 36min
/ S002 25min / S003 35min）—— 提取墙钟、是否仍出现 ~2100s 爆掉样本、产物
schema 是否仍合法、defer 债是否未增加。**这是「xhigh 有没有杀掉双峰」的
唯一判据，也是 T-GATE-SCOPED-RECHECK 单变量前提的实际内容。**

## Completed

- **Status**: DONE
- **Finished**: 2026-07-17 07:36:19 EDT
