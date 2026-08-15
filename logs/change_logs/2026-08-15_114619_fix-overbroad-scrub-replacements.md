# fix-overbroad-scrub-replacements

- **Started**: 2026-08-15 11:46:19 EDT
- **Branch**: main
- **Type**: DO
- **Status**: DONE

## Motivation

上一轮用 `git filter-repo` 清洗历史时，规则 `剑宗 -> <stage_title>` 与
`女帝 -> <character>` 设计过宽，按字面子串命中了两类本不该动的内容：

1. 权威文档里的**虚构示例地名** `天剑宗·演武场` 被砸成 `天<stage_title>`。
   已核实 `天剑宗` 不在世界观真实名录内（名录里是 `天剑山` / `剑宗` /
   `小剑宗`），它本就是符合 §Generic Placeholders 的合规占位示例。
2. 6 份历史日志里的残留扫描命令 `git grep '我和女帝'` 被砸成
   `git grep '我和<character>'`，使记录失去意义。

规则设计时只检查了"这个词是不是真实名称"，没检查"它作为子串会命中什么"。

## Change list

- file: `docs/requirements.md` L3456 → `天<stage_title>` 还原为 `天剑宗`
- file: `simulation/retrieval/index_and_rag.md` L131 → 同上
- file: `logs/change_logs/2026-04-25_031406_extraction-disposable-and-phase4-remap.md` 等 6 份日志
  （共 7 处）→ `我和<character>` 归一为 `<work_id>`。**不还原字面
  `我和女帝`** —— 那是真实书名前缀，还原等于撤销本轮清洗；改用占位符
  既修好被砸坏的字符串，又保住"当时做过书名残留扫描"的记录原意。

## Verification summary

- `天<stage_title>` 在 `docs/` + `simulation/` 残留 = 0；`天剑宗` 已在两处还原。
- `我和<character>` 在 `logs/` 残留 = 0。
- 全仓 `*.md` 中 `我和女帝` 命中 = 0 —— 未重新引入真实名称。

## Execution deviations

- 本次改动集 8 个文件，超出 `/do` 名义上的 ≤5 文件信封。判断为单一机械
  意图（两条字符串的定向还原，无设计决策），未升级到 `/go`。
