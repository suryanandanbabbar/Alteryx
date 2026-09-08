"""Shared structured JSON extraction and parsing layer for LLM responses.

Provides robust, multi-pass JSON extraction from arbitrary LLM completion responses:
- Direct JSON parsing
- Markdown code fence unwrapping (```json ... ```)
- Balanced bracket scanning ({ ... } and [ ... ])
- Safe trailing comma normalization
- Unicode BOM / think-tag stripping
- Explicit rejection of None, empty, or whitespace responses
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Sequence

logger = logging.getLogger("awa.llm.json_extractor")


def _find_balanced_json_blocks(text: str) -> list[str]:
    """Scan text for all balanced top-level JSON objects ({...}) and arrays ([...]).

    Correctly handles:
    - Escaped quotes (\\")
    - Nested braces and brackets
    - String literals containing braces/brackets
    - Mixed content before and after JSON
    """
    candidates: list[str] = []
    in_string = False
    escape = False
    brace_depth = 0
    bracket_depth = 0
    start_idx = -1
    active_type: str | None = None  # "object" or "array"

    for i, ch in enumerate(text):
        if escape:
            escape = False
            continue

        if ch == "\\":
            if in_string:
                escape = True
            continue

        if ch == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        # Top-level opener
        if ch == "{" and active_type is None:
            active_type = "object"
            brace_depth = 1
            start_idx = i
        elif ch == "{" and active_type == "object":
            brace_depth += 1
        elif ch == "}" and active_type == "object":
            brace_depth -= 1
            if brace_depth == 0:
                if start_idx != -1:
                    candidates.append(text[start_idx : i + 1])
                start_idx = -1
                active_type = None

        elif ch == "[" and active_type is None:
            active_type = "array"
            bracket_depth = 1
            start_idx = i
        elif ch == "[" and active_type == "array":
            bracket_depth += 1
        elif ch == "]" and active_type == "array":
            bracket_depth -= 1
            if bracket_depth == 0:
                if start_idx != -1:
                    candidates.append(text[start_idx : i + 1])
                start_idx = -1
                active_type = None

    return candidates


def _normalize_safe_json(candidate: str) -> str:
    """Apply safe, non-destructive normalizations to repair common LLM syntax deviations."""
    clean = candidate.strip()

    # 1. Strip trailing commas before closing braces/brackets: [1, 2,] -> [1, 2]
    clean = re.sub(r",\s*([\]}])", r"\1", clean)

    # 2. Normalize common boolean/null capitalization if unquoted
    # (Only outside strings - handles pythonic True/False/None)
    clean = re.sub(r":\s*True\b", ": true", clean)
    clean = re.sub(r":\s*False\b", ": false", clean)
    clean = re.sub(r":\s*None\b", ": null", clean)

    return clean


def extract_and_parse_json(
    raw_response: Any,
    expected_type: type = dict,
) -> tuple[dict[str, Any] | list[Any] | None, str, str]:
    """Extract and parse structured JSON from arbitrary LLM response.

    Args:
        raw_response: Raw response from LLM client (string, dict, list, or object).
        expected_type: Expected root data type (dict or list).

    Returns:
        tuple of (parsed_data, status, error_reason)
        status is one of: "success", "empty_response", "extraction_failed", "json_parse_failed", "type_mismatch"
    """
    # Step 1: Explicit empty / None rejection
    if raw_response is None:
        return None, "empty_response", "Response is None"

    # Step 2: Already-parsed dict or list
    if isinstance(raw_response, (dict, list)):
        if isinstance(raw_response, expected_type):
            return raw_response, "success", ""
        return None, "type_mismatch", f"Expected {expected_type.__name__}, got {type(raw_response).__name__}"

    # Step 3: Object with .content or .text attribute
    if hasattr(raw_response, "content") and isinstance(getattr(raw_response, "content"), (str, dict, list)):
        return extract_and_parse_json(getattr(raw_response, "content"), expected_type=expected_type)
    if hasattr(raw_response, "text") and isinstance(getattr(raw_response, "text"), (str, dict, list)):
        return extract_and_parse_json(getattr(raw_response, "text"), expected_type=expected_type)

    if not isinstance(raw_response, str):
        return None, "empty_response", f"Unsupported response type: {type(raw_response).__name__}"

    text = raw_response.strip()
    if not text:
        return None, "empty_response", "Response text is empty or whitespace"

    # Step 4: Clean BOM and reasoning tags
    text = text.lstrip("\ufeff")
    if "<think>" in text.lower() and "</think>" in text.lower():
        text = re.sub(r"^[\s\S]*?</think>\s*", "", text, flags=re.IGNORECASE).strip()
        if not text:
            return None, "empty_response", "Response is empty after removing reasoning tags"

    # Step 5: Collect candidate JSON strings in priority order
    candidates: list[str] = []

    # Priority 1: Direct exact match if entire string is bounded
    if (expected_type == dict and text.startswith("{") and text.endswith("}")) or (
        expected_type == list and text.startswith("[") and text.endswith("]")
    ):
        candidates.append(text)

    # Priority 2: Markdown fenced code blocks (```json ... ``` or ``` ... ```)
    code_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    for block in code_blocks:
        b = block.strip()
        if b and b not in candidates:
            candidates.append(b)

    # Priority 3: Balanced bracket/brace scanner across surrounding prose
    balanced_blocks = _find_balanced_json_blocks(text)
    for block in balanced_blocks:
        b = block.strip()
        if b and b not in candidates:
            candidates.append(b)

    if not candidates:
        return None, "extraction_failed", "No JSON object or array structure found in response"

    # Step 6: Parse candidates with bounded recovery
    last_error = ""
    for cand in candidates:
        # Pass A: Strict json.loads
        try:
            parsed = json.loads(cand)
            if isinstance(parsed, expected_type):
                return parsed, "success", ""
            elif isinstance(parsed, (dict, list)):
                # If parsed is valid JSON but root type differs, check if expected structure is inside
                if expected_type == dict and isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
                    pass
                elif expected_type == list and isinstance(parsed, dict):
                    for k in ("stages", "items", "data", "results", "mappings", "findings", "inputs", "outputs"):
                        if k in parsed and isinstance(parsed[k], list):
                            return parsed[k], "success", ""
        except Exception as exc:
            last_error = str(exc)

        # Pass B: Normalized safe repair (trailing commas, python booleans)
        try:
            normalized = _normalize_safe_json(cand)
            parsed = json.loads(normalized)
            if isinstance(parsed, expected_type):
                return parsed, "success", ""
            elif isinstance(parsed, (dict, list)):
                if expected_type == list and isinstance(parsed, dict):
                    for k in ("stages", "items", "data", "results", "mappings", "findings", "inputs", "outputs"):
                        if k in parsed and isinstance(parsed[k], list):
                            return parsed[k], "success", ""
        except Exception as exc:
            last_error = str(exc)

    return None, "json_parse_failed", f"Failed to parse JSON candidates: {last_error}"
