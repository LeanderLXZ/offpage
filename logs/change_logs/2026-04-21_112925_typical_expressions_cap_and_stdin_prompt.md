# 2026-04-21 11:29 — typical_expressions 上限放宽 + claude -p 改走 stdin 临时文件

## 背景

在某 stage 提取中触发两层失败：

1. **Schema 硬门控**：LLM 在 `voice_state.emotional_voice_map[*].typical_expressions`
   与 `voice_state.target_voice_map[*].typical_expressions` 下产出 7 / 8 条短语，
   超过 schema `maxItems: 5`，判为 structural error 进入 Phase B 修复。
2. **修复 T3 全文件 regen 触发 ARG_MAX**：T3 prompt 携带原文文本（可达数十 KiB），
   与旧 JSON + issue 列表叠加后，通过 `claude -p <prompt>` 以单个 argv 传入子进程。
   Linux 单个 argv 字符串上限 `MAX_ARG_STRLEN ≈ 128 KiB`，execve 直接返回
   `E2BIG / [Errno 7] Argument list too long`，修复循环原地失败直至达到上限，
   stage 被标记为 `error`。

用户决策：放宽 schema 上限到 15，并将所有 `claude -p` 的 prompt 传递改走
唯一命名的临时文件 + stdin，从机制上彻底绕过 ARG_MAX。

## 改动清单

### 1. Schema 上限放宽

- `schemas/character/stage_snapshot.schema.json`
  - `voice_state.emotional_voice_map.items.properties.typical_expressions.maxItems`: 5 → 15
  - `voice_state.target_voice_map.items.properties.typical_expressions.maxItems`: 5 → 15

`schemas/character/voice_rules.schema.json` 中同名字段本就无 `maxItems` 约束，无需改动。
`automation/config.toml` 中不存在任何 `typical_expressions` 相关阈值键，已核查。

### 2. 文档同步

- `docs/requirements.md` §字段条数上限汇总表：`各 typical_expressions` 5 → 15，
  说明放宽原因（覆盖同一情绪/对象下的常见短句模板）。

prompt 模板 `character_snapshot_extraction.md` 中的 "主角 target 至少 5 条，
重要配角至少 3 条" 是**下限**（floor），放宽上限不冲突，保持不变。

### 3. ClaudeBackend prompt 走 stdin 临时文件

`automation/persona_extraction/llm_backend.py`：

- 新增模块级 `_prompt_tempfile(prompt, *, backend_tag, lane_name)` context manager：
  - 使用 `tempfile.mkstemp` 生成进程 + 线程原子唯一路径
  - 文件名带 `pid` 与清理后的 `lane_name`，便于并行/调试时识别归属
  - 退出时 `finally` 删除，异常/超时不泄漏
- `ClaudeBackend.run` 移除 `cmd` 中的 positional prompt，改为打开临时文件作为
  `stdin` 传入 `subprocess.Popen`。`claude -p` 未显式给 prompt 时自动读 stdin
  （已通过真实调用验证，haiku 2s 返回 "pong"）。
- `CodexBackend` 保持原 argv prompt 写法，新增注释标注同一 ARG_MAX 风险——
  本机未安装 codex CLI，无法验证其 stdin 接口，暂不动以免破坏潜在用户。

### 4. 作业数据层面

- Stage02 失败残留（7 modified + 5 untracked 艺术品）在 extraction 分支上
  `git checkout -- ...` / `rm ...` 回滚到 stage01 commit 后的干净工作树。
- `works/.../analysis/progress/phase3_stages.json` 中 stage02 从
  `state: error` / 带长 error_message 重置为 `state: pending` / 空 lane_states，
  以便下一轮 `--resume` 重新调度。

### 5. gitignore

`078e1c0 chore(gitignore): ignore .claude/*.lock runtime lockfiles` 先前只在
extraction 分支。此次按分支纪律 cherry-pick 到 master。

## 验证

```
# 并行 20 条 tempfile 唯一性 + 清理
tempfile uniqueness + cleanup OK (20 parallel)
sample path: /tmp/persona_claude_<pid>_snapshot_<lane>_<rand>.txt

# schema 合法性 + 8 条 typical_expressions 从失败变通过
stage_snapshot schema valid
maxItems = 15  (两处)

# baseline validator 无回归
validate_baseline(...) => PASSED=True, issues=0

# 真实 claude -p 端到端探测（haiku, max_turns=1, 1 个 prompt via stdin）
success: True
text: pong
duration: 2.4 s
```

## 分支影响

- master：schema + 文档 + llm_backend + gitignore cherry-pick
- `extraction/<work>`：承接 master 合并；本地 stage02 残留已回滚，
  progress JSON 已 reset 为 pending，准备 resume。

## 6. after-check 跟进改动

`/after-check` 针对前述改动做聚焦复审，共落 4 条后续（M1 / M2 / L3 / L4）；
用户决策：M1 跳过，M2 / L3 / L4 在本轮补齐；统一追加到本 log 而非新开一篇。

### 6.1 L3 — voice_rules.schema.json 对齐 maxItems=15

- `schemas/character/voice_rules.schema.json`
  - `emotional_voice_map.items.properties.typical_expressions.maxItems`: 新增 15
  - `target_voice_map.items.properties.typical_expressions.maxItems`: 新增 15

原 voice_rules schema 无该约束（stage_snapshot 层才有）。对齐后两份 schema
在该维度完全对称，避免 baseline 校验与 stage 快照校验不一致。

### 6.2 M2 — prompt 模板追加上限 15 条的说明与截断策略

`automation/prompt_templates/character_snapshot_extraction.md`：

- 原单行 "typical_expressions 下限：主角 target 至少 5 条，重要配角至少 3 条"
  拆为两条：保留下限说明，新增 "上限 15 条（schema 硬门控）" 独立段
- 明确 "原文有多少就写多少，不必刻意凑满"——避免 LLM 为填满额度敷衍造句
- 超限时的 **截断策略**：保留最贴合当前 stage 语境（当前情绪/关系阶段、
  当前对象、当前核心冲突）的表达；丢弃跨 stage 通用或已被
  `dialogue_examples` 覆盖的条目
- 同一规则显式覆盖 `emotional_voice_map[*].typical_expressions` 语境维度
  （当前情绪下的典型短句），避免 LLM 只应用到 target_voice_map 层

### 6.3 L4 — codex stdin ARG_MAX 跟进登记

`docs/todo_list.md` "下一步" 新增 `[T-CODEX-STDIN]` 条目：

- 动机：本轮 stdin 改造只覆盖 ClaudeBackend；CodexBackend argv 传 prompt
  的路径仍对大 prompt 脆弱
- 行动项：验证 `codex` CLI 是否支持从 stdin 读取 prompt（`echo 'hi' | codex`
  或 `codex -` / `codex --prompt -`）；若支持则照搬 ClaudeBackend 写法
- 验证条件：> 150 KiB prompt + 5 并行 lane 端到端不触发 E2BIG
- 不在本轮修改，仅登记，避免无 CLI 环境盲改破坏 codex 用户

### 6.4 M1 — 跳过（用户决策）

`ai_context/` 不需要记录 stdin tempfile 机制细节；只需知道 backend 大致职责，
细节在代码与本 log 中可查。

## 验证（本轮追加）

```
# 两份 schema 合法性 + maxItems=15 在两处（emotional_voice_map +
# target_voice_map）
voice_rules schema: valid
stage_snapshot schema: valid
voice_rules typical_expressions maxItems: ['15', '15']
stage_snapshot typical_expressions maxItems: ['15', '15']

# voice_rules 功能性：15 条接受，16 条 schema 拒绝
voice_rules 15 items: accepted
voice_rules 16 items: correctly rejected
```

