# Git 分支使用规范

## 变更内容

在 `ai_context/conventions.md` 的 Git 部分新增分支使用规则：

1. 默认分支是 `master`，非提取时必须在 `master` 上
2. 所有代码改动（code、schemas、prompts、docs、ai_context）先提交到 `master`，再 merge 到提取分支
3. 提取分支只放提取数据（stage 产出），提取暂停后立即切回 `master`

## 修改文件

- `ai_context/conventions.md`

## 原因

之前出现过代码改动直接提交在 extraction 分支上、master 落后的情况，导致分支间代码不同步。明确规范后避免此类问题。
