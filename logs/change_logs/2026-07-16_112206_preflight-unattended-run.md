# preflight-unattended-run

- **Started**: 2026-07-16 11:22:06 EDT
- **Branch**: main
- **Type**: GO
- **Status**: DONE

## Background / Trigger

用户明确表示**打算挂机长跑**首个作品的端到端提取（`handoff.md §下一步` 的高优先级
方向）。在此之前刚落地 commit `8f60da8`（`/full-review` 17 条 findings + 6 条 OQ），
修掉了 repair 层与编排层的高危缺陷。

用户问"挂着跑现在要修什么"。从上一轮 `/full-review`
（`logs/review_reports/2026-07-16_100448_opus-4-8_full-review-findings.md`）留 todo 的
项里，按"无人值守"这个新前提重新筛选——挂机把三条的优先级顶了上来：它们的共同点是
**故障静默、且没人在旁边喊停**。其余留 todo 项（M3/M4/M6/M7/M10/M17 等）是浪费或
测试问题，不会让挂机跑停摆或失控，本轮不碰。

M8 的修法有设计取舍（改变信号语义），Step 0 已询问用户：**选彻底版**
（`start_new_session` + `killpg` 杀整棵进程树）。

## Conclusion and decisions

**方向**：只修"挂机会被静默咬到"的三条，最小补丁。不扩大改动面。

**本轮改**：

- **M8（必修）** —— 子进程超时后 `communicate()` 无 timeout，等管道 EOF。
  `claude -p` 带 Bash 工具会派生继承管道的孙进程，`proc.kill()` 只杀直接子进程 →
  孙进程攥着写端 → lane 线程永久阻塞。决策 #49 明确 phase 0 **经常**撞 1800s wall，
  该路径必被走到。`--max-runtime` 非抢占式，救不了。挂机 = 卡整夜且不报错。
  **修法（用户选彻底版）**：`Popen(start_new_session=True)` 起独立进程组，超时路径
  `os.killpg(os.getpgid(proc.pid), SIGKILL)` 杀整棵树。代价：子进程不再收终端
  Ctrl+C（挂机不靠它；同仓 `process_guard.py:227` 已在用该参数）。
  两个 backend 同构：Claude(`:301`) + Codex(`:469`)。
- **H8（挂机翻案）** —— `_RESET_ISO`(`:94-97`) 无 `[Rr]esets?` 锚点、匹配 stderr 中
  任意位置的 ISO 时间戳，且是**第一个**被尝试的分支；ISO 分支(`:181-192`)直接
  `return dt`，无未来性校验（对比绝对时间分支 `:211-212` 有向前滚动）。解析出过去
  时刻 → `resume_at` 在过去 → `wait_if_paused` 的 `wait_s <= 0` → 立即 `_clear()`
  返回 → `llm_backend.py:662-663` `attempt -= 1; continue` → 同一 prompt 零间隔重发，
  `attempt` 永不增长、rate-limit 分支无任何退避。
  **上一轮建议"先加 WARN 观测再修"，挂机前提推翻该建议**：真烧起来无人喊停，
  等发现时额度已尽；修法三行，改错代价远小于赌它不触发。
- **M1（便宜且在热路径）** —— `character_snapshot_extraction.md` 与
  `prompt_builder.py:922-924` 注入的 hard-gate 块在 `timeline_anchor` 上正面冲突：
  后者列其为"程序注入字段（不要写）"，前者 `:133` 列为结构性骨架、`:150` 写"必填"、
  `:313` 要求"均已填写"。sub-lane 若听"必填"→ 触发 merge gate 1（partial 顶层字段集
  必须**等于** lane 分配）→ `MergeError` → 整个 char_snapshot lane 4 个 sub-lane 重跑。
  `config.toml:135` `char_snapshot_sub_lanes = true` 是生产路径，每角色每 stage 都摇
  一次骰子。归属已核实：`snapshot_merge.py:103-134` `FIELD_ALLOCATION` 不含它，
  `:204-211` `PROGRAM_INJECTED_FIELDS` 含它，`:507-515` merge 后由 `stage_title` 派生注入。

**本轮不改**（挂机不会被它们静默咬到）：M3（T2 第 2 次拿同样上下文，纯浪费）、
M4（catalog 白进 repair，浪费 token；`defer_unresolved_semantic=true` 下不会阻塞）、
M6/M7（json_repair 两条）、M10（#11e 覆盖不全）、M17（`_smoke_triage`，测试问题）、
M18-M20、全部 Low。M9（lane_scope 散文说"两个 sub-lane"实为 3）与 M1 同文件，
但它不会触发 MergeError，本轮不顺手改。

## Planned action list

- file: `extraction/persona_extraction/core/llm_backend.py` → **M8**: 两个 backend 的
  `Popen` 加 `start_new_session=True`（`:301` Claude / `:469` Codex）；两处超时路径
  （`:340-343` / `:503-506`）的 `proc.kill()` 换成杀整个进程组 + `communicate()` 加
  timeout 兜底（killpg 失败时不至于回到死锁）。
- file: `extraction/persona_extraction/core/rate_limit.py` → **H8**: `parse_reset_time`
  的 ISO 分支（`:181-192`）加未来性校验——解析结果不在未来则不采信该分支，落到后续
  锚定分支或返回 None（走默认 pause 时长），不让 `resume_at` 落在过去。
- file: `extraction/persona_extraction/prompts/character_snapshot_extraction.md` →
  **M1**: `:133` / `:150` / `:313` 三处的 `timeline_anchor` 改为"由程序在 merge 后注入，
  本次输出**不要写**"，与 `prompt_builder` 注入块一致。注意 `snapshot_summary` 归
  `char_internal` lane、**是**该写的，不要误伤。

## Validation criteria

- [ ] `python -m compileall -q extraction` 退出码 0
- [ ] import smoke：`extraction.persona_extraction.core.{llm_backend,rate_limit}` 无 error
- [ ] 8 个 smoke test 回归：7 个原本 PASS 的仍 PASS（`_smoke_triage` 仍允许 FAIL = M17）
- [ ] **M8 专项**：构造一个"派生了持有管道的孙进程"的子进程 → 触发超时 →
      断言 (a) 调用在有限时间内返回（不死锁）、(b) 孙进程确实被杀（`os.kill(pid, 0)` 抛
      ProcessLookupError）
- [ ] **H8 专项**：`parse_reset_time("2026-07-16T09:30:00Z ...", now=12:00)` 不再返回
      过去时刻；带真实 reset 语义的 stderr（`resets at 3pm` / `resets in 2h30m` /
      未来的 ISO）仍正确解析
- [ ] **H8 回归**：`RateLimitController` 的 flock / 原子写 / 预启动阻塞路径不受影响
      （`record_pause` → `wait_if_paused` 往返一次）
- [ ] **M1 专项**：`grep -c '必填' character_snapshot_extraction.md` 中 timeline_anchor
      相关行为 0；`snapshot_summary` 的"必填/已填写"要求**仍在**（未误伤）
- [ ] `_smoke_4_lane_merge_and_slice` 的 smoke 6 仍 PASS（`PROGRAM_INJECTED_FIELDS`
      与 schema 的关系未被动）

## Execution deviations

- **M1 落地形态与计划不同两次（计划的修法是错的，我的第一版修法也是错的）**：
  计划写「三处改为『由程序在 merge 后注入，本次输出**不要写**』」。实现时查出该 prompt
  被**两种模式**共用：`char_snapshot_sub_lanes=true` 走 4 sub-lane
  （`prompt_builder._render_lane_scope_block` 注入「程序注入字段（不要写）」块，
  `timeline_anchor` 在其中）；`=false` 时 `orchestrator.py:2935` 直接
  `build_char_snapshot_prompt`（`lane_scope="ALL"`），而 `_render_lane_scope_block` 对
  `"ALL"` **返回空块**（`prompt_builder.py:893-894`）、且该路径不经 `merge_partials`
  —— 即 **fallback 模式下 `timeline_anchor` 必须由 LLM 自己写**。照计划无条件改成
  「不要写」会把 fallback 模式修坏（产出缺 schema required 字段）。
  **第一版修法（已废弃）**：把三处 prompt 正文改成条件判据「以上方 §本次仅写以下字段
  为准」。Step 5 复审（分片 C）抓出该段名**在渲染产物里根本不存在** —— 实际渲染的是
  `## Sub-lane 字段范围（hard gate）`（`prompt_builder.py:916`），`本次仅写以下字段`
  只存在于 `:886` 的 docstring 里。LLM 按字面找不到该段 → 走 else → 必填 → 正是 M1
  要消灭的失败路径。改锚到「程序注入字段（不要写）」后自测又发现**判据不可判定**：
  任何被正文引用的字面串，正文自己就含有该串。
  **最终修法（更小更稳）**：正文**完全不动**（回退到原状），改为让**注入块自己声明
  优先级** —— `_render_lane_scope_block` 的「程序注入字段（不要写）」段追加一句
  「本清单优先于下文对这些字段的任何『必填 / 均已填写』表述——下文按单 lane 模式撰写，
  那时它们确实要你写；本次是 sub-lane 模式，写了就会触发 merge hard fail」。
  这样正文只陈述 ALL 模式的真相、无需任何模式判据，sub-lane 模式由注入块显式覆盖，
  零悬空锚点。净改动从「3 处 prompt 文案」变成「1 处代码字符串」。两种模式渲染均已实测。
  **代价**：改动落在 `prompt_builder.py`（计划里只列了 .md）。
- **H8 连带发现的文档/代码漂移（就地同步）**：`docs/requirements.md` §11.13.4 把 reset
  正则的优先级写成「1 绝对 → 2 相对 → 3 ISO」，而代码实际是 **ISO 优先**
  （`parse_reset_time` 的 `# 1. ISO 8601`）—— 顺序恰好相反。这与 H8 直接相关：若真按
  文档的顺序，带锚定词的分支会先赢，H8 much 难触发。本轮按**代码实情**同步文档
  （代码是运行真相），未改动匹配顺序（改顺序是超出计划的行为变更）。
- **新增决策条目 #63**（计划未明说要立条目）：M8 的「用 Ctrl+C 换不死锁」当时确有
  像样的备选（保守版只加 timeout、不动进程组），且未来读者很可能为恢复 Ctrl+C 而移除
  `start_new_session` 从而**静默重引入死锁** —— 符合 `ai_context/decisions.md` §格式 的
  准入判据（"没有这条 entry，一个不知情但有能力的人会做出不同选择吗？"→ 会）。
  H8 不立新条目，作为 #46 的就地收紧注（它是 bug 修复而非争议决策）。
- **`_terminate_process_tree` 抽成模块级 helper**：两个 backend 的超时路径同构，而
  killpg + 回退 + 异常处理的逻辑不平凡，复制两份比抽一个 10 行 helper 更糟。不属
  "extract abstraction" 式过度设计。
- **Step 5 自查加的自杀守卫（计划外，但属把 M8 做对的一部分）**：实测确认
  `killpg` 的安全性**完全依赖**与 `start_new_session=True` 配对——实测
  `start_new_session=True` → child pgid ≠ 自身 pgid（安全）；**不带该参数 → child pgid
  == orchestrator 自身 pgid**，此时 `killpg` 会把 orchestrator 自己一起 SIGKILL。
  初版 helper 只在 docstring 里假设配对、没有防：将来任何人加一个 `Popen` 忘了该参数
  又调用本 helper，就是 orchestrator 中途自杀（挂机场景下的最坏结局）。
  **修正**：helper 内比较 `os.getpgid(proc.pid)` 与 `os.getpgid(0)`，相同则**拒绝
  killpg**、降级为 child-only kill 并打 ERROR 点名"该 Popen 少了
  start_new_session=True"。实测三态：正常配对 → killpg 杀整树；误配对 →
  orchestrator 存活 + ERROR；子进程已消失 → `getpgid` 抛 OSError 被接住、不崩。
  另实测澄清：killpg 后子进程进入**僵尸态**（`/proc/<pid>/stat` = `Z`，已死待回收），
  紧随的 `communicate()` 回收后彻底消失——无进程泄漏。
- **Step 5 复审补齐 M8 的连带后果（分片 A 量化报告 + 主循环独立推演，就地修）**：
  `start_new_session` 让子进程不再收终端 SIGINT，而 lane 跑在**非 daemon** 的
  ThreadPoolExecutor 线程里、阻塞在 `communicate(timeout=extraction_timeout_s)`。
  信号 handler（`orchestrator.py:556-565`）的顺序是「存盘 → **释放 PID 锁** →
  `sys.exit(130)`」，SystemExit 展开时撞上 executor join → **停机要空转到子进程
  自然超时（最长 `extraction_timeout_s = 3600s`），而锁在这之前就被 unlink 了**。
  即 **PID 锁在说谎**：此间 `acquire()` 会成功，第二个 `--resume` 能并发写同一
  work tree / git 分支。该 race 改动前就存在（`kill <PID>` 是 README 记载的停机
  方式，SIGTERM 走同一 handler，子进程从来收不到），但窗口只有 ~1.6s；改动后
  Ctrl+C 也向它看齐，窗口放大到 3600s —— **正好命中本轮的挂机停机路径**。
  **修正**：`llm_backend` 加在飞子进程注册表（`_live_children` + 锁 +
  `_register_child` / `_unregister_child`，两个 backend 的 `Popen` 后注册、
  `finally` 注销）+ 导出 `terminate_all_children()`；`_handle_interrupt` 在
  **释放锁之前**调用它。实测（lane 子进程超时 scaled 到 25s 代表真实 3600s）：
  修复前停机等待 **23.52s**、修复后 **0.00s**，锁窗口回到 ~0。
  **代价**：改动扩到 `orchestrator.py`（计划里只列了 llm_backend / rate_limit /
  prompt）。判据：这是 M8 的直接连带后果、且命中"挂机会被静默咬到"的立项标准，
  属把 M8 做完整而非顺手扩张。
- **未越界**：本轮未顺手修任何其余留 todo 项（M3 / M4 / M6 / M7 / M9 / M10 / M17 /
  M18-M20 / 全部 Low）。M9（`{lane_scope}` 散文说"两个 sub-lane"实为 3）与 M1 同文件
  且就在隔壁，**刻意未改** —— 它不触发 MergeError，不在本轮"挂机会被静默咬到"的判据内。

<!-- POST phase fills in -->

## Landed changes

挂机长跑前置加固：修掉三条"故障静默、无人喊停"的缺陷 —— M8（子进程超时后
`communicate()` 永久阻塞 → lane 线程死锁 → 卡整夜不报错）、H8（限流 ISO 解析
无未来性校验 → `resume_at` 落在过去 → 零间隔热循环烧额度）、M1（`timeline_anchor`
指令冲突 → MergeError → 整个 char_snapshot lane 重跑）。M8 按用户选择走彻底版
（`start_new_session` + `killpg` 杀整棵进程树），并在复审中补齐其两个连带后果
（自杀守卫 + 停机时先杀子进程再放锁）。新增决策 #63。
文件级明细见本次 commit diff。

## Diff from plan

- **三条计划项全部落地**，但 M1 的落地形态与计划**完全不同**（计划的修法会把
  fallback 单 lane 模式修坏；详见 §Execution deviations）。
- **新增 4 项**（Step 5 自查 + 两个复审分片抓出，均就地修）：
  (1) `_terminate_process_tree` 的自杀守卫；(2) M1 第一版的悬空锚点 → 改为注入块
  自声明优先级、prompt 正文回退；(3) M8 的停机连带后果 —— 在飞子进程注册表 +
  handler 放锁前杀子进程；(4) #63 归档描述与代码对齐。
- **改动面比计划宽**：计划只列 `llm_backend.py` / `rate_limit.py` /
  `character_snapshot_extraction.md`；实际还动了 `prompt_builder.py`（M1 最终修法）
  与 `orchestrator.py`（M8 连带后果）。两处都属"把计划内的 finding 做完整"，
  非顺手扩张，逐条理由见 §Execution deviations。

## Validation results

- [x] `python -m compileall -q extraction` — 退出码 0
- [x] import smoke（`llm_backend` / `rate_limit` / `orchestrator` / `prompt_builder`）— 无 error
- [x] 8 个 smoke 回归 — 7 PASS；`_smoke_triage` 仍 FAIL（M17 已知，与本轮三条无关，
      状态与开工前一致）
- [x] **M8 专项** — A/B 实证：修复前 `communicate` 阻塞 >8s + 孙进程存活；
      修复后 0.00s 返回 + 孙进程被杀（`returncode=-9`）
- [x] **M8 自杀守卫三态** — 正常配对 → killpg 杀整树；误配对（无
      `start_new_session`）→ **orchestrator 存活** + ERROR 点名；子进程已消失 →
      `getpgid` 抛 OSError 被接住、不崩
- [x] **M8 停机专项** — scaled 实测（lane 子进程超时 25s 代表真实 3600s）：
      停机等待 **23.52s → 0.00s**，锁窗口回到 ~0
- [x] **M8 无进程泄漏** — killpg 后子进程 `/proc/<pid>/stat` = `Z`（僵尸），
      随后 `communicate()` 回收 → `gone`
- [x] **H8 专项** — 6 个用例：过去裸 ISO → 不采信走 fallback；过去 ISO + 可锚定
      信息（`Resets in 2h30m` / `Resets at 3PM`）→ **正确回落到那些分支**；
      未来 ISO / 纯相对量 → 照常解析；无信息 → None
- [x] **H8 端到端** — `record_pause` 往返：过去裸 ISO 的 `resume_at` 从
      **-9000s 量级 → +1800s**（fallback 默认），热循环不再可达
- [x] **H8 回归** — flock / 原子写 / 预启动阻塞路径未受影响；新 warning 仅在真撞
      限流时最多打一条（`parse_reset_time` 唯一调用点是 `record_pause`）
- [x] **M1 专项** — 两种模式渲染均实测自洽：sub-lane → 注入块含
      `timeline_anchor` 于「不要写」清单 + 显式声明优先于下文『必填』；
      ALL → 空块 + 正文「必填」生效。零悬空锚点；`snapshot_summary` 未误伤
- [x] 34 个 schema 元校验 — 全部合法
- [x] decisions 索引 ↔ 归档 lockstep — 双向零差集（#63 两边齐备、同节）
- [x] 真实名残留 grep（全仓，排除豁免集）— 0

## Completed

- **Status**: DONE
- **Finished**: 2026-07-16 11:51:59 EDT
