#!/usr/bin/env python3
"""Render a Claude Code session transcript (JSONL) to a self-contained HTML chat log.

Owned by the /save-chat skill. The skill body is the source of truth for *when* and
*why* this runs; this script is the deterministic *how* (locate -> filter -> md->HTML
-> fill template). Keeping the transform here (not in skill prose) means it can only
change via an explicit script edit, and the AI re-emits only the summary fragment, not
the transcript -- so cost stays flat regardless of conversation length.

Pipeline:
  1. Locate the session transcript .jsonl (see resolve_transcript).
  2. Keep only genuine user/assistant TEXT turns; drop thinking, tool_use, tool_result,
     isMeta (skill-body / context injections), and isSidechain (sub-agent) records.
  3. Render each turn's markdown to HTML with a dependency-free mini converter.
  4. Splice an AI-authored summary fragment (--summary-file) above the transcript into
     a static template (template.html), write to <out-dir>/<timestamp>_<ai>_<slug>.html.

The caller (skill) computes the timestamp per skills_config.md §Timezone and passes it
via --timestamp; if omitted, local time is used as a fallback.

Usage examples:
  # list turns (index | role | preview) so a subset can be chosen, then exit
  transcript_to_html.py --list

  # render the whole current session
  transcript_to_html.py --title "..." --slug topic-slug --ai claude \
      --timestamp 2026-06-06_185414 --summary-file /tmp/summary.html

  # render only turns 5..20
  transcript_to_html.py ... --from 5 --to 20
"""
from __future__ import annotations

import argparse
import datetime as _dt
import glob
import html
import json
import os
import re
import sys
from pathlib import Path

PROJECTS_ROOT = Path.home() / ".claude" / "projects"
PLACEHOLDER = "\x00{}\x00"


# --------------------------------------------------------------------------- locate
def first_record_cwd(jsonl_path: Path) -> str | None:
    """Return the `cwd` of the first record carrying one, or None."""
    try:
        with open(jsonl_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(rec, dict) and rec.get("cwd"):
                    return rec["cwd"]
    except OSError:
        return None
    return None


def resolve_transcript(explicit: str | None, session_id: str | None) -> Path:
    """Resolve the transcript .jsonl path.

    Priority: --transcript -> session id (glob across project dirs; the id is globally
    unique so mangled-cwd derivation is unnecessary) -> newest .jsonl whose first
    record's cwd matches the current working directory.
    """
    if explicit:
        p = Path(explicit).expanduser()
        if p.is_file():
            return p
        sys.exit(f"[save-chat] --transcript not found: {p}")

    if session_id:
        hits = sorted(PROJECTS_ROOT.glob(f"*/{session_id}.jsonl"))
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            # session id should be unique; if a stray copy collides, prefer the
            # cwd-matching transcript, else the most recently written one.
            cwd = str(Path.cwd())
            cwd_match = [h for h in hits if first_record_cwd(h) == cwd]
            if cwd_match:
                return cwd_match[0]
            return max(hits, key=lambda h: h.stat().st_mtime)
        sys.exit(
            f"[save-chat] no transcript for session id {session_id} under {PROJECTS_ROOT}"
        )

    cwd = str(Path.cwd())
    candidates = [
        (p.stat().st_mtime, p)
        for p in PROJECTS_ROOT.glob("*/*.jsonl")
        if first_record_cwd(p) == cwd
    ]
    if candidates:
        return max(candidates)[1]
    sys.exit(
        "[save-chat] could not locate a session transcript; pass --transcript or set "
        "$CLAUDE_CODE_SESSION_ID"
    )


# ---------------------------------------------------------------------------- parse
_SYSTEM_REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL)
_LOCAL_STDOUT = re.compile(r"<local-command-stdout>.*?</local-command-stdout>", re.DOTALL)
_COMMAND_TAGS = re.compile(r"</?command-[a-z-]+>")
_BLANKS = re.compile(r"\n{3,}")
# synthetic marker injected when the user interrupts a response mid-stream;
# it is not a real conversation turn.
_INTERRUPT = re.compile(r"\[Request interrupted[^\]]*\]")


def clean_user_text(text: str) -> str:
    """Strip injection wrappers from a genuine user turn."""
    text = _SYSTEM_REMINDER.sub("", text)
    text = _LOCAL_STDOUT.sub("", text)
    text = _COMMAND_TAGS.sub(" ", text)
    text = _BLANKS.sub("\n\n", text)
    return text.strip()


def extract_text(content) -> str:
    """Join the text blocks of a message; ignore thinking / tool_use / tool_result."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            b["text"]
            for b in content
            if isinstance(b, dict) and b.get("type") == "text" and b.get("text")
        ]
        return "\n\n".join(parts)
    return ""


def parse_turns(path: Path) -> list[dict]:
    """Return ordered [{role, text}] genuine conversation turns."""
    turns: list[dict] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(rec, dict):
                continue
            if rec.get("isMeta") or rec.get("isSidechain"):
                continue
            if rec.get("type") not in ("user", "assistant"):
                continue
            msg = rec.get("message") or {}
            role = msg.get("role") or rec["type"]
            text = extract_text(msg.get("content"))
            if role == "user":
                text = clean_user_text(text)
            text = text.strip()
            if not text:
                continue
            if role == "user" and _INTERRUPT.fullmatch(text):
                continue  # drop the synthetic "[Request interrupted ...]" marker
            turns.append({"role": role, "text": text})
    return turns


# ------------------------------------------------------------------------- md->html
def _safe_href(url: str) -> str | None:
    """Attribute-escape a URL; reject dangerous schemes (javascript:/data:/vbscript:)."""
    u = url.strip()
    if re.match(r"(?i)\s*(javascript|data|vbscript):", u):
        return None
    return html.escape(u, quote=True)


def _inline(s: str) -> str:
    """Inline markdown -> HTML on a single text run.

    Escapes first, then stashes already-rendered fragments (code spans, anchors) so
    later emphasis substitution can never run over a tag's attributes — this keeps
    `__dunder__` / `*` inside URLs from corrupting hrefs and avoids HTML injection via
    a crafted link target. Only `**` is treated as bold (bare `__` collides with code
    identifiers like `__init__`); single `*` / `_` is identifier-safe italic.
    """
    s = html.escape(s, quote=False)
    stash: list[str] = []

    def _keep(fragment: str) -> str:
        stash.append(fragment)
        return PLACEHOLDER.format(len(stash) - 1)

    # code spans (content already escaped) -> stash
    s = re.sub(r"`([^`]+)`", lambda m: _keep(f"<code>{m.group(1)}</code>"), s)

    # links: escape href, drop unsafe schemes, stash the whole anchor
    def _link(m: re.Match) -> str:
        href = _safe_href(m.group(2))
        if href is None:
            return m.group(1)  # unsafe URL -> keep link text only
        return _keep(f'<a href="{href}">{m.group(1)}</a>')

    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", _link, s)

    # emphasis (bold only via **, identifier-safe italic)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*(?!\*)([^*\n]+?)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"(?<![\w*])_(?!_)([^_\n]+?)_(?![\w])", r"<em>\1</em>", s)

    # restore stashed fragments (loop: a stashed link may contain a code placeholder)
    while "\x00" in s:
        new = re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m.group(1))], s)
        if new == s:
            break
        s = new
    return s


def _is_table_sep(line: str) -> bool:
    return bool(re.match(r"^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$", line)) and "-" in line


def _split_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def md_to_html(text: str) -> str:
    """Dependency-free markdown -> HTML covering the chat-prose subset:
    fenced code, GFM tables, ul/ol lists, blockquotes, headings, hr, paragraphs,
    plus inline bold/italic/code/links. Nested lists render flat (one level)."""
    lines = text.split("\n")
    out: list[str] = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]

        # fenced code block
        m = re.match(r"^\s*```(.*)$", line)
        if m:
            i += 1
            buf = []
            while i < n and not re.match(r"^\s*```\s*$", lines[i]):
                buf.append(lines[i])
                i += 1
            i += 1  # closing fence
            out.append(
                "<pre><code>" + html.escape("\n".join(buf), quote=False) + "</code></pre>"
            )
            continue

        # blank
        if not line.strip():
            i += 1
            continue

        # horizontal rule
        if re.match(r"^\s*([-*_])\1{2,}\s*$", line):
            out.append("<hr>")
            i += 1
            continue

        # heading (markdown level N -> h(N+2), clamped to h6, kept subordinate to page)
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            level = min(len(m.group(1)) + 2, 6)
            out.append(f"<h{level}>{_inline(m.group(2).strip())}</h{level}>")
            i += 1
            continue

        # GFM table: header row followed by a separator row
        if "|" in line and i + 1 < n and _is_table_sep(lines[i + 1]):
            header = _split_row(line)
            i += 2
            rows = []
            while i < n and "|" in lines[i] and lines[i].strip():
                rows.append(_split_row(lines[i]))
                i += 1
            thead = "".join(f"<th>{_inline(c)}</th>" for c in header)
            body = "".join(
                "<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>"
                for r in rows
            )
            out.append(f"<table><thead><tr>{thead}</tr></thead><tbody>{body}</tbody></table>")
            continue

        # blockquote
        if re.match(r"^\s*>\s?", line):
            buf = []
            while i < n and re.match(r"^\s*>\s?", lines[i]):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            out.append("<blockquote>" + md_to_html("\n".join(buf)) + "</blockquote>")
            continue

        # unordered list
        if re.match(r"^\s*[-*+]\s+", line):
            items = []
            while i < n and re.match(r"^\s*[-*+]\s+", lines[i]):
                items.append(_inline(re.sub(r"^\s*[-*+]\s+", "", lines[i]).strip()))
                i += 1
            out.append("<ul>" + "".join(f"<li>{it}</li>" for it in items) + "</ul>")
            continue

        # ordered list
        if re.match(r"^\s*\d+[.)]\s+", line):
            items = []
            while i < n and re.match(r"^\s*\d+[.)]\s+", lines[i]):
                items.append(_inline(re.sub(r"^\s*\d+[.)]\s+", "", lines[i]).strip()))
                i += 1
            out.append("<ol>" + "".join(f"<li>{it}</li>" for it in items) + "</ol>")
            continue

        # paragraph (gather consecutive non-blank, non-block lines)
        buf = []
        while i < n and lines[i].strip() and not re.match(
            r"^\s*(```|#{1,6}\s|>\s?|[-*+]\s|\d+[.)]\s|([-*_])\2{2,}\s*$)", lines[i]
        ):
            if "|" in lines[i] and i + 1 < n and _is_table_sep(lines[i + 1]):
                break
            buf.append(lines[i].strip())
            i += 1
        if buf:
            out.append("<p>" + _inline(" ".join(buf)) + "</p>")
    return "\n".join(out)


# ------------------------------------------------------------------------- assemble
def render_transcript(turns: list[dict], ai_label: str) -> str:
    blocks = []
    for idx, t in enumerate(turns, 1):
        is_user = t["role"] == "user"
        cls = "user" if is_user else "ai"
        who = "User" if is_user else ai_label
        blocks.append(
            f'<section class="msg {cls}" id="t{idx}">\n'
            f'  <div class="role"><span class="dot"></span>{html.escape(who)}'
            f'<span class="idx">#{idx}</span></div>\n'
            f'  <div class="content">{md_to_html(t["text"])}</div>\n'
            f"</section>"
        )
    return "\n".join(blocks)


def main() -> None:
    ap = argparse.ArgumentParser(description="Render a session transcript to chat-log HTML.")
    ap.add_argument("--transcript", help="explicit .jsonl path (overrides session id)")
    ap.add_argument("--session-id", default=os.environ.get("CLAUDE_CODE_SESSION_ID"))
    ap.add_argument("--from", dest="frm", type=int, default=1, help="first turn index (1-based)")
    ap.add_argument("--to", type=int, default=0, help="last turn index (0 = through end)")
    ap.add_argument("--list", action="store_true", help="list turns then exit")
    ap.add_argument("--title", default="Chat log")
    ap.add_argument("--kicker", default="Conversation log")
    ap.add_argument("--slug", default="chat")
    ap.add_argument("--ai", default="claude", help="runtime family: claude / codex / ...")
    ap.add_argument("--summary-file", help="path to an HTML fragment for the summary block")
    ap.add_argument("--timestamp", help="YYYY-MM-DD_HHMMSS (caller supplies per §Timezone)")
    ap.add_argument("--out-dir", default="logs/chats", help="output directory (auto-created)")
    ap.add_argument("--template", help="template path (default: sibling template.html)")
    args = ap.parse_args()

    path = resolve_transcript(args.transcript, args.session_id)
    turns = parse_turns(path)
    if not turns:
        sys.exit(f"[save-chat] no conversation turns parsed from {path}")

    if args.list:
        for idx, t in enumerate(turns, 1):
            preview = re.sub(r"\s+", " ", t["text"]).strip()[:90]
            print(f"{idx:>4}  {t['role']:<9}  {preview}")
        print(f"\n[save-chat] {len(turns)} turns in {path.name}", file=sys.stderr)
        return

    lo = max(1, args.frm)
    hi = args.to if args.to and args.to > 0 else len(turns)
    selected = turns[lo - 1 : hi]
    if not selected:
        sys.exit(f"[save-chat] empty selection (--from {args.frm} --to {args.to}; have {len(turns)})")

    ai_label = args.ai[:1].upper() + args.ai[1:] if args.ai else "AI"

    summary_html = ""
    if args.summary_file:
        sf = Path(args.summary_file)
        if not sf.is_file():
            sys.exit(f"[save-chat] --summary-file not found: {sf}")
        summary_html = sf.read_text(encoding="utf-8").strip()

    tpl_path = Path(args.template) if args.template else Path(__file__).resolve().parent.parent / "template.html"
    template = tpl_path.read_text(encoding="utf-8")

    ts = args.timestamp or _dt.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    # sanitize the filename components (slug/ai may carry spaces or path chars)
    safe_ai = re.sub(r"[^A-Za-z0-9._-]+", "-", args.ai).strip("-") or "ai"
    safe_slug = re.sub(r"[^A-Za-z0-9._-]+", "-", args.slug).strip("-") or "chat"
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{ts}_{safe_ai}_{safe_slug}.html"

    meta_tags = (
        f'<span class="tag"><b>AI</b> {html.escape(ai_label)}</span>'
        f'<span class="tag"><b>Turns</b> {len(selected)}</span>'
        f'<span class="tag"><b>When</b> {html.escape(ts)}</span>'
        f'<span class="tag"><b>Session</b> {html.escape(path.stem[:8])}</span>'
    )
    summary_block = (
        f'<section class="summary">{summary_html}</section>' if summary_html else ""
    )

    out_html = (
        template.replace("{{TITLE}}", html.escape(args.title))
        .replace("{{KICKER}}", html.escape(args.kicker))
        .replace("{{META_TAGS}}", meta_tags)
        .replace("{{SUMMARY}}", summary_block)
        .replace("{{TRANSCRIPT}}", render_transcript(selected, ai_label))
        .replace("{{GENERATED}}", html.escape(ts))
    )
    out_path.write_text(out_html, encoding="utf-8")
    print(str(out_path))


if __name__ == "__main__":
    main()
