# Repair Agent 审计修复

**日期**：2026-04-17
**范围**：四轮并行审计发现的 bug + 旧术语残留，全部修复

## 审计范围

| 审计维度 | 发现数 |
|---------|--------|
| 文档对齐（旧术语） | 6 处 |
| 代码残留注释 | 2 处 |
| repair_agent bugs | 2 CRITICAL + 4 HIGH + 4 MEDIUM + 1 MINOR |
| 集成测试 | 33/33 通过 + 1 confirmed bug |

## Bug 修复

### CRITICAL

1. **`tracker.py` `is_regression()`** — `>=` → `>`。  
   旧条件 `introduced >= resolved` 把 introduced=1 resolved=1
   （语法修复暴露 schema 问题）误判为回归并中止修复循环。

2. **`coordinator.py` `_run_fixer_with_escalation()`** — 修复记录顺序。  
   旧代码先记录 attempts 再 remove resolved，导致已修复的 issue
   也被记为 "persisting"。改为：fix → remove resolved → record。

### HIGH

3. **Phase B recheck** — `pipeline.run()` → `pipeline.run_scoped()`。  
   修复循环内不应触发 L3 语义检查。

4. **`run_scoped()` 设计** — 经审查属于 by-design（全文件重检正确），
   改进 docstring 说明。

5. **`_fix_missing_required()`** — 构造了 `new_path` 但第 228 行用的是
   `parent_path + "." + field_name`，改为使用 `new_path`。

6. **T2 `source_patch`** — `source_context=None` 时静默返回空，
   添加 warning 日志。

### MEDIUM

7. **`SchemaChecker`** — `path_parts` 为空时 json_path 产生尾部点号，
   加括号修正优先级。

8. **`JsonSyntaxChecker`** — JSONL 文件解析后不缓存到 `f.content`，
   导致后续 checker 拿到 None。现在缓存为 list。

9. **`context_retriever`** — docstring "Attempt 1/2/3" 与 0-indexed
   代码不符，改为 `attempt_num 0/1/≥2`。

### MINOR

10. **`file_regen.py`** — `write_patched_file` 从方法内部 inline import
    移到顶部。

## 术语清理

| 文件 | 变更 |
|------|------|
| `ai_context/current_status.md` | 移除 "inter-lane dependency"、"commit gate"、"parallel review lanes" |
| `ai_context/requirements.md` | "parallel review lanes, commit gate" → "repair agent" |
| `ai_context/architecture.md` | "inter-lane dependency" → "inter-process dependency" |
| `ai_context/decisions.md` | 重写 §25（旧三层质检 → repair_agent 四层×四级）；"world review lane" → "repair agent"；"char_support lane" → "char_support process" |
| `progress.py` | 两处旧 docstring（review-lane / targeted fix）更新为 repair_agent |

## 测试

- 修复后全部 20 项单元测试通过
- E2E 回归场景（trailing comma → schema violation）验证通过
