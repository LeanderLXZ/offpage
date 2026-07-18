# llm-section-effort-config

- **Started**: 2026-07-18 13:16:23 EDT
- **Branch**: main
- **Type**: GO
- **Status**: PRE

## Background / Trigger

会话中用户追问「config 里的 effort 是怎么设置的、分几层」，排查后发现 effort
的取值散在三个互不相干的机制里：

| 取值点 | 现状 |
|---|---|
| 全局默认 | `cli.py` argparse `--effort` default `"xhigh"`，**敲死在解析代码里** |
| Phase 0 救火 sweep | `[phase0].recovery_effort = "high"`，唯一进了 config 的 |
| repair 复读档 | 5 处 `effort="medium"` 字面量（T1 / T2 / triage / L3 gate / Phase C fallback） |

关键发现（比「5 处重复」更硬的那条）：**同一个 argparse 块里四个邻居，
`--backend` 读 `cfg.runtime.default_backend`、`--max-turns` 读
`cfg.phase3.max_turns`，而 `--model` 与 `--effort` 是敲死的字面量。** 后果是
`config.local.toml` 能覆盖 backend / max_turns，唯独覆盖不了 model 与 effort ——
纯粹的运行时常量住在 CLI 解析代码里，违反
`ai_context/conventions.md §Single Source of Truth`。

用户随后提议「单独开一节集中配置所有 AI 档位」。讨论中收敛掉两个问题：
段名不用 `tier`（与 repair 的 fixer 层 T0/T1/T2 撞车），以及集中程度取 B 方案。

## Conclusion and decisions

**方案 B（用户拍板）：全局默认进新段 `[llm]`；per-phase override 留在原段，
靠 `[llm]` 的段注释做索引。**

不选 A（全集中，把 `recovery_effort` / `recheck_effort` 也搬进 `[llm]`）：那
需要给键加 `phase0_` / `repair_` 前缀，而**需要用段名给键加前缀，通常说明它本
该待在那个段里**。`recovery_effort` 的语义是「phase 0 撞墙后怎么办」，属 phase 0
的故障处理策略，只是恰好用 effort 表达。

段名取 `[llm]` 而非 `[tier]`：本仓库 tier 已有既定含义（repair 的 T0/T1/T2），
`[tier]` 挨着 `[repair]` 放会误导。

落地后 effort 的取值被 3 个键穷尽：`[llm].effort`（全局默认，冷读吃它）/
`[phase0].recovery_effort` / `[repair].recheck_effort`（收敛 5 处字面量）。

**边界（有意不做）**：
- 不把 `[runtime].default_backend` 搬进 `[llm]` —— backend 是进程 / 传输层选择，
  与推理档位不是一回事，搬了 `[llm]` 就开始变杂物抽屉。
- 不新增 per-phase 抽取 effort 键（Phase 0/1/2/3/4 抽取 lane 共用
  `[llm].effort`）—— 无证据需要，要试可用 CLI。
- 不改任何档位数值：`xhigh` / `high` / `medium` 与 model `claude-opus-4-8`
  原样搬运，**行为不变**。

**必须写进 `[llm]` 段注释的一条**：`codex` backend 完全忽略 effort
（`llm_backend.py` 中 kwarg 被静默丢弃，codex CLI 无该参数）。这是唯一一处
「配了但不生效且无提示」的地方，不写出来就是给未来的人埋坑。

## Planned action list

- file: `extraction/config.toml` → 新增 `[llm]` 段（`model` / `effort` +
  per-phase override 索引注释 + codex 警示）；`[repair]` 新增 `recheck_effort`
- file: `extraction/persona_extraction/core/config.py` → 新增 `LLMConfig`
  dataclass；注册进 `_SECTION_TYPES` 与 `Config`；`RepairAgentConfig` 加
  `recheck_effort`
- file: `extraction/persona_extraction/cli.py` → `--model` / `--effort` 的
  argparse default 改读 `cfg.llm.*`（与相邻的 `--backend` / `--max-turns` 形态
  一致，help 文本同步标注来源段）
- file: `extraction/repair/protocol.py` → `RepairConfig` 加 `recheck_effort`
- file: `extraction/repair/coordinator.py` → 透传给 fixer / Triager 构造点；
  自身两处 `effort="medium"`（L3 gate 复检 / Phase C fallback）改读 config
- file: `extraction/repair/fixers/local_patch.py` / `fixers/source_patch.py` /
  `triage.py` → ctor 收 `recheck_effort`，去掉字面量
- file: `extraction/persona_extraction/orchestrator.py` → 两个 `RepairConfig`
  构造点透传 `recheck_effort`
- file: `extraction/README.md` + `docs/requirements.md` → 配置分节表新增
  `[llm]` 行 + `[repair]` 行补键
- file: `ai_context/decisions.md` + `docs/decisions.md` → #65 就地订正
  （effort 值的来源由字面量改为 config）+ 新增条目记录 `[llm]` 段归属

## Validation criteria

- [ ] `python -c "import extraction.persona_extraction.cli"` 无错
- [ ] `load_config()` 能读到 `llm.model` / `llm.effort` / `repair.recheck_effort`；
      `config.local.toml` 覆盖链对三个新键生效
- [ ] argparse 的 `--model` / `--effort` default 确实来自 config（改 local toml
      后 `parse_args([])` 的取值跟随变化）
- [ ] `grep -rn 'effort="[a-z]*"' extraction/repair/` 命中 0
- [ ] `grep -rn 'default="xhigh"\|default="claude-opus-4-8"' extraction/` 命中 0
- [ ] repair smoke 全过（`_smoke_l3_gate`；`_smoke_triage` 为既有破损
      `T-SMOKE-TRIAGE-BROKEN`，不计本轮）
- [ ] 行为不变：5 个 repair 调用点实际传出仍为 `medium`，backend 实例默认仍为
      `xhigh`，model 仍为 `claude-opus-4-8`

## Execution deviations

- Step 2 计划外新增一句：`cli.py` 的 `--effort` help 末尾加
  `Ignored by the codex backend.`。这是 PRE「必须写进 `[llm]` 段注释的
  codex 警示」在 CLI 侧的一句话呼应——用户在 `--help` 处即可看到，成本一行。
- Step 5 复审查出 `[phase0]` 行在两份配置表镜像里都漏了 `recovery_effort`
  （#49 的历史漏记），导致本轮「effort 被 3 个键穷尽」的索引承诺查过去会落空。
  已顺手补齐 `extraction/README.md` + `docs/requirements.md` 两处。
- Step 5 另订正 `docs/architecture/extraction_workflow.md` 两处 effort 归属
  描述（原写 `LLMBackend.run(effort='high')` / 默认档挂在 `--effort`），
  它们正是本轮清扫目标的句式，属计划内文件的漏改。

<!-- POST phase fills in -->

## Landed changes

模型与推理档位的全局默认收进新的 `[llm]` 段（`model` / `effort`，argparse
default 改读它）；repair 复读档的 5 处 `"medium"` 字面量收进
`[repair].recheck_effort`。落地后 effort 被 3 个键穷尽。新增决策 #69，就地
订正 #65 的值来源表述。文件级明细见 commit diff。

## Diff from plan

- 计划内 9 条全部落地。
- 计划外 3 处（均记入 §Execution deviations）：CLI help 的 codex 一句话、
  两份配置表补 `[phase0].recovery_effort`、`extraction_workflow.md` 两处
  归属订正。三者都是本轮清扫目标的自然闭合，非范围扩张。

## Validation results

- [x] `import cli` / `orchestrator` 无错
- [x] `load_config()` 读到 `llm.model` / `llm.effort` / `repair.recheck_effort`；
      `config.local.toml` 覆盖链对三键生效。复审另用 DEBUG 捕获确认
      `load_config()` 期间**零条日志记录**（不只是零条 unknown-key warn）——
      排除「warn-and-drop 后恰好回退到相同默认值」的假阳性
- [x] argparse default 确实来自 config —— 临时写入 local toml 后 `--help`
      实际渲染出 `default: PROBE-MODEL, from [llm].model` / `default: low,
      from [llm].effort`（探针文件已清理）
- [x] `grep -rnE 'effort="[a-z]+"' extraction/repair/` 命中 0
- [x] `grep 'default="xhigh"\|default="claude-opus-4-8"' extraction/` 命中 0
- [x] smoke 7/8 —— `_smoke_l3_gate` 场景 A–G 全过；`_smoke_triage` 为既有破损
      `T-SMOKE-TRIAGE-BROKEN`（上一轮已 stash 对照证实 HEAD 即坏），正交
- [x] 行为不变 —— 复审用注入哨兵值证明五个复读点取的是注入值而非 dataclass
      默认，实际仍为 `medium`；另用 spy 捕获 Phase A 冷读的实际 kwarg 仍为
      `None`（#65 的冷读/复读分档判据未被破坏）；model / 主流程档位不变

## Completed

- **Status**: DONE
- **Finished**: 2026-07-18 13:28:52 EDT
