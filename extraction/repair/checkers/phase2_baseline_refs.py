"""L2 — Phase 2 baseline 引用合法性 checkers（决策 #59）。

Phase 2 lane fan-out 的产物级程序 checker（纯集合运算，零 LLM）。三个
checker 都是**构造函数注入 hint**（合法 id 集 / 期望 character_id /
lane A 前置状态）——不走 ``_repair_hints`` 内容注入，避免 hint 被
fixer 写回落盘文件。由 orchestrator 在 phase 2 per-lane repair 调用时
经 ``coordinator.run(extra_checkers=...)`` 注册；phase 3 的 repair
pipeline 不含这些 checker（path 过滤 + 构造注入双重保证互不干扰）。

fixed_relationships ↔ target_baseline **无跨产物一致性约束**（模板
明确两者合法分叉），所以这里没有 merge 点 cross-artifact checker——
每个 checker 只对照 candidate_characters 这组不可变共享输入。
"""

from __future__ import annotations

from pathlib import Path

from . import BaseChecker
from ..protocol import FileEntry, Issue


def _posix(path: str) -> str:
    return path.replace("\\", "/")


class FoundationKeyFiguresChecker(BaseChecker):
    """Layer 2: lane A 替换结果核验 —— 对照 pre-lane 状态与合法 id 集。

    规则（对应 baseline_key_figures prompt 的替换契约）：
    - ``foundation_factions_stable``：势力集合（按 name）不得新增 / 删除
    - ``key_figures_provenance``：替换后每个条目必须 ∈ 合法 character_id
      全集 ∪ 该势力 pre-lane 的 raw 名集（"不新增"——防幻觉名 / 幻觉 id）
    - ``key_figures_duplicate``：同一势力内不得有重复条目（替换后去重契约）

    "匹配不上保留 raw 名"是合法终态，所以 provenance 只拦"凭空出现的
    字符串"，不拦 raw 名残留。
    """

    layer = 2

    def __init__(self, legal_ids: set[str],
                 pre_key_figures: dict[str, list[str]]):
        self._legal_ids = set(legal_ids)
        self._pre = {name: set(vals) for name, vals in pre_key_figures.items()}

    def check(self, files: list[FileEntry], **kwargs) -> list[Issue]:
        issues: list[Issue] = []
        for f in files:
            if not _posix(f.path).endswith("world/foundation/foundation.json"):
                continue
            content = f.content if f.content is not None else f.load()
            if not isinstance(content, dict):
                continue
            factions = content.get("major_factions")
            if not isinstance(factions, list):
                continue

            post_names = [fac.get("name", "") for fac in factions
                          if isinstance(fac, dict)]
            pre_names = set(self._pre.keys())
            added = sorted(set(post_names) - pre_names)
            removed = sorted(pre_names - set(post_names))
            if added or removed:
                issues.append(Issue(
                    file=f.path, json_path="$.major_factions",
                    category="structural", severity="error",
                    rule="foundation_factions_stable",
                    message=(
                        f"势力集合被改动（lane A 只允许改 key_figures）："
                        f"新增 {added or '无'}，删除 {removed or '无'}。"),
                    context={"added": added, "removed": removed},
                ))

            for idx, fac in enumerate(factions):
                if not isinstance(fac, dict):
                    continue
                name = fac.get("name", "")
                entries = fac.get("key_figures")
                if not isinstance(entries, list):
                    continue
                pre_raw = self._pre.get(name, set())
                seen: set[str] = set()
                for e_idx, entry in enumerate(entries):
                    if not isinstance(entry, str):
                        continue
                    # json_path carries the entry index so two bad
                    # entries in one faction get distinct fingerprints
                    # (fingerprint = file::json_path::rule).
                    entry_path = (f"$.major_factions[{idx}]"
                                  f".key_figures[{e_idx}]")
                    if entry in seen:
                        issues.append(Issue(
                            file=f.path,
                            json_path=entry_path,
                            category="structural", severity="error",
                            rule="key_figures_duplicate",
                            message=(f"势力「{name}」key_figures 内重复条目"
                                     f"「{entry}」（替换后应去重）。"),
                            context={"faction": name, "entry": entry},
                        ))
                    seen.add(entry)
                    if entry not in self._legal_ids and entry not in pre_raw:
                        issues.append(Issue(
                            file=f.path,
                            json_path=entry_path,
                            category="structural", severity="error",
                            rule="key_figures_provenance",
                            message=(
                                f"势力「{name}」key_figures 条目「{entry}」"
                                f"既不是合法 character_id，也不是该势力"
                                f"替换前已有的 raw 名（不新增契约）。"),
                            context={
                                "faction": name, "entry": entry,
                                "pre_raw": sorted(pre_raw),
                            },
                        ))
        return issues


class FixedRelationshipsPartiesChecker(BaseChecker):
    """Layer 2: fixed_relationships 引用核验。

    - ``relationship_id_duplicate``（error）：relationship_id 重复
    - ``fixed_relationships_party_unmatched``（**warning**）：parties[]
      条目 ∉ 合法 character_id 集。schema 契约允许 raw 角色名（对方可能
      不在 candidate 集内），所以不能 hard error——warning 提示 runtime
      绑定能力受限，供人工复核。
    """

    layer = 2

    def __init__(self, legal_ids: set[str]):
        self._legal_ids = set(legal_ids)

    def check(self, files: list[FileEntry], **kwargs) -> list[Issue]:
        issues: list[Issue] = []
        for f in files:
            if not _posix(f.path).endswith("fixed_relationships.json"):
                continue
            content = f.content if f.content is not None else f.load()
            if not isinstance(content, dict):
                continue
            rels = content.get("relationships")
            if not isinstance(rels, list):
                continue
            seen_ids: set[str] = set()
            for idx, rel in enumerate(rels):
                if not isinstance(rel, dict):
                    continue
                rid = rel.get("relationship_id", "")
                if rid in seen_ids:
                    issues.append(Issue(
                        file=f.path,
                        json_path=f"$.relationships[{idx}].relationship_id",
                        category="structural", severity="error",
                        rule="relationship_id_duplicate",
                        message=f"relationship_id「{rid}」重复。",
                        context={"relationship_id": rid},
                    ))
                if isinstance(rid, str) and rid:
                    seen_ids.add(rid)
                parties = rel.get("parties")
                if not isinstance(parties, list):
                    continue
                unmatched = [p for p in parties
                             if isinstance(p, str)
                             and p not in self._legal_ids]
                if unmatched:
                    issues.append(Issue(
                        file=f.path,
                        json_path=f"$.relationships[{idx}].parties",
                        category="structural", severity="warning",
                        rule="fixed_relationships_party_unmatched",
                        message=(
                            f"parties 含非 candidate character_id 条目 "
                            f"{unmatched}（schema 允许 raw 名，但 runtime "
                            f"无法绑定角色包；确属固定关系可保留）。"),
                        context={"unmatched": unmatched},
                    ))
        return issues


class TargetBaselineKeysChecker(BaseChecker):
    """Layer 2: target_baseline 引用核验。

    - ``target_baseline_character_id_mismatch``（error）：character_id
      与目录 / 期望角色不一致
    - ``target_id_not_candidate``（error）：targets[].target_character_id
      ∉ 合法 character_id 集（prompt 硬契约：统一用 identity ID）
    - ``target_id_duplicate``（error）：target_character_id 重复
    - ``target_self_reference``（error）：target 指向 baseline 主角自身
    """

    layer = 2

    def __init__(self, legal_ids: set[str], expected_character_id: str):
        self._legal_ids = set(legal_ids)
        self._expected = expected_character_id

    def check(self, files: list[FileEntry], **kwargs) -> list[Issue]:
        issues: list[Issue] = []
        for f in files:
            if not _posix(f.path).endswith("canon/target_baseline.json"):
                continue
            content = f.content if f.content is not None else f.load()
            if not isinstance(content, dict):
                continue

            cid = content.get("character_id")
            if cid != self._expected:
                issues.append(Issue(
                    file=f.path, json_path="$.character_id",
                    category="structural", severity="error",
                    rule="target_baseline_character_id_mismatch",
                    message=(f"character_id「{cid}」!= 期望角色"
                             f"「{self._expected}」（须与目录名一致）。"),
                    context={"expected": self._expected, "actual": cid},
                ))

            targets = content.get("targets")
            if not isinstance(targets, list):
                continue
            seen: set[str] = set()
            for idx, entry in enumerate(targets):
                if not isinstance(entry, dict):
                    continue
                tid = entry.get("target_character_id")
                if not isinstance(tid, str) or not tid:
                    continue
                if tid in seen:
                    issues.append(Issue(
                        file=f.path,
                        json_path=(f"$.targets[{idx}]"
                                   f".target_character_id"),
                        category="structural", severity="error",
                        rule="target_id_duplicate",
                        message=f"target_character_id「{tid}」重复。",
                        context={"target": tid},
                    ))
                seen.add(tid)
                if tid == self._expected:
                    issues.append(Issue(
                        file=f.path,
                        json_path=(f"$.targets[{idx}]"
                                   f".target_character_id"),
                        category="structural", severity="error",
                        rule="target_self_reference",
                        message=(f"target 指向 baseline 主角自身"
                                 f"「{tid}」（targets 只装其它角色）。"),
                        context={"target": tid},
                    ))
                elif tid not in self._legal_ids:
                    issues.append(Issue(
                        file=f.path,
                        json_path=(f"$.targets[{idx}]"
                                   f".target_character_id"),
                        category="structural", severity="error",
                        rule="target_id_not_candidate",
                        message=(
                            f"target_character_id「{tid}」不在 candidate_"
                            f"characters 合法 id 集内（统一用 identity ID，"
                            f"不要用 canonical_name / aliases）。"),
                        context={
                            "target": tid,
                            "legal_sample": sorted(self._legal_ids)[:10],
                        },
                    ))
        return issues
