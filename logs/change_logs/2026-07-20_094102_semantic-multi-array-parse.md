# semantic-multi-array-parse

- **Started**: 2026-07-20 09:41:02 EDT
- **Branch**: main
- **Type**: DO
- **Status**: DONE

## Motivation

`T-SEMANTIC-UNPARSEABLE` 的根因诊断结果。台账
（`works/<work_id>/analysis/deferred_repairs/{S001,S003}.jsonl`）里各有一条
`semantic_unparseable`，报错为 `Extra data: line 1 column 4 (char 3)` 与
`column 5 (char 4)`。逐字复现确认：模型最终消息里有**两个顶层 JSON 数组**、
同行空格分隔（`[] [{...}]` / `[]  [{...}]`），而 `_parse_response` 用
first-`[` 到 last-`]` 切片，把两个数组连同中间空格切成一个非法串。

即故障不在模型输出破损，而在解析器对"多个顶层值"无防御。这不是随机故障，
重试无意义；同时**不能改成只取第一个数组** —— 实测第一个是空数组，取它等于
在有真实 error 的文件上报干净通过，正是本 checker 存在意义所要防的假 PASS。

## Change list

- file: `extraction/repair/checkers/semantic.py` → 新增模块级
  `_decode_top_level_arrays()`：从首个 `[` 起用 `json.JSONDecoder().raw_decode`
  逐个解码顶层值并收集其中的数组，数组间的杂质靠寻找下一个 `[` 跳过；仅当
  一个数组都没解出来时才抛 `JSONDecodeError`（已解出至少一个时，尾部残留视为
  模型补话，保留旧切片对 markdown 围栏 / 收尾散文的容忍度）。
- file: `extraction/repair/checkers/semantic.py::_parse_response` → 改用该
  helper 替换 `find`/`rfind` 切片；解出 >1 个数组时打 warning（解析成功后不再
  产生 issue 记录，无此日志则模型的异常输出习惯会完全隐形）；`JSONDecodeError`
  分支的 message 补上响应前 80 字符（与相邻"找不到数组"分支对齐 —— 本次定位
  根因正是因为缺这段而只能靠偏移量反推）。
- file: `extraction/repair/tests/_smoke_l3_gate.py` → 新增 Scenario H
  `_scenario_h_multi_array_response()`，覆盖两个生产实测形状 + markdown 围栏，
  断言真实 finding 存活；接入 `main()`。

## Verification summary

- `python -m extraction.repair.tests` 全通过 —— `all 2 smoke module(s) passed`，
  含新增 Scenario H 与既有 A–G（scope 过滤 / backend-failure 穿透 / 未 gate
  文件携带未修 issue 等语义均未受影响）。
- 直接对 `_parse_response` 跑 8 组 payload：两个生产实测形状 → 真实 finding
  存活；markdown 围栏 / 前置散文 / 后置散文（含方括号）→ 正常解析；真·空数组
  → `[]`；真·截断与真·非 JSON 响应 → 仍产出 `semantic_unparseable`（硬故障
  未被降级为假 PASS）。

## Execution deviations

- 已知的良性副作用：响应尾部散文若含方括号（如 `see [1].`），会被当作第二个
  顶层数组解出并触发 merge warning。其元素非 dict，被 `_parse_response` 既有的
  `isinstance(item, dict)` 过滤丢弃，结果正确，仅日志略噪。为此加判别逻辑属
  收益为零的复杂度，不做。
- 未做 todo 收尾：`T-SEMANTIC-UNPARSEABLE` 的 4 个待决项中 1/2/3 已由本次改动
  与前序讨论得出结论，剩余第 4 项（defer 桶按 rule 分流）归属
  `T-PHASE35-DEFERRED-FIX` 的设计范围。条目合并与归档属 todo 维护，不在 `/do`
  职责内（见 skill Constraints）。
