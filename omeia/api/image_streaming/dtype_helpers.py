"""Scientific dtype profiles for viewer manifest and pixel probe."""
from __future__ import annotations

import re
from typing import Any


_DTYPE_RE = re.compile(r"^(?:<|>)?(?:u)?(int|float)(\d+)$", re.IGNORECASE)


def dtype_profile(dtype: str | None) -> dict[str, Any]:
    """Map numpy/tifffile dtype string to viewer-safe value range metadata."""
    raw = str(dtype or "uint8").strip().lower()
    match = _DTYPE_RE.match(raw.replace("numpy.", ""))
    if not match:
        return {
            "dtype": raw,
            "bit_depth": 8,
            "value_min": 0,
            "value_max": 255,
            "is_float": False,
        }

    kind, bits = match.group(1).lower(), int(match.group(2))
    is_float = kind == "float"
    if is_float:
        return {
            "dtype": raw,
            "bit_depth": bits,
            "value_min": 0.0,
            "value_max": 1.0,
            "is_float": True,
        }

    value_max = (2**bits) - 1
    return {
        "dtype": raw,
        "bit_depth": bits,
        "value_min": 0,
        "value_max": value_max,
        "is_float": False,
    }
