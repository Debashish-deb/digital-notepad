#!/usr/bin/env python3
"""Run the digitalization pipeline from the command line."""
import argparse
import json
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
LOGGER = logging.getLogger("run_digitalization")

# Add blueprint root to sys.path
BLUEPRINT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BLUEPRINT_ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the end-to-end data digitalization pipeline.")
    parser.add_argument(
        "--provider",
        type=str,
        default="local",
        help="Storage provider (e.g. local, pdrive_smb, datacloud_webdav)",
    )
    parser.add_argument(
        "--root",
        type=str,
        required=True,
        help="Root path to scan",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Maximum number of files to process",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run discovery only (no extraction or database writes)",
    )

    args = parser.parse_args()

    # Import the pipeline runner
    try:
        from app_skeleton.digitalization.ingestion_job import run_digitalization
    except ImportError as exc:
        LOGGER.error("Failed to import pipeline: %s", exc)
        return 1

    LOGGER.info("Starting digitalization pipeline")
    LOGGER.info("Provider: %s", args.provider)
    LOGGER.info("Root path: %s", args.root)
    LOGGER.info("Dry run: %s", args.dry_run)
    if args.max_files:
        LOGGER.info("Max files: %s", args.max_files)

    result = run_digitalization(
        provider=args.provider,
        root_path=args.root,
        dry_run=args.dry_run,
        max_files=args.max_files,
        created_by="cli",
    )

    print("\n--- Digitalization Result ---")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if result.get("status") == "failed":
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
