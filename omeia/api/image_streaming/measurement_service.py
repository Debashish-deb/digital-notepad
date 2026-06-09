"""ROI measurement from raw image regions (scientific instrument)."""
from __future__ import annotations

import math
from typing import Any


def _polygon_area(points: list[dict[str, float]]) -> float:
    if len(points) < 3:
        return 0.0
    area = 0.0
    for i, p in enumerate(points):
        j = (i + 1) % len(points)
        area += p["x"] * points[j]["y"] - points[j]["x"] * p["y"]
    return abs(area) / 2.0


def _polygon_perimeter(points: list[dict[str, float]]) -> float:
    if len(points) < 2:
        return 0.0
    total = 0.0
    for i, p in enumerate(points):
        j = (i + 1) % len(points)
        total += math.hypot(points[j]["x"] - p["x"], points[j]["y"] - p["y"])
    return total


def _circle_metrics(geometry: dict[str, Any]) -> tuple[float, float]:
    r = float(geometry.get("radius") or 0)
    return math.pi * r * r, 2 * math.pi * r


def _line_length(geometry: dict[str, Any]) -> float:
    pts = geometry.get("points") or []
    if len(pts) < 2:
        return 0.0
    return math.hypot(pts[1]["x"] - pts[0]["x"], pts[1]["y"] - pts[0]["y"])


def geometry_area_perimeter(geometry: dict[str, Any], roi_type: str) -> tuple[float, float]:
    """Pixel units area and perimeter for supported ROI types."""
    roi_type = (roi_type or geometry.get("type") or "rectangle").lower()
    if roi_type == "circle":
        return _circle_metrics(geometry)
    if roi_type in ("polygon", "freehand"):
        pts = geometry.get("points") or []
        return _polygon_area(pts), _polygon_perimeter(pts)
    if roi_type == "line":
        return 0.0, _line_length(geometry)
    # rectangle
    w = abs(float(geometry.get("width") or 0))
    h = abs(float(geometry.get("height") or 0))
    return w * h, 2 * (w + h)


def _point_in_polygon(x: float, y: float, points: list[dict[str, float]]) -> bool:
    inside = False
    n = len(points)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = points[i]["x"], points[i]["y"]
        xj, yj = points[j]["x"], points[j]["y"]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / max(yj - yi, 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def _point_in_geometry(x: float, y: float, geometry: dict[str, Any], roi_type: str) -> bool:
    roi_type = (roi_type or "rectangle").lower()
    if roi_type == "circle":
        cx = float(geometry.get("cx") or geometry.get("x") or 0)
        cy = float(geometry.get("cy") or geometry.get("y") or 0)
        r = float(geometry.get("radius") or 0)
        return math.hypot(x - cx, y - cy) <= r
    if roi_type in ("polygon", "freehand"):
        return _point_in_polygon(x, y, geometry.get("points") or [])
    if roi_type == "line":
        return False
    rx = float(geometry.get("x") or 0)
    ry = float(geometry.get("y") or 0)
    rw = float(geometry.get("width") or 0)
    rh = float(geometry.get("height") or 0)
    return rx <= x <= rx + rw and ry <= y <= ry + rh


def measure_region_stats(
    region: Any,
    *,
    geometry: dict[str, Any],
    roi_type: str,
    um_per_pixel: float | None,
) -> dict[str, Any]:
    """Compute intensity stats inside ROI mask from raw numpy region."""
    import numpy as np  # type: ignore

    arr = np.asarray(region)
    if arr.ndim > 2:
        arr = np.squeeze(arr)
    h, w = arr.shape[:2]
    ox = int(geometry.get("origin_x") or geometry.get("x") or 0)
    oy = int(geometry.get("origin_y") or geometry.get("y") or 0)

    mask_vals: list[float] = []
    for row in range(h):
        for col in range(w):
            gx = ox + col
            gy = oy + row
            if _point_in_geometry(gx, gy, geometry, roi_type):
                v = arr[row, col]
                mask_vals.append(float(v))

    area_px, perimeter_px = geometry_area_perimeter(geometry, roi_type)
    stats: dict[str, Any] = {
        "area_px2": round(area_px, 3),
        "perimeter_px": round(perimeter_px, 3),
        "pixel_count": len(mask_vals),
    }
    if um_per_pixel and um_per_pixel > 0:
        stats["area_um2"] = round(area_px * um_per_pixel ** 2, 3)
        stats["perimeter_um"] = round(perimeter_px * um_per_pixel, 3)
        stats["um_per_pixel"] = um_per_pixel

    if mask_vals:
        import numpy as np  # type: ignore

        vals = np.asarray(mask_vals, dtype=np.float64)
        stats.update(
            {
                "mean": round(float(vals.mean()), 4),
                "median": round(float(np.median(vals)), 4),
                "min": round(float(vals.min()), 4),
                "max": round(float(vals.max()), 4),
                "std": round(float(vals.std()), 4),
                "integrated_intensity": round(float(vals.sum()), 4),
            }
        )
    else:
        stats.update(
            {
                "mean": None,
                "median": None,
                "min": None,
                "max": None,
                "std": None,
                "integrated_intensity": None,
            }
        )
    return stats
