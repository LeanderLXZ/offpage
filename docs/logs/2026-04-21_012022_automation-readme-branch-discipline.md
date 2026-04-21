# F6 收口：automation/README.md 补齐分支纪律段

## 动机

`/after-check` F6：`automation/README.md` 的 git 相关内容只有两处一笔带过
（"分支正确"、"auto squash-merge 开关"），没提本次新装的 try/finally +
`checkout_master` dirty guard + SessionStart hook。module 级 README 是
读 automation 模块的人第一眼看的文件，约束机制不可见等于不存在。

## 改动

- `automation/README.md`：
  - stage 流程 step 1 的 "分支正确" 具体化为 "分支 = `extraction/{work_id}`"。
  - 新增 `## 分支纪律` 节，放在 `## 进程保护` 之后、`## 目录结构` 之前。
    内容点到 "进入 / 退出 / Dirty guard / 异常检测 / squash-merge" 五条
    机制，指向 `ai_context/architecture.md §Git Branch Model` 作为权威源。

## 验证

- `grep -n "分支纪律\|checkout_master\|SessionStart"
  automation/README.md` 命中。
- README 结构未破坏（目录结构、进度文件、Phase 3.5、Phase 4 等节仍按原
  顺序）。

## 影响范围

- 纯文档。无代码、无数据、无兼容性影响。
