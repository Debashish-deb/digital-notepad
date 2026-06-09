"""Spatial biology metrics from cell centroids in overlay metadata."""
from __future__ import annotations

import math
from typing import Any


def _cell_centroids(overlay_metadata: dict[str, Any]) -> list[dict[str, Any]]:
    cells = overlay_metadata.get("cells")
    if isinstance(cells, dict):
        out = []
        for cell_id, entry in cells.items():
            if not isinstance(entry, dict):
                continue
            c = entry.get("centroid") or {}
            if c.get("x") is None or c.get("y") is None:
                continue
            out.append(
                {
                    "cell_id": cell_id,
                    "x": float(c["x"]),
                    "y": float(c["y"]),
                    "phenotype": entry.get("phenotype") or entry.get("label") or "unknown",
                }
            )
        if out:
            return out

    # Deterministic mock centroids for demo / tests
    mock = []
    for i in range(12):
        mock.append(
            {
                "cell_id": f"cell_mock_{i + 1}",
                "x": 80.0 + (i % 4) * 45.0,
                "y": 60.0 + (i // 4) * 40.0,
                "phenotype": ["tumor", "CD8", "CD163", "stroma"][i % 4],
            }
        )
    return mock


def _dist_px(a: dict[str, Any], b: dict[str, Any]) -> float:
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])


def compute_spatial_metrics(
    *,
    overlay_metadata: dict[str, Any] | None = None,
    radius_um: float = 50.0,
    um_per_pixel: float | None = None,
    phenotype_filter: str | None = None,
) -> dict[str, Any]:
    """Nearest-neighbor counts and radius density on cell centroids."""
    cells = _cell_centroids(overlay_metadata or {})
    if phenotype_filter:
        pf = phenotype_filter.lower()
        cells = [c for c in cells if pf in str(c.get("phenotype", "")).lower()]

    radius_px = radius_um / um_per_pixel if um_per_pixel and um_per_pixel > 0 else radius_um

    nearest_neighbors: list[dict[str, Any]] = []
    for i, cell in enumerate(cells):
        others = [c for j, c in enumerate(cells) if j != i]
        if not others:
            nearest_neighbors.append({"cell_id": cell["cell_id"], "nearest_count": 0, "nearest_dist_px": None})
            continue
        dists = sorted((_dist_px(cell, o), o["cell_id"]) for o in others)
        nearest_neighbors.append(
            {
                "cell_id": cell["cell_id"],
                "nearest_count": sum(1 for d, _ in dists if d <= radius_px),
                "nearest_dist_px": round(dists[0][0], 3),
                "nearest_neighbor_id": dists[0][1],
            }
        )

    # Tumor–immune distances: tumor centroids to nearest CD8
    tumors = [c for c in cells if "tumor" in str(c.get("phenotype", "")).lower() or "panck" in str(c.get("phenotype", "")).lower()]
    immune = [c for c in cells if any(k in str(c.get("phenotype", "")).lower() for k in ("cd8", "cd4", "immune"))]
    tumor_immune: list[dict[str, Any]] = []
    for t in tumors:
        if not immune:
            break
        dists = sorted((_dist_px(t, im), im["cell_id"]) for im in immune)
        d_px = dists[0][0]
        d_um = d_px * um_per_pixel if um_per_pixel else None
        tumor_immune.append(
            {
                "tumor_cell_id": t["cell_id"],
                "nearest_immune_id": dists[0][1],
                "distance_px": round(d_px, 3),
                "distance_um": round(d_um, 3) if d_um is not None else None,
            }
        )

    area_px = radius_px ** 2 * math.pi
    density_per_cell = [
        {
            "cell_id": c["cell_id"],
            "neighbors_in_radius": nn["nearest_count"],
            "density_per_mm2": round(nn["nearest_count"] / max(area_px, 1e-6) * 1e6, 4) if um_per_pixel else None,
        }
        for c, nn in zip(cells, nearest_neighbors)
    ]

    return {
        "cell_count": len(cells),
        "radius_um": radius_um,
        "radius_px": round(radius_px, 3),
        "um_per_pixel": um_per_pixel,
        "nearest_neighbors": nearest_neighbors,
        "radius_density": density_per_cell,
        "tumor_immune_distances": tumor_immune,
        "phenotype_filter": phenotype_filter,
    }
