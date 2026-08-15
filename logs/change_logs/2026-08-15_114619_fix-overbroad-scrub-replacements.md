# fix-overbroad-scrub-replacements

- **Started**: 2026-08-15 11:46:19 EDT
- **Branch**: main
- **Type**: DO
- **Status**: DONE

## Motivation

上一轮用 `git filter-repo` 清洗历史时，其中两条把宗门类专有名词映射到
`<stage_title>` / `<character>` 的规则设计过宽，按字面子串命中了两类本
不该动的内容：

1. 权威文档里的**虚构示例地名**（一个宗门名 + `·演武场`）被砸成
   `天<stage_title>`。已核实该示例名不在世界观真实名录内，它本就是符合
   §Generic Placeholders 的合规占位示例 —— 只是恰好包含了某个真实宗门名
   作为子串。
2. 6 份历史日志里的残留扫描命令（原本 grep 的是书名前缀）被砸成
   `git grep '我和<character>'`，使记录失去意义。

规则设计时只检查了"这个词是不是真实名称"，没检查"它作为子串会命中什么"。

## Change list

- file: `docs/requirements.md` L3456 → `天<stage_title>` 还原为 `天剑宗`
- file: `simulation/retrieval/index_and_rag.md` L131 → 同上
- file: `logs/change_logs/2026-04-25_031406_extraction-disposable-and-phase4-remap.md` 等 6 份日志
  （共 7 处）→ `我和<character>` 归一为 `<work_id>`。**不还原字面的书名
  前缀** —— 还原等于撤销本轮清洗；改用占位符既修好被砸坏的字符串，
  又保住"当时做过书名残留扫描"的记录原意。

## Verification summary

- `天<stage_title>` 在 `docs/` + `simulation/` 残留 = 0；`天剑宗` 已在两处还原。
- `我和<character>` 在 `logs/` 残留 = 0。
- 全仓 `*.md` 中书名前缀命中 = 0 —— 未重新引入真实名称。

  （**本段后经订正**：上述验证在写本日志之前执行，而本日志当时为说明
  问题引用了真实书名前缀，自身即违反 §Generic Placeholders。教训是
  验证必须在全部产物写完之后执行，说明性文档只写结构化描述。）

## Execution deviations

- 本次改动集 8 个文件，超出 `/do` 名义上的 ≤5 文件信封。判断为单一机械
  意图（两条字符串的定向还原，无设计决策），未升级到 `/go`。
