# 2026-04-23 01:50 · E1 落地后文档漂移修正

## 背景

commit `eafe682`（feat: repair per-file parallel dispatch E1）把 repair
改为 per-file 并发，但有两处文档描述没跟上新语义——`/after-check`
sweep 抓出：

1. **H1** · `automation/repair_agent/recorder.py` 的模块 + 类 docstring
   仍然说"one file per stage" / "single stage's repair run"，与 E1 的
   per-file 一份 JSONL 矛盾
2. **M1** · `automation/README.md:66` 配置段 `[repair_agent]` 描述未
   提及 `repair_concurrency`，与 `docs/requirements.md §11.12` 已更新的
   描述不一致

两处都是 6b9341f 引入 RepairRecorder、eafe682 改命名语义之间的纯文档
漂移，无代码逻辑影响。

## 改动

### `automation/repair_agent/recorder.py`

- **模块 docstring**：路径范式从 `repair_{stage_id}.jsonl` 改为
  `repair_{stage_id}_{slug(file)}.jsonl`；新增一段说明 orchestrator
  并发调度、每 worker 独立 recorder 因此无锁
- **类 docstring**：`single stage's repair` → `single file's repair`；
  补一句"parallel per-file workers each hold their own recorder, so
  writes are lock-free by construction"

### `automation/README.md`

- 配置段 `[repair_agent]` 条目从"各 tier 重试次数、triage 设置"改为
  "各 tier 重试次数、T3 全局上限、triage 接受上限、总轮数、per-file
  并发度（`repair_concurrency`，默认 10）"——与
  `docs/requirements.md:2349` 对齐

## 不改的

- 代码逻辑：零触及
- `docs/requirements.md` / `docs/architecture/` / `ai_context/`：上个
  commit 已对齐，无改动
- after-check 的 L1（`except Exception` 不含 `BaseException`）—— Python
  惯例建议不改
- after-check 的 L2（配置表描述位置）—— 风格问题，不改

## 验证

```python
python3 -c "
from automation.repair_agent.recorder import RepairRecorder
import automation.repair_agent.recorder as rec_mod
assert 'one file per repaired target' in rec_mod.__doc__.lower()
assert \"single file's repair\" in RepairRecorder.__doc__.lower()
print(rec_mod.__doc__.splitlines()[0])
print(RepairRecorder.__doc__.splitlines()[0])
"
```

通过。
