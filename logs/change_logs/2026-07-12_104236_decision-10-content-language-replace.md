# decision-10-content-language-replace

- **Started**: 2026-07-12 10:42:36 EDT
- **Branch**: main
- **Type**: DO
- **Status**: DONE

## Motivation

决策 #10 原文「`ai_context/` 保持英文」与本日 /holo:init 设定的
`content_language=zh`（skills_config §Language，ai_context/docs 已全量中文化）
相悖。/compress-ai-context 收尾报告将其列为待决事项，用户经 /do 拍板
就地替换（决策变了、主题仍相关，编号不变，index + archive 两侧同步）。

## Change list

- file: ai_context/decisions.md:115 → 索引 #10 陈述改为「书面语言跟随
  skills_config §Language 的 content_language（当前 zh）；代码标识符与
  JSON 字段名保持英文」
- file: docs/decisions.md:69-70 → 归档 #10 同步改写，附半行痕迹
  （曾为 English-only，随语言轴引入就地替换），指针补
  `skills_config §Language`
- file: ai_context/conventions.md:217 → §Naming and Identifiers 对应
  bullet（#10 指针目标）同步改写

## Verification summary

- grep 旧声明「`ai_context/` 保持英文」全仓（除 logs/）残留 = 0
- decisions_fat_format 探针 = []（#10 两侧仍为 index 形态、编号锁步不变）
- 其余「保持英文」命中均指代码标识符 / 字段名，语义仍成立，未触碰

## Execution deviations

- none
