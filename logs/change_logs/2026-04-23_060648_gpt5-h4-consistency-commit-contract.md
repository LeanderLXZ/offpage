# 2026-04-23 06:06 — gpt-5 audit H4：Phase 3.5 产物 commit 契约 + 只读加载

## 背景

gpt-5 H4：Phase 3.5 `_run_consistency_check` 写出
`consistency_report.json` 后直接进入 `_offer_squash_merge`，没有 commit。
两条坏路径：
1. 用户拒绝 squash → `checkout_master` 在 work scope 下发现未提交脏，
   被迫失败
2. 用户接受 squash → 未提交的 report 不进 squash commit，违反
   `current_status.md` "consistency_report 是 tracked" 的声明

另外，一致性检查器 `_load_json` / `_load_jsonl` 通过
`try_repair_json_file` / `try_repair_jsonl_file` 会在加载时顺带 L1
修复并**写回磁盘**——这个隐式写盘进一步放大了 H4 的 dirty 风险。

## 改动

### `_load_json` / `_load_jsonl` 改只读（`automation/persona_extraction/consistency_checker.py`）

- 去掉 `try_repair_json_file` / `try_repair_jsonl_file` 的调用和 import
- 解析失败时 log warning + 返回 None / []，与原有的 JSONDecodeError
  分支行为一致
- 原始文件的完整性由 repair_agent 保证（Phase 3 出口条件就是"全部
  repair 通过 + 重跑 PP"，Phase 3.5 不该越权修改 committed 产物）

### `_commit_consistency_report` 新辅助（`automation/persona_extraction/orchestrator.py`）

- `save_report` 之后立刻调用，复用 `commit_stage(stage_id="phase3.5",
  files=[rel], message=...)`
- commit message 例：`phase3.5: consistency_report S001..S049\n\n...`
- commit 失败不抛异常——仅 log warning，不阻断 Phase 3.5 流程（commit
  失败最可能是工作区无 diff，属于 no-op）
- 调用时机：**pass/fail 两条路径都 commit**。fail 路径下用户不会
  squash，但 dirty 报告仍需被固化，`checkout_master` 才能清场；pass
  路径下 squash-merge 会打包本次 commit

## 跨文件对齐

- `docs/requirements.md` §11.10 新增"Phase 3.5 产物提交契约"小节，说明
  提交时机 + 读入端只读约束
- `ai_context/architecture.md` Phase 3.5 段追加 read-only + commit
  contract 描述
- `docs/architecture/extraction_workflow.md` §7 末尾追加"提交契约"段

## 验证

- `python -c 'from automation.persona_extraction import consistency_checker, orchestrator'` 通过
- `ExtractionOrchestrator._commit_consistency_report` 存在
- 源码层面确认 `_load_json` / `_load_jsonl` 不再引用 `try_repair_json_file`
  / `try_repair_jsonl_file`，import 已删除
- 实际 Phase 3.5 运行依赖全部 stage COMMITTED，端到端回归由用户下次
  扩展完成 49 stage 时自然覆盖

## 未做 / 推迟

- `json_repair.py` 的 `try_repair_json_file` / `try_repair_jsonl_file`
  本身不动——Phase 0 / Phase 2.5 等场景仍有合法调用方
- Phase 4 `scene_archive.py` 是否也有只读约束漏洞不在本次范围

## 受影响文件清单

```
ai_context/architecture.md
automation/persona_extraction/consistency_checker.py
automation/persona_extraction/orchestrator.py
docs/architecture/extraction_workflow.md
docs/requirements.md
```
