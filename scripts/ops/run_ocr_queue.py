"""OCR queue worker skeleton — processes platform.ocr_job rows when ENABLE_OCR=true."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

LOGGER = logging.getLogger(__name__)


def process_queue(*, limit: int = 10, dry_run: bool = False) -> dict:
    from app_skeleton.api.ocr.adapter import get_ocr_backend, ocr_enabled

    if not ocr_enabled():
        LOGGER.info("ENABLE_OCR=false — worker idle")
        return {"processed": 0, "skipped": "ocr_disabled"}

    backend = get_ocr_backend()
    if backend is None:
        LOGGER.warning("No OCR backend available")
        return {"processed": 0, "skipped": "no_backend"}

    LOGGER.info("OCR queue worker skeleton — would process up to %s jobs (dry_run=%s)", limit, dry_run)
    return {"processed": 0, "dry_run": dry_run, "status": "skeleton"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = process_queue(limit=args.limit, dry_run=args.dry_run)
    LOGGER.info("Result: %s", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
