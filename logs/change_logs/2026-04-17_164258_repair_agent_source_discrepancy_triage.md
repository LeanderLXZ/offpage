# Repair Agent — Source-Discrepancy Triage & `accept_with_notes`

- 时间：2026-04-17 16:42 EDT
- 工作区：`/tmp/persona-engine-source-discrepancy`（基于 master `8afb87c`）
- 目标分支：合并后落到 master；extraction 分支再按需 merge

## 背景

L3 语义 gate 会抓到"原小说自带的 bug"——作者矛盾、typo、角色名/代称混用、
世界规则冲突等。没有本次变更时，这类问题只能靠 T3（20 分钟全文件重生成）
+ 不断打补丁，结果要么 T3 无效被 cap 挡掉（`t3_max_per_file=1`），要么
越改越离谱。本次给 repair agent 加一个 **源文件问题 triage** 机制，允许
在两个点合法地 `accept_with_notes`：

1. **pre-T3**：T0/T1/T2 都没解决、正要升级到 T3 时，先跑一次轻量级 LLM
   判定。若残留 L3 issue 全部被判为"源文件自带"，**跳过 T3**（省 ~20 分钟）
2. **post-L3-gate**：每轮 L3 gate 出结果后，对 gate_blocking 再 triage 一次

被接受的 issue 不再被当成"待修复"，而是写成 `SourceNote` 存到
`{entity}/canon/extraction_notes/{stage_id}.jsonl`，stage 依旧 COMMITTED，
sidecar notes 作为审计痕迹和未来 fixer 的线索。

## 反作弊硬线（全部程序校验）

1. 只有 `semantic` 类 issue 可以被接受；L0/L1/L2（JSON 语法/schema/结构）
   错误一律拒绝 triage——机械错误不可能是"源文件的错"
2. 每个接受判定必须给出 `chapter_number + line_range + 逐字 quote`；程序用
   `chapter_text.find(quote) >= 0` 校验 quote 是章节文本的字面子串
3. `discrepancy_type` 必须是 12 项闭集之一（见 `DISCREPANCY_TYPES`）
4. 每文件接受上限 `accept_cap_per_file=3`（跨轮次累计），防止 LLM 面对
   "修不动"的 bug 时把所有问题都甩锅给作者
5. **T3_CORRUPTED 硬停**：T3 跑完后立即对被重写文件做一次 scoped L0–L2
   检查，发现任何 L0–L2 错误即以 `T3_CORRUPTED` 中止 Phase B 并 FAIL，
   **不走 triage**

## 实施内容

### 1. 需求文档 `docs/requirements.md`

- §11.4.4 `RepairConfig` dataclass 示例新增 `triage_enabled: bool = True`、
  `accept_cap_per_file: int = 3`
- §11.4.5 三阶段流程重写：Phase B 循环里明确出现 Triage-1（pre-T3）、
  Triage-2（post-gate）、T3 corruption 硬停的三个 hook；给出 LLM 预算公式
- §11.4.6 安全阀新增 T3_CORRUPTED、per-file accept cap
- §11.4.7（新建）完整 "Source discrepancy triage + accept_with_notes" 章节：
  12 种 `discrepancy_type` 枚举、`SourceEvidence` / `SourceNote` dataclass、
  存储路径规范、T2/T3 自报通道说明
- 原 §11.4.7 顺延为 §11.4.8

### 2. 核心代码

**新文件**：
- `schemas/source_note.schema.json` — JSON Schema draft 2020-12，对应
  `SourceNote` dataclass，严格约束 `note_id` 正则 `^SN-S[0-9]{3}-[0-9]{2}$`、
  `issue_category` 只允许 `semantic`、`discrepancy_type` 12 项闭集、
  `chapter_sha256`/`quote_sha256` 为 64 位 hex
- `automation/repair_agent/triage.py` — `Triager` 类：每文件一次批量
  prompt（`TRIAGE_SYSTEM` 内含闭集、反作弊说明、输出 schema）；
  LLM 返回 `verdicts: []`；程序逐条校验 quote→拒绝不匹配的；
  per-file cap 在此处强制。还提供 `build_source_note()` 把
  `TriageVerdict` 转成可持久化的 `SourceNote`（自动算 quote/chapter SHA-256）
- `automation/repair_agent/notes_writer.py` — `NotesWriter`：从 file path
  推导 entity root（`.../canon` 或 `.../world`），生成
  `extraction_notes/{stage_id}.jsonl`；`next_seq`/`allocate_note_id` 从已
  存在的 jsonl 里读取最大 seq 保持单调递增；`append()` 用 tmp+rename 原子追加
- `automation/repair_agent/_smoke_triage.py` — 三个场景：(A) 合法 quote
  被接受并跳过 T3、(B) 错误 quote 被程序拒绝、(C) accept_cap_per_file
  生效

**修改**：
- `automation/repair_agent/protocol.py`：`RepairConfig` 新增
  `triage_enabled`、`accept_cap_per_file`；新增 `DISCREPANCY_TYPES`、
  `SourceEvidence`、`SourceNote`、`TriageVerdict` dataclasses；
  `FixResult` 新增 `source_inherent_candidates`；`RepairResult` 新增
  `accepted_notes`
- `automation/repair_agent/context_retriever.py`：`__init__` 加两个 LRU-
  like 字典缓存；`_load_chapter`/`_load_chapter_summary` 接入缓存；
  对外暴露 `load_chapter_text()` 和 `get_stage_chapters()` 给 triager
- `automation/repair_agent/coordinator.py`：完全重写
  - 构造共享 `ContextRetriever` 传给 T2/T3 和 triager
  - 新 helper `_run_triage_round()`：per-file 分组、应用 cap、写 notes、
    返回剩余 issue
  - `_run_fixer_with_escalation()` 在 `tier == 3` 时先跑 pre-T3 triage；
    T3 跑完后做 scoped L0–L2 校验（T3_CORRUPTED 硬停）；返回
    `(modified_files, t3_corrupted, t3_candidates)`
  - Phase B 主循环：L3 gate 出结果后跑 post-gate triage
  - Phase C：若 `t3_corrupted` 直接用特殊报告路径 FAIL
  - `RepairResult.accepted_notes` 填充；`_build_report` 打印 note 摘要
- `automation/repair_agent/fixers/source_patch.py`：prompt 增加
  `source_inherent` escape-hatch 描述；`fix()` 解析 LLM 输出——若看到
  `{"source_inherent": true, ...}` 对象，打包成 `TriageVerdict` 放进
  `FixResult.source_inherent_candidates`（作为 pre-T3 triage 的 prior）
- `automation/repair_agent/fixers/file_regen.py`：同上，但 T3 是整文件
  输出，所以用 `__source_inherent__: []` 顶层数组承载自报；写文件前
  剥掉这个字段；T3 自报过的 issue 不计入 `resolved_fingerprints`，留给
  post-gate triage 判定
- `automation/repair_agent/__init__.py`：公共 API 增加 `SourceNote`、
  `SourceEvidence`、`TriageVerdict`、`DISCREPANCY_TYPES`

### 3. 测试

两个 smoke 都通过：

```
$ python -m automation.repair_agent._smoke_l3_gate
OK — L3 gate fired, T3 capped at 1, verdict FAIL as expected.

$ python -m automation.repair_agent._smoke_triage
[A] passed=True  notes=1  T3 regen calls=0  triage calls=1
[A] OK — pre-T3 triage accepted, notes persisted
[B] passed=False  notes=0
[B] OK — bad quote rejected by program verification
[C] passed=False  notes=2  persisted_lines=2
[C] OK — accept_cap_per_file enforced
```

场景 A 证实：当所有 L3 残留都是源文件 bug 时，T3 调用数 = 0、note 持久
化到 `characters/A001/canon/extraction_notes/S001.jsonl`、note_id 是
`SN-S001-01`、`issue_category` 是 `semantic`、`source_evidence` 带 64 位
hash。场景 B 证实：quote 不在章节里时，程序一行 `find(quote) >= 0` 直接
判否，不会被写入。场景 C 证实：`accept_cap_per_file=2` 下即便 LLM 把五个
issue 都判为源文件问题，最多只接受两条。

### 4. 文档对齐

所有 L3 gate / T3 相关段落同步新增 triage 描述：
- `ai_context/architecture.md`（Phase 3 repair agent 段落）
- `ai_context/current_status.md`（repair_agent 摘要）
- `ai_context/decisions.md`（新增 25a 条）
- `ai_context/requirements.md`（repair agent 段落）
- `docs/architecture/extraction_workflow.md`（ASCII 流程图 + 关键设计段落）
- `automation/README.md`（目录树、repair agent 章节）

## 不改动的决策

- 不新增 stage 状态：依旧 `COMMITTED`，sidecar notes 作为可审计附加物
  （下游消费者无需改动）
- 不跨 run 缓存 triage 结果：每次 `run()` 独立判定，避免 stale verdicts
- 不对 source SHA 做 resume 幂等（留给将来）
- 不做 Phase A 的"suspicion hints"（留给将来）
- 不按 discrepancy_type 做专用处理（所有类型共享通用引文校验）

## 后续

- 在实际 stage 上观察 triage 命中率和假阳性率；若 `author_contradiction`
  的误判高，再考虑把它拆成更细的子类型
- 未来做"自动 fixer"时，可直接读 `extraction_notes/` 的
  `future_fixer_hint` 字段驱动
- 注意 `extraction_notes/` **未** 加入 `.gitignore`，设计上就该随 stage
  一起 commit，作为审计资料

## 合并路径

worktree `/tmp/persona-engine-source-discrepancy` 基于 master `8afb87c`。
变更涉及 `ai_context/` / `docs/` / `automation/` / `schemas/`，纯架构加
固，不会和正在跑的 extraction 分支冲突。建议：

1. worktree commit → push master
2. 回到 extraction 分支：`git stash`（阶段 02 脏改动）→
   `git checkout extraction/<work_id>` → `git merge master` →
   `git stash pop`
