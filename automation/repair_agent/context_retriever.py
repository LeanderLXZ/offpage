"""Context retriever — locates relevant original chapter text for T2 fixes.

Two-step process:
  1. Search chapter_summaries for keywords → locate chapter numbers (0 token)
  2. Load original chapter text from sources/ (0 token)
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from .protocol import Issue, SourceContext

logger = logging.getLogger(__name__)


class ContextRetriever:
    """Retrieves original chapter text relevant to an issue."""

    def retrieve(
        self,
        issue: Issue,
        source_ctx: SourceContext,
        attempt_num: int,
        max_attempts: int,
    ) -> str:
        """Return relevant chapter text for a T2 source_patch fix.

        attempt_num 0: top-3 chapters
        attempt_num 1: top-5 + adjacent chapters
        attempt_num ≥2: all chapters in the stage
        """
        stage_chapters = self._get_stage_chapters(source_ctx)
        if not stage_chapters:
            logger.warning("No stage chapters found for %s", source_ctx.stage_id)
            return ""

        keywords = self._extract_keywords(issue)
        summaries_dir = Path(source_ctx.chapter_summaries_dir)
        chapters_dir = Path(source_ctx.chapters_dir)

        # Step 1: rank chapters by keyword relevance
        ranked = self._rank_chapters(stage_chapters, keywords, summaries_dir)

        # Step 2: determine how many chapters to load based on attempt
        if attempt_num >= max_attempts or attempt_num >= 3:
            # Last attempt: load all stage chapters
            selected = stage_chapters
        elif attempt_num >= 2:
            # Expanded: top-5 + adjacent
            top = ranked[:5]
            expanded = set(top)
            for ch in top:
                idx = stage_chapters.index(ch) if ch in stage_chapters else -1
                if idx > 0:
                    expanded.add(stage_chapters[idx - 1])
                if idx < len(stage_chapters) - 1:
                    expanded.add(stage_chapters[idx + 1])
            selected = sorted(expanded)
        else:
            # First attempt: top-3
            selected = ranked[:3]

        # Step 3: load chapter text
        texts: list[str] = []
        for ch_num in selected:
            text = self._load_chapter(chapters_dir, ch_num)
            if text:
                texts.append(f"=== 第{ch_num}章 ===\n{text}")

        result = "\n\n".join(texts)
        logger.info(
            "Retrieved %d chapters (%d chars) for %s attempt %d",
            len(texts), len(result), issue.fingerprint, attempt_num + 1,
        )
        return result

    def retrieve_all_stage(self, source_ctx: SourceContext) -> str:
        """Load all chapter text for the stage (used by T3 file_regen)."""
        stage_chapters = self._get_stage_chapters(source_ctx)
        if not stage_chapters:
            return ""
        chapters_dir = Path(source_ctx.chapters_dir)
        texts: list[str] = []
        for ch_num in stage_chapters:
            text = self._load_chapter(chapters_dir, ch_num)
            if text:
                texts.append(f"=== 第{ch_num}章 ===\n{text}")
        result = "\n\n".join(texts)
        logger.info("Retrieved all %d stage chapters (%d chars)",
                     len(texts), len(result))
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_stage_chapters(self, ctx: SourceContext) -> list[int]:
        """Get chapter numbers for the stage from stage_plan.json."""
        work_path = Path(ctx.work_path)
        plan_path = work_path / "analysis" / "stage_plan.json"
        if not plan_path.exists():
            return []
        try:
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            for stage in plan.get("stages", []):
                if stage.get("stage_id") == ctx.stage_id:
                    chapters = stage.get("chapters", [])
                    if isinstance(chapters, list) and len(chapters) == 2:
                        return list(range(chapters[0], chapters[1] + 1))
                    return chapters
        except (json.JSONDecodeError, OSError):
            pass
        return []

    def _extract_keywords(self, issue: Issue) -> list[str]:
        """Extract search keywords from issue json_path and message."""
        keywords: list[str] = []
        # Extract character names from json_path like $.relationships[角色B]
        bracket_matches = re.findall(r"\[([^\]]+)\]", issue.json_path)
        keywords.extend(
            m for m in bracket_matches if not m.isdigit()
        )
        # Extract meaningful words from message (Chinese-aware)
        words = re.findall(r"[\u4e00-\u9fff]{2,}", issue.message)
        keywords.extend(words[:5])
        return keywords

    def _rank_chapters(
        self,
        chapters: list[int],
        keywords: list[str],
        summaries_dir: Path,
    ) -> list[int]:
        """Rank chapters by keyword occurrence in their summaries."""
        scores: dict[int, int] = {}
        for ch in chapters:
            summary_text = self._load_chapter_summary(summaries_dir, ch)
            if not summary_text:
                scores[ch] = 0
                continue
            score = sum(summary_text.count(kw) for kw in keywords if kw)
            scores[ch] = score
        return sorted(chapters, key=lambda c: scores.get(c, 0), reverse=True)

    def _load_chapter_summary(self, summaries_dir: Path,
                              chapter_num: int) -> str:
        """Load a chapter summary from the summaries directory."""
        # Try common naming patterns
        for pattern in [f"{chapter_num:04d}.json", f"{chapter_num}.json"]:
            path = summaries_dir / pattern
            if path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        return data.get("summary", json.dumps(data, ensure_ascii=False))
                    return json.dumps(data, ensure_ascii=False)
                except (json.JSONDecodeError, OSError):
                    continue
        # Try chunk files that may contain multiple chapters
        for chunk_file in sorted(summaries_dir.glob("chunk_*.json")):
            try:
                chunk = json.loads(chunk_file.read_text(encoding="utf-8"))
                if isinstance(chunk, list):
                    for entry in chunk:
                        if isinstance(entry, dict):
                            ch = entry.get("chapter_number") or entry.get("chapter")
                            if ch == chapter_num:
                                return entry.get("summary", json.dumps(entry, ensure_ascii=False))
                elif isinstance(chunk, dict):
                    chapters = chunk.get("chapters", [])
                    for entry in chapters:
                        ch = entry.get("chapter_number") or entry.get("chapter")
                        if ch == chapter_num:
                            return entry.get("summary", json.dumps(entry, ensure_ascii=False))
            except (json.JSONDecodeError, OSError):
                continue
        return ""

    def _load_chapter(self, chapters_dir: Path, chapter_num: int) -> str:
        """Load original chapter text."""
        for pattern in [f"{chapter_num:04d}.txt", f"{chapter_num}.txt",
                        f"chapter_{chapter_num:04d}.txt"]:
            path = chapters_dir / pattern
            if path.exists():
                try:
                    return path.read_text(encoding="utf-8")
                except OSError:
                    continue
        return ""
