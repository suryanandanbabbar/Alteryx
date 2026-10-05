"""Canonical payload serialisation for Ed25519 signature generation.

CRITICAL CONTRACT:
Both the Azure License Server signing logic and the client verification logic
must produce the exact same byte sequence for a given payload dictionary.

Algorithm:
1. Exclude the "signature" key if present.
2. Serialise remaining keys as compact JSON with sorted keys:
   - sort_keys=True
   - separators=(",", ":")
   - default=str (for datetimes or other non-primitive types)
3. Encode as UTF-8 bytes.
"""

from __future__ import annotations

import json
from typing import Any


def canonical_payload(data: dict[str, Any]) -> bytes:
    """Produce the canonical UTF-8 bytes representation for Ed25519 signing.

    Args:
        data: Response dictionary containing all payload fields.

    Returns:
        Deterministic UTF-8 bytes representation with signature field excluded.
    """
    filtered = {k: v for k, v in data.items() if k != "signature"}
    return json.dumps(
        filtered,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
