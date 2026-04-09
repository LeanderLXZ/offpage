"""Three-level JSON repair: programmatic fix → LLM fix → full re-run.

Level 1 (programmatic, zero tokens):
  - Escape unescaped ASCII double quotes inside JSON string values
  - Remove trailing commas before } or ]
  - Strip trailing garbage after last valid } or ]
  - Fix truncated JSON (close open brackets/braces)

Level 2 (LLM repair, minimal tokens):
  - Send the broken JSON text to an LLM and ask it to output valid JSON
  - No source material needed — just the broken output

Level 3 (full re-run):
  - Caller's responsibility — this module only handles L1 and L2
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Level 1: Programmatic repair (zero tokens)
# ---------------------------------------------------------------------------

def _fix_inner_quotes(content: str) -> str:
    """Escape unescaped ASCII double quotes inside JSON string values.

    Targets lines matching the pattern ``"key": "value",`` where the value
    itself contains bare double quotes (commonly used as Chinese book-title
    marks by LLMs).  Also handles bare string elements in arrays.
    """
    lines = content.split("\n")
    fixed: list[str] = []

    for line in lines:
        # Pattern 1: key-value pairs — "key": "value with "inner" quotes",
        m = re.match(r'^(\s*"[^"]+"\s*:\s*)"(.*)"(,?\s*)$', line)
        if m:
            prefix, value, suffix = m.group(1), m.group(2), m.group(3)
            if '"' in value:
                value = value.replace('"', '\\"')
            fixed.append(f'{prefix}"{value}"{suffix}')
            continue

        # Pattern 2: bare array string elements — "some text with "quotes"",
        m2 = re.match(r'^(\s*)"(.*)"(,?\s*)$', line)
        if m2 and not re.match(r'^\s*"[^"]+"\s*:', line):
            prefix, value, suffix = m2.group(1), m2.group(2), m2.group(3)
            if '"' in value:
                value = value.replace('"', '\\"')
                fixed.append(f'{prefix}"{value}"{suffix}')
                continue

        fixed.append(line)

    return "\n".join(fixed)


def _fix_trailing_commas(content: str) -> str:
    """Remove trailing commas before ``}`` or ``]``."""
    return re.sub(r",\s*([}\]])", r"\1", content)


def _fix_truncated_json(content: str) -> str:
    """Attempt to close unclosed brackets/braces at the end of truncated JSON."""
    stripped = content.rstrip()
    if not stripped:
        return content

    # Count open/close brackets
    stack: list[str] = []
    in_string = False
    escape = False
    for ch in stripped:
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in ("{", "["):
            stack.append(ch)
        elif ch == "}" and stack and stack[-1] == "{":
            stack.pop()
        elif ch == "]" and stack and stack[-1] == "[":
            stack.pop()

    # Close any remaining open brackets
    closers = {"[": "]", "{": "}"}
    suffix = "".join(closers.get(c, "") for c in reversed(stack))
    if suffix:
        # Remove trailing comma before closing
        stripped = stripped.rstrip().rstrip(",")
        return stripped + "\n" + suffix
    return content


def _strip_trailing_garbage(content: str) -> str:
    """Strip anything after the last matching ``}`` or ``]`` at depth 0."""
    depth = 0
    in_string = False
    escape = False
    last_close = -1

    for i, ch in enumerate(content):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in ("{", "["):
            depth += 1
        elif ch in ("}", "]"):
            depth -= 1
            if depth == 0:
                last_close = i

    if last_close > 0 and last_close < len(content) - 1:
        trimmed = content[: last_close + 1]
        if trimmed.rstrip() != content.rstrip():
            logger.info("Stripped %d trailing garbage chars",
                        len(content) - last_close - 1)
        return trimmed
    return content


def programmatic_repair(content: str) -> str:
    """Apply all Level-1 fixes in sequence. Returns repaired text."""
    content = _fix_inner_quotes(content)
    content = _fix_trailing_commas(content)
    content = _strip_trailing_garbage(content)
    content = _fix_truncated_json(content)
    return content


# ---------------------------------------------------------------------------
# Level 2: LLM repair (minimal tokens — broken JSON only, no source)
# ---------------------------------------------------------------------------

_LLM_REPAIR_PROMPT = """\
下面是一个 JSON 文件的内容，但格式有问题导致无法被 json.loads 解析。
请修复所有 JSON 格式问题，输出一个有效的 JSON。

规则：
1. 只修复格式问题（引号转义、逗号、括号匹配等），不要修改任何实际内容
2. 如果字符串值内有裸双引号（如中文书名号用法），请转义为 \\"
3. 直接将修复后的 JSON 写入以下路径，不要输出其他内容：
   {output_path}

--- 原始内容 ---
{broken_json}
"""


def build_llm_repair_prompt(broken_content: str, output_path: str) -> str:
    """Build a prompt for LLM-based JSON repair."""
    return _LLM_REPAIR_PROMPT.format(
        broken_json=broken_content,
        output_path=output_path,
    )


# ---------------------------------------------------------------------------
# Unified repair entry point
# ---------------------------------------------------------------------------

def try_repair_json_file(
    path: Path,
    *,
    backend: object | None = None,
    expected_key: str | None = None,
) -> tuple[bool, str]:
    """Try to repair a JSON file. Returns (success, description).

    Parameters
    ----------
    path
        Path to the JSON file to repair.
    backend
        Optional LLM backend for Level-2 repair. If None, only Level-1 is
        attempted.
    expected_key
        If provided, the repaired JSON must contain this top-level key
        (e.g. ``"summaries"``).  Repair is considered failed if the key
        is missing or empty.
    """
    content = path.read_text(encoding="utf-8")

    # Already valid?
    try:
        data = json.loads(content)
        if expected_key and not data.get(expected_key):
            return False, f"valid JSON but '{expected_key}' is empty"
        return True, "already valid"
    except json.JSONDecodeError:
        pass

    # --- Level 1: programmatic ---
    repaired = programmatic_repair(content)
    try:
        data = json.loads(repaired)
        if expected_key and not data.get(expected_key):
            return False, f"L1 fix parsed but '{expected_key}' is empty"
        # Write back clean JSON
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        logger.info("L1 programmatic repair succeeded: %s", path.name)
        return True, "L1 programmatic fix"
    except json.JSONDecodeError:
        logger.info("L1 repair failed for %s, trying L2", path.name)

    # --- Level 2: LLM repair ---
    if backend is None:
        return False, "L1 failed and no LLM backend for L2"

    # Import here to avoid circular dependency
    from .llm_backend import LLMBackend, run_with_retry

    if not isinstance(backend, LLMBackend):
        return False, "L1 failed and backend is not an LLMBackend"

    prompt = build_llm_repair_prompt(content, str(path))
    result = run_with_retry(backend, prompt, timeout_seconds=120)

    if not result.success:
        return False, f"L2 LLM repair call failed: {result.error}"

    # Check if LLM wrote the file
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if expected_key and not data.get(expected_key):
            return False, f"L2 wrote file but '{expected_key}' is empty"
        logger.info("L2 LLM repair succeeded: %s", path.name)
        return True, "L2 LLM fix"
    except json.JSONDecodeError:
        return False, "L2 LLM repair did not produce valid JSON"


def try_repair_jsonl_file(
    path: Path,
    *,
    backend: object | None = None,
) -> tuple[bool, str]:
    """Try to repair a JSONL file (one JSON object per line).

    Only applies Level-1 (per-line programmatic fix). Level-2 is not
    attempted for JSONL since sending the whole file may be too large.
    """
    content = path.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    fixed_lines: list[str] = []
    repairs = 0

    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        try:
            json.loads(line)
            fixed_lines.append(line)
        except json.JSONDecodeError:
            repaired = programmatic_repair(line)
            try:
                json.loads(repaired)
                fixed_lines.append(repaired)
                repairs += 1
            except json.JSONDecodeError:
                logger.warning("JSONL line %d unfixable in %s", i, path.name)
                fixed_lines.append(line)  # keep as-is

    if repairs > 0:
        path.write_text("\n".join(fixed_lines) + "\n", encoding="utf-8")
        return True, f"L1 fixed {repairs} JSONL lines"
    elif all(_is_valid_json(l) for l in fixed_lines):
        return True, "already valid"
    else:
        return False, "some JSONL lines unfixable"


def _is_valid_json(text: str) -> bool:
    try:
        json.loads(text)
        return True
    except (json.JSONDecodeError, ValueError):
        return False
