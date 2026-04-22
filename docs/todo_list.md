# TODO List（待办任务清单）

---

## 文件说明

### 用途

记录**计划完成但尚未完成**的具体工程任务。区别于：
- `ai_context/next_steps.md`：**架构方向**和高层 roadmap（用英文）
- `ai_context/current_status.md`：**当前项目状态快照**
- `docs/logs/`：**历史记录**（时间戳，只追加不修改）
- `docs/architecture/`：**正式架构文档**

本文件是**工程级**的待办队列，含文件路径、行号、改动清单、验证步骤。

### 记录什么

✓ 具体到文件/函数级的改动任务
✓ 每条任务必须包含：**动机**、**改动清单**（含文件路径和行号）、**验证方法**、**预估工作量**、**依赖**、**完成标准**
✓ 讨论中尚未定案的方案及其权衡

### 不记录什么

✗ 架构方向 / 高层 roadmap → 写进 `ai_context/next_steps.md`
✗ 已完成任务 → **完成即删除**（历史价值写进 `docs/logs/` 时间戳日志）
✗ 临时调试笔记 / 中间思考 → 对话上下文或 plan，不持久化
✗ 当前运行状态 / 进度 → 写进 `works/*/analysis/progress/`

### 如何更新 / 删除

**添加任务**：放进合适的分节（立即执行 / 下一步 / 讨论中）。新任务必须有上方"记录什么"列出的全部字段。

**任务进入执行**：不改位置（仍在"立即执行"或"下一步"）；若中途发现需要拆解，原位扩展或增加子任务。

**任务完成**：
1. **立即从本文件删除整条**。不留"已完成"标记、不划删除线、不移到"历史"节——本文件无历史层
2. 若该任务产生了值得沉淀的结论、新架构决策、或可复用经验，写一条 `docs/logs/{YYYY-MM-DD_HHMMSS}_{slug}.md`
3. 若完成涉及 `ai_context/` 的持久事实变化（current_status / decisions / next_steps 等），同步更新
4. **从"下一步"首条提升一条到"立即执行"**，保持 pipeline 不空转；若"下一步"也空则跳过。提升时不改任务内容，仅挪位置

**任务废弃**：写一条 `docs/logs/` 记录废弃原因后从本文件删除；若废弃的是"立即执行"条目，同样触发上述第 4 步的提升。

**讨论转落地**：讨论中章节产生结论时，无论整体定案还是阶段性结论，都要立即把结果反映到对应章节——
- **整体定案**：把条目从"讨论中"整条移到"立即执行"或"下一步"，补全成完整任务（动机/清单/验证/依赖/完成标准）
- **部分定案**：把已定案的子任务单独拆出迁移到对应章节（作为独立任务条目），未定案部分继续留在"讨论中"并更新上下文说明已拆分出去的部分
- **结论颠覆原假设**：若讨论结果反而证明某已在"立即执行/下一步"的任务不再必要，按"任务废弃"流程处理

### 读取时机

- 用户问及待办 / 即将做什么 / 接下来该做什么
- 开始任意改动前 **先查一次**，避免重复规划
- 讨论到可能已登记的话题时
- **默认不主动读取**（不进入 session 启动的 `ai_context/` 读取序列）

---

## 立即执行

（暂无条目）

---

## 下一步

（暂无条目）

---

## 讨论中（未定案）

### [T-CODEX-STDIN] CodexBackend prompt 走 stdin 临时文件

**上下文**

`ClaudeBackend` 已在
`automation/persona_extraction/llm_backend.py::ClaudeBackend.run` 把 prompt
改走唯一临时文件 + stdin，绕过 Linux `MAX_ARG_STRLEN ≈ 128 KiB` 的 argv
上限。`CodexBackend.run` 仍用 `cmd = ["codex", "--quiet", "--full-auto",
prompt]`（同文件 L378 附近），大 prompt（尤其 T3 全文件 regen）会在
切到 `--backend codex` 时复现 `[Errno 7] Argument list too long`。

当前已加注释标注风险，未改代码——本机未安装 codex CLI 无法实测其 stdin
接口（是否自动读 stdin / 是否要 `-` / 是否要 `--prompt -`）。

**待决策项**

1. codex CLI 的 stdin 契约到底是哪种形式？三种候选：
   - `echo 'hi' | codex --quiet --full-auto`（自动读 stdin）
   - `codex --quiet --full-auto -`（显式 `-`）
   - `codex --quiet --full-auto --prompt -`（`--prompt` flag + `-`）
2. 是否仍坚持与 ClaudeBackend 对称？也可以走 `--input-file /tmp/xxx` 这类
   文件传递（若 codex 支持），避免 stdin 管道在并发下意外关闭的风险

**改动清单（待契约确认后落地）**

1. `automation/persona_extraction/llm_backend.py::CodexBackend.run` 复用
   `_prompt_tempfile` + stdin 文件句柄的写法，移除 cmd 中的 positional
   prompt
2. 删掉 `CodexBackend.run` 开头那段 "NOTE: codex CLI still receives the
   prompt via argv ..." 注释
3. 小 prompt smoke：`create_backend('codex', ...).run('ping')`

**暂不做的事**

- 不在没有 codex CLI 的机器上盲改——三种候选形式有两种会 silent hang，
  必须实测
- 不把 argv 传递路径保留为 fallback——要么切 stdin 要么不切，保留两路
  只会让并发下的错误更难定位

**依赖**：有 codex CLI 的机器 / 订阅

**未落地原因**

- 当前所有 extraction 默认走 `--backend claude`，codex 分支未被激活使用；
  问题是潜在风险而非阻塞

---

### [T-SIMULATION-MODE-MARKER] simulation 运行时注入 worker-mode marker

**上下文**

`CLAUDE.md` / `AGENTS.md` 顶部的 Worker-Mode Short-Circuit 已预留
`[simulation_runtime_mode]` 标记：当 system prompt 包含该字符串时，
worker 跳过 `ai_context/` 加载与所有自检，只按 user prompt 执行。

extraction 侧已在 [automation/persona_extraction/llm_backend.py](automation/persona_extraction/llm_backend.py)
注入对应 `[extraction_worker_mode]`。simulation 侧预留了入口但尚无代码：
`simulation/` 当前只有 contracts / flows / prompt_templates / retrieval /
README.md，零 Python。

**待决策项**

1. simulation runtime 的 LLM backend 选型（是否复用 `ClaudeBackend` 类，
   还是独立 backend）
2. marker 注入点：每轮 user→character 对话的 LLM 调用、retrieval
   辅助调用、`search_memory` tool 的内部 LLM 调用，全部都需注入还是
   按调用类型区分

**完成标准**

- simulation runtime 首个实装的 LLM 调用处，命令行参数追加
  `--append-system-prompt "[simulation_runtime_mode]"`（或等价机制）
- 本 todo 条目删除

**未落地原因**

- simulation runtime 尚未开始实装；无注入点

**依赖**：simulation runtime 首次实装

---

### [T-PHASE5-RETRIEVAL] 新增 Phase 5 生成 retrieval 产物

**上下文**

多处 canonical docs 宣称 `works/*/indexes/` 是 committed 产物
（`ai_context/current_status.md:157`、`ai_context/requirements.md:229`、
`ai_context/decisions.md:174,225`、`docs/architecture/data_model.md:160,475`、
`docs/architecture/system_overview.md:36,326`），但当前没有任何 Phase
承担生成职责——首作 `works/{work_id}/indexes/` 目录在磁盘上不存在。

计划：新增 **Phase 5**，专责生成 retrieval 相关产物，统一承接现在散落的
缺口。覆盖范围初定：

- `works/{work_id}/indexes/vocab_dict.txt`（jieba 自定义词典）
- 关键词 / 专名抽取结果
- 索引数据库（FTS5 / 其他）
- RAG 相关 embedding / chunking 产物
- 其它 retrieval 层启动所需的预计算产物

**待决策项**

1. Phase 5 的产物是 committed 还是 local-only？
   - 若 committed：需决定 `vocab_dict.txt` / 关键词表等是否落仓；
     体积上限？
   - 若 local-only：`.gitignore` 加 `works/*/indexes/`；删除 ai_context /
     docs 中"committed"叙述
2. Phase 5 入口：独立 CLI 子命令 vs. `--start-phase 5`？
3. 触发门控：是否要 Phase 3.5 passed 才能进 Phase 5？（类比 Phase 4
   的独立性）
4. 与运行时 retrieval 实现的边界：Phase 5 产 artifact，运行时消费——
   但 embedding 模型选型 / chunking 策略需先定好
5. 并行度：是否复用 Phase 4 的 per-chapter 并行模式？

**未落地原因**

- retrieval 层整体设计尚未动工（见 `ai_context/current_status.md` Current
  Gaps：No retrieval implementation）
- Phase 3 仍在进行（1/49 committed），且即将回滚重跑，Phase 5 要等
  Phase 3 真正完成有完整 stage_snapshots 作为源

**暂不做的事**

- 不改 ai_context / docs 里"committed indexes"的叙述（等 Phase 5
  落定后再批量同步，否则来回改噪声大）
- 不把 `works/*/indexes/` 加入 `.gitignore`（决策未定）
- 不要把 `vocab_dict.txt` 硬塞进 Phase 2.5 / Phase 3.5（B 方案已否决：
  两 Phase 本职不是 retrieval，硬塞会扭曲 Phase 边界）

**依赖**：Phase 3 全量完成 + retrieval 层设计定稿

---

### [T-RETRY] claude -p 失败的智能重试策略

**上下文**

某次长 lane 跑 38m 后 exit 1，未被 `run_with_retry` 重试。用户提问：短时间内 exit 是否可以重试或退避？T-LOG 完成后，长时失败现在可见 `subtype` / `num_turns`，重试决策可基于实际信号。

**现有机制**（[llm_backend.py `run_with_retry`](automation/persona_extraction/llm_backend.py)）

| 错误类型 | 识别 | 处理 |
|---|---|---|
| `fast_empty_failure` | duration < `[backoff].fast_empty_failure_threshold_s` + stderr 空 + exit N | 按 `[backoff].fast_empty_failure_backoff_s` 序列重试（默认 30s → 60s → 120s） |
| `rate_limit` / `usage_limit` | stderr 含 "rate limit" / "weekly" / "5-hour" / "too many requests" | **暂停所有新请求**直到 reset，然后重发同一 prompt（**不消耗重试次数**，§11.13） |
| `token_limit` | stderr 含 "context window" / "max_tokens" 等 | **不重试** |
| 通用长时 exit N | stderr 空 + duration 长 | **不重试** |

**待决策项**

1. **短时间阈值扩大？** 当前 5s 过严。char_snapshot 正常 10-20m，任何 <60s（或 <120s）失败都不是真正工作后失败，更可能是 CLI launch 错误或 API 连接失败。候选阈值：60s 或 120s。
   - 支持扩大：风险小（<2 分钟浪费），覆盖面更广
   - 反对扩大：仍在盲猜，不如等 T-LOG 完成后按 subtype 分流
2. **长时 exit 是否也重试一次？** 本次阶段 02 属此类。
   - 代价：再跑 40m；若也失败总计浪费 ~80m
   - 收益：若是瞬态错误能自愈
   - 观点：**等 T-LOG 完成，根据 stdout subtype 分类**：
     - `error_max_turns` → 不重试（同 prompt 同样触达）
     - `error_during_execution` → 重试 1 次（瞬态可能性大）
     - 无 subtype / 解析失败 → 可选重试 1 次
3. **退避策略** 暂无调整需求，现有 30s/60s/120s 合理

**未落地原因**

- T-LOG 已完成，stdout/subtype 可见——盲猜问题已解除
- 尚未收集足够的真实失败样本来验证不同 subtype 的重试收益

**争议**

- 短时阈值是否一次扩大到 60s？风险小；可独立先行
- 长时 exit 按 subtype 分流是否一步到位？待收集几次真实失败后决定
- 结论：**待定案**，需要几次真实失败样本佐证

**依赖**：T-LOG 已完成；可基于 `failed_lanes/` 日志样本决策

---

### [T-USER-AUX-SCHEMAS] users/ 辅助文件缺 schema

**上下文**

2026-04-20 codex audit (residual R3) 指出 users/ 下若干辅助文件无 schema
绑定，在 runtime 真正落地前最容易继续自由漂移：

- `users/_template/contexts/{context_id}/session_index.json`
- `users/_template/conversation_library/archive_refs.json`

**待决策项**

1. 每个辅助文件是否都要独立 schema，还是由总目录层级 schema 一并约束？
2. schema 发布顺序：立即补齐，还是与 simulation runtime loader 设计
   同步发布？

**未落地原因**

- simulation 运行时尚未动工，实际消费路径未定；现阶段只有模板占位，
  字段边界可能随 loader 设计调整

**暂不做的事**

- 不提前补 schema，避免与后续 loader 字段收敛方案冲突

**依赖**：simulation runtime loader 选型 / 设计定稿

---
