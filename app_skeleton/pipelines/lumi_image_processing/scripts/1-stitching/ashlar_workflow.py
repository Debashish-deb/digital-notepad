#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LUMI-compatible Ashlar wrapper.

Scientific behavior preserved from the local workstation script:
  ashlar <raw .rcpnl files> -o <sample>.ome.tif --pyramid --filter-sigma 1 -m 30
with optional BaSiC flat-field/dark-field profiles passed through --ffp/--dfp.
"""

import argparse
import os
import subprocess
from pathlib import Path

FILE_EXT = ".rcpnl"
ASHLAR_BIN = os.environ.get("ASHLAR_BIN", "ashlar")


def ashlar_call(files_to_stitch, output_path):
    cmd = [
        ASHLAR_BIN,
        *files_to_stitch,
        "-o", output_path,
        "--pyramid",
        "--filter-sigma", "1",
        "-m", "30",
    ]
    print("Running:", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def ashlar_call_illumination(files_to_stitch, output_path, flat_fields, dark_fields):
    cmd = [
        ASHLAR_BIN,
        *files_to_stitch,
        "-o", output_path,
        "--pyramid",
        "--filter-sigma", "1",
        "-m", "30",
        "--ffp", *flat_fields,
        "--dfp", *dark_fields,
    ]
    print("Running:", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def collect_files(folder):
    folder = Path(folder)
    files = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == FILE_EXT)

    if not files:
        raise RuntimeError(f"No {FILE_EXT} files found in {folder}")

    print("Files to stitch:", flush=True)
    for f in files:
        print(f"  {f}", flush=True)

    return [str(p) for p in files]


def collect_illumination(illum_folder):
    illum_folder = Path(illum_folder)
    if not illum_folder.is_dir():
        return None, None

    illum_files = sorted(p for p in illum_folder.iterdir() if p.is_file())

    flat_fields = [str(p) for p in illum_files if "-ffp" in p.name]
    dark_fields = [str(p) for p in illum_files if "-dfp" in p.name]

    if not flat_fields and not dark_fields:
        return None, None

    if len(flat_fields) != len(dark_fields):
        raise RuntimeError(
            f"Mismatch in illumination files in {illum_folder}: "
            f"{len(flat_fields)} flat-fields, {len(dark_fields)} dark-fields"
        )

    print("Flat field files:", flush=True)
    for f in flat_fields:
        print(f"  {f}", flush=True)

    print("Dark field files:", flush=True)
    for f in dark_fields:
        print(f"  {f}", flush=True)

    return flat_fields, dark_fields


def main():
    parser = argparse.ArgumentParser(description="Run Ashlar for one sample directory.")
    parser.add_argument("--input", required=True, help="Sample input directory containing .rcpnl files")
    parser.add_argument("--output", required=True, help="Root output directory")
    parser.add_argument("--illumination", required=False, help="Root illumination directory")
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_root = Path(args.output)
    sample_name = input_dir.name

    sample_output_dir = output_root / sample_name
    sample_output_dir.mkdir(parents=True, exist_ok=True)

    output_file = sample_output_dir / f"{sample_name}.ome.tif"

    print(f"Ashlar executable: {ASHLAR_BIN}", flush=True)
    print(f"Input directory  : {input_dir}", flush=True)
    print(f"Output directory : {sample_output_dir}", flush=True)
    print(f"Output file      : {output_file}", flush=True)

    files_to_stitch = collect_files(input_dir)

    if args.illumination:
        illum_folder = Path(args.illumination) / sample_name
        print(f"Illumination folder: {illum_folder}", flush=True)
        flat_fields, dark_fields = collect_illumination(illum_folder)

        if flat_fields and dark_fields:
            # Ashlar requires exactly one --ffp and one --dfp per input cycle
            # file. If the illumination folder has fewer (or more) cycles than
            # the raw input folder, ashlar fails partway through with a
            # confusing error. Surface the mismatch up front instead.
            if len(flat_fields) != len(files_to_stitch) or len(dark_fields) != len(files_to_stitch):
                raise RuntimeError(
                    f"Illumination/cycle count mismatch for sample {sample_name}: "
                    f"{len(files_to_stitch)} cycle file(s), "
                    f"{len(flat_fields)} flat-field file(s), "
                    f"{len(dark_fields)} dark-field file(s). "
                    "Ashlar requires exactly one -ffp and one -dfp per input cycle."
                )
            ashlar_call_illumination(files_to_stitch, str(output_file), flat_fields, dark_fields)
        else:
            print(f"WARNING: Illumination files not found for sample {sample_name}. Running without correction.", flush=True)
            ashlar_call(files_to_stitch, str(output_file))
    else:
        print("No illumination root provided. Running without correction.", flush=True)
        ashlar_call(files_to_stitch, str(output_file))

    print("Ashlar processing complete.", flush=True)


if __name__ == "__main__":
    main()
