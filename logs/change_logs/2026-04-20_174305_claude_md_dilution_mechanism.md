# Dilution 机制从 ai_context/ 迁入 CLAUDE.md / AGENTS.md

## 动机

原先 `ai_context/instructions.md` 的 §"Dilution Protection" 节本身是长会话
漂移防护机制，但它自己就是 `ai_context/` 被加载一次后最可能被稀释/压缩的那段
文字——**防漂移的规则自己先漂了**。

把它搬到 `CLAUDE.md` / `AGENTS.md`：

- 这两个文件由 Claude Code session-start hook 常驻注入，接近于"永远在
  context 里"的地位
- 重构成三条可执行的自检问题，强迫 AI 在每次改动前主动自问，而非被动希望
  触发式规则能被记起
- 顺带解决一个历史隐患：extraction 的 `claude -p` 跑在 `cwd=project_root`
  下，其实一直在加载 CLAUDE.md——以前那里面那句 "session start 读
  ai_context/" 对 extraction worker 是浪费或噪声；本次用 worker-mode
  短路条件一并修掉

## 改动清单

### CLAUDE.md / AGENTS.md（镜像同步，硬规则）

顶部新增 §**Worker-Mode Short-Circuit**：
- 若 system prompt 含 `[extraction_worker_mode]` 或 `[simulation_runtime_mode]`
  → 停止读本文件、不加载 `ai_context/`、不自检、完全按 user prompt 执行

底部新增 §**Dilution Self-Check**（三条）：
1. **Scope check** — 是否在做用户要求之外的 proactive 改动
2. **Right layer** — 编辑的文件是否在对的模块；不确定 → 重读
   `ai_context/architecture.md`
3. **Alignment check** — 改动收尾前是否查过 `ai_context/conventions.md`
   的 Cross-File Alignment 表

触发时机：编辑 code / schema / prompt / docs 之前、任务类型切换之后。

### ai_context/ 精简（已搬走的段不再在这里重复）

- [ai_context/instructions.md](../../ai_context/instructions.md) — 删除整节
  §"Dilution Protection"；Reading Order 后加一行指针说明自检在 CLAUDE.md
- [ai_context/conventions.md](../../ai_context/conventions.md) — 标题从
  "Operational Conventions — RE-READ WHEN IN DOUBT" 改回
  "Operational Conventions"；删除顶部 "Re-read this file before writing..."
  两行，加一行指针
- [ai_context/README.md](../../ai_context/README.md) — "dilution-protection
  checkpoints" 措辞简化为指针

### 代码（extraction worker 注入 marker）

- [automation/persona_extraction/llm_backend.py](../../automation/persona_extraction/llm_backend.py) —
  `ClaudeBackend.run` 拼 cmd 追加一行
  `"--append-system-prompt", "[extraction_worker_mode]"`

### TODO

- [docs/todo_list.md](../todo_list.md) §讨论中 新增 `T-SIMULATION-MODE-MARKER`：
  simulation runtime 首次实装 LLM 调用时，同样注入
  `[simulation_runtime_mode]`。marker 在 CLAUDE.md 已预留，simulation 侧目前
  零 Python 代码，无注入点

## 验证

```bash
# 1. Python 模块可 import
python3 -c "
from automation.persona_extraction import llm_backend
from automation.persona_extraction.llm_backend import ClaudeBackend
print('import OK')
"

# 2. CLAUDE.md 与 AGENTS.md 仅标题差异
diff CLAUDE.md AGENTS.md
# 预期：仅 line 1、65、67、68 差异（Claude/Agent 字样）

# 3. ai_context/ 无残留旧文案
rg -n 'Dilution Protection|dilution-protection|RE-READ WHEN IN DOUBT|Re-read this file before' ai_context/ docs/ \
  -g '!docs/logs/**' -g '!docs/review_reports/**'
# 预期：无输出

# 4. marker 字符串已注入且只出现在预期位置
rg -l 'extraction_worker_mode|simulation_runtime_mode' -g '!docs/logs/**'
# 预期：CLAUDE.md / AGENTS.md / automation/persona_extraction/llm_backend.py /
#       docs/todo_list.md
```

全部通过。

## 注意事项

- CLAUDE.md 的 Worker-Mode 短路依赖 system prompt 中有字符串 marker；
  这是 Claude Code CLI `--append-system-prompt` 的确定性行为，不依赖 LLM
  启发式自判
- `[simulation_runtime_mode]` 在代码层暂无注入点，但 CLAUDE.md 侧已对齐。
  只有一份 TODO 在追踪，不是悬挂 bug——运行时的 CLAUDE.md 看到该 marker
  时也能正常短路（因为短路逻辑是"含任一 marker 即跳过"）
- 之前 extraction worker 其实一直在被 CLAUDE.md 指示"读 ai_context/"——
  没出事是因为 extraction prompt 足够强势；现在是显式断掉这条路径，不是
  引入新的 worker 行为
