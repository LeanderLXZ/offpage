# TODO List Archived（归档清单）

---

## 文件说明

### 用途

接收从 `docs/todo_list.md` 移走的两类任务条目：

- **已完成**：包括完整完成、部分完成、改方案后完成
- **废弃**：包括方案被颠覆、外部前提消失、合并到其他任务等

`docs/todo_list.md` 是**正在做和将来做**的事，本文件是**已经做完和决定不做**的事。两者互不重叠，原 todo 条目移过来后从源文件删除。

### 为什么要瘦身存档

不是为了保留完整改动记录——那个职责由 `git log` + `logs/change_logs/{timestamp}_{slug}.md` 共同承担。本文件仅作 **快速浏览索引**：

- 看 ID / 标题 → 知道有这件事
- 看完成形式 → 知道走到哪一步收尾的
- 看 1 行摘要 → 知道大概改了什么
- 看 log 链接 → 想了解细节就跳过去

**绝不在本文件保留改动清单原文 / 验证步骤 / 待决策项 / 长篇上下文**——这些在原 todo 段落里有，原 todo 一并被瘦身。需要追溯历史时去 git history 看 todo_list.md 删除前的版本，或去 change_logs 看落地详情。

### 条目格式

#### 已完成段

```markdown
### [T-XXX] 中文标题 · 完成于 YYYY-MM-DD · {完整 / 部分 / 改方案后} 完成

- 1 行摘要：实际改了什么 / 走到哪一步
- 关联 log: [logs/change_logs/YYYY-MM-DD_HHMMSS_slug.md](../logs/change_logs/YYYY-MM-DD_HHMMSS_slug.md)
- 关联 commit:（可选）`<short-sha>`
```

完成形式三档：

- **完整完成**：按原 todo 的完成标准全部达成
- **部分完成**：核心达成、留下次要尾巴；尾巴**必须作为新 todo 条目**重新登记到 `todo_list.md`，本归档行的摘要里标"尾巴去 T-YYY"
- **改方案后完成**：方案与原 todo 不同（更优 / 受新约束影响 / 实测后调整），但目的达成；摘要里 1 句话说清"原方案 vs 实际方案"

#### 废弃段

```markdown
### [T-YYY] 中文标题 · 废弃于 YYYY-MM-DD

- 废弃原因：1–2 句话
- 关联 log: [logs/change_logs/YYYY-MM-DD_HHMMSS_slug.md](../logs/change_logs/YYYY-MM-DD_HHMMSS_slug.md)
```

### 排序

每段内部按"完成 / 废弃日期"**降序**（新的在上）。同一天有多条按 ID 字母序。

### 不记录什么

✗ 仍在进行的任务 → `docs/todo_list.md`
✗ 历史 design 决策 → `ai_context/decisions.md`
✗ 落地细节 / diff / 验证日志 → `logs/change_logs/`
✗ 改动清单原文 → 不要从源 todo 拷过来
✗ 完整 PRE / POST log 内容 → 引一个链接就够了

### 读取时机

- 用户问"X 这件事我们之前做过 / 讨论过吗？" → 先在本文件 grep ID / 关键词
- 用户问"为什么不做 Y？" → 在"废弃"段查 → 引到对应 change_log
- 默认不主动加载（不进入 session 启动序列）

---

## 已完成

### [T-CHAR-SNAPSHOT-13-DIM-VERIFY] 角色 stage_snapshot "13 必填维度" 表述核对 · 完成于 2026-04-27 · 改方案后完成

- 1 行摘要：原方案候选"字面 17 条" vs 实际方案"指针式"；`docs/architecture/extraction_workflow.md:277` 与 `docs/requirements.md:2139` 改为"以 `schemas/character/stage_snapshot.schema.json` 的 `required` 列表为准"，去掉具体数字与字段示例，避免下次 schema 增减字段时再次漂移。
- 关联 log: [logs/change_logs/2026-04-27_185531_char-snapshot-required-fields-pointer.md](../logs/change_logs/2026-04-27_185531_char-snapshot-required-fields-pointer.md)

---

## 废弃

_（暂无条目。第一个废弃的任务从 `todo_list.md` 移过来时按上方"废弃段"格式追加到本节顶部。）_
