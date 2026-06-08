"""Physical measurement helpers (Python mirror of frontend measurementHelpers.js)."""
from __future__ import annotations

from typing import Any


def pixels_to_microns(pixels: float, um_per_pixel: float) -> float | None:
    if not um_per_pixel or um_per_pixel <= 0:
        return None
    return pixels * um_per_pixel


def rectangle_area(rect: dict[str, Any]) -> float:
    return abs(float(rect.get("width") or 0) * float(rect.get("height") or 0))


def rectangle_perimeter(rect: dict[str, Any]) -> float:
    w = abs(float(rect.get("width") or 0))
    h = abs(float(rect.get("height") or 0))
    return 2 * (w + h)


def polygon_area(points: list[dict[str, Any]]) -> float:
    if len(points) < 3:
        return 0.0
    total = 0.0
    for i, p1 in enumerate(points):
        p2 = points[(i + 1) % len(points)]
        total += float(p1["x"]) * float(p2["y"]) - float(p2["x"]) * float(p1["y"])
    return abs(total) / 2.0


def polygon_perimeter(points: list[dict[str, Any]]) -> float:
    if len(points) < 2:
        return 0.0
    length = 0.0
    for i, p1 in enumerate(points):
        p2 = points[(i + 1) % len(points)]
        dx = float(p2["x"]) - float(p1["x"])
        dy = float(p2["y"]) - float(p1["y"])
        length += (dx * dx + dy * dy) ** 0.5
    return length
