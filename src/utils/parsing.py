from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger("parsing")


def extract_match_score(response_text: str) -> int:
    """
    Extract the first score between 0 and 100 from model output.
    """
    match = re.search(r"\b(100|[1-9]?[0-9])\b", response_text)
    if match:
        return int(match.group(0))
    return 0


def extract_json_object(raw_text: str) -> dict[str, Any] | None:
    """
    Extract and parse the first JSON object found in a text blob.

    Returns None if parsing fails.
    """
    if not raw_text:
        return None

    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if not match:
        logger.warning("No JSON object found in text.")
        return None

    cleaned = match.group(0).replace("\xa0", " ").replace("\n", " ").strip()

    try:
        return json.loads(cleaned, strict=False)
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse JSON object: %s", exc)
        return None


def normalize_whitespace(text: str) -> str:
    """
    Collapse repeated whitespace and trim the result.
    """
    return re.sub(r"\s+", " ", text).strip()


def safe_get_text(value: Any, default: str = "") -> str:
    """
    Return a safe string value for display or concatenation.
    """
    if value is None:
        return default
    return str(value)