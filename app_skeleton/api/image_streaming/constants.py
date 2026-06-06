"""Constants for image streaming APIs."""
from __future__ import annotations

IMAGE_EXTENSIONS = frozenset({".tif", ".tiff", ".ome.tif", ".ome.tiff"})
OME_TIFF_SUFFIXES = (".ome.tif", ".ome.tiff")

MAX_TILE_EDGE = 512
MAX_TILE_PIXELS = MAX_TILE_EDGE * MAX_TILE_EDGE
DEFAULT_THUMB_EDGE = 256
METADATA_ONLY_BYTES = 50 * 1024 * 1024  # 50 MB — defer full inspect until job runs

STREAMING_STATUS = frozenset({
    "unknown",
    "metadata_only",
    "ready",
    "thumbnail_pending",
    "thumbnail_ready",
    "tile_ready",
    "failed",
    "unsupported",
})

PROVIDER_MAP = {
    "local_database_mirror": "database-static",
    "database-static": "database-static",
    "projects-static": "projects-static",
    "projects": "projects-static",
    "csc-media": "csc-media",
}
