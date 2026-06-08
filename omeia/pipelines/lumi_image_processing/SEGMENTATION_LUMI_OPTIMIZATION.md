# Ada segmentation optimization for LUMI

## Decision

Use `small-g`, one GCD per image, and up to 32 concurrent images.

Mesmer and StarDist in this pipeline are single-process TensorFlow workloads.
Allocating extra GCDs to one rule does not make that rule faster. `standard-g`
allocates and bills a complete eight-GCD node, so it is only sensible after
the pipeline can keep all eight GCDs busy in one allocation.

The fast profile is therefore many `small-g` one-GCD jobs, not many
`standard-g` one-sample jobs. For 58 samples this creates roughly two waves at
the default cap of 32 concurrent jobs. To attempt a single wave, use
`MESMER_JOBS=58 MAX_GPU_JOBS=58 SEGMENTATION_JOB_CAP=58`, but expect heavier
queue pressure and much higher shared-filesystem I/O pressure.

If you intentionally want to test `standard-g`, set
`SLURM_PARTITION_GPU=standard-g` before launching the pipeline. Do this only
when the higher full-node billing and queue behavior are acceptable. The
current Snakemake layout submits one image per Slurm job, so `standard-g` does
not automatically pack eight samples into one node. A truly efficient
`standard-g` mode would need a separate full-node packing layer that launches
multiple samples inside one allocation and pins each worker to a different
GCD.

## Problems found

- A 150-200 GiB stitched file caused Mesmer to request up to eight GCDs and
  StarDist up to six GCDs, but both rules hid every allocated GCD except the
  first.
- Mesmer's configured batch size was ignored. Every 1024 x 1024 outer tile
  caused a separate `app.predict` call.
- Host-memory estimates used the size of the complete multichannel OME-TIFF,
  although segmentation reads only two channels for Mesmer or one for
  StarDist.
- Mesmer preprocessing retained avoidable whole-slide float32 copies.
- StarDist targeted only about 4.8 million pixels per inference tile, which is
  unnecessarily conservative for a 64 GiB LUMI GCD.
- `/tmp` was treated as local disk. On LUMI compute nodes it resides in RAM and
  counts against the Slurm memory allocation.
- Huge single-file outputs were created without an explicit Lustre stripe
  layout.

## Implemented profile

- Partition: `small-g`
- GCDs per image: `1`
- CPU threads per image: `8`
- Concurrent GPU images: `32`
- Mesmer outer tile batch: `4`, with automatic split-and-retry after GPU OOM
- StarDist target tile edge: `4096`, with two automatic smaller-tile retries
- Lustre output striping: 4 OSTs with 4 MiB stripes
- Mesmer walltime for a 200 GiB file: 12 hours on the first attempt
- StarDist walltime for a 200 GiB file: 10 hours on the first attempt

For a 200 GiB, 40-channel OME-TIFF, the new first-attempt estimates are about
104,000 MiB for Mesmer and 72,000 MiB for StarDist. The old estimates were
480,000 MiB and 360,000 MiB. Actual peak RSS is now written to each worker log,
so these values can be tightened after representative LUMI runs.

## Expected effect

Mesmer now makes one outer prediction call per four tissue tiles instead of
one call per tile. StarDist uses roughly 3.5 times larger inference tiles than
the old heuristic. End-to-end acceleration depends on how much time is spent
in TIFF I/O and DeepTile mask stitching, so a measured LUMI run is required;
the code does not claim a fixed speedup.

The segmentation model, MPP, input channels, preprocessing values, overlap,
Mesmer compartments, StarDist model thresholds, and DeepTile mask-stitching
algorithm remain unchanged.

## Storage

LUMI-G has no compute-node local disk. Keep `LOCAL_SCRATCH` on shared project
scratch or project flash, never on `/tmp` for large data. For repeated
segmentation of these 150-200 GiB images, LUMI-F can reduce I/O waiting, but it
is billed at three times the storage rate of LUMI-P. Existing stitched files
with stripe count 1 are not automatically redistributed; newly stitched files
and new masks receive the configured stripe layout.

## Tuning after one representative run

Read the `TIMING ...` and `Peak RSS GiB` lines in the Mesmer or StarDist log.

- If Mesmer inference dominates and no OOM retry appears, test
  `MESMER_BATCH_SIZE=8` on one image.
- If Mesmer stitching dominates, additional GPU allocation will not help.
- If peak RSS is comfortably below the request, set `MESMER_MEM_MB` or
  `STARDIST_MEM_MB` just above the measured peak, preferably near a 64 GiB
  billing boundary.
- If TIFF read/write dominates, place the stitched working set temporarily on
  LUMI-F and compare one image before moving the whole dataset.

## Primary references

- [LUMI Slurm partitions](https://docs.lumi-supercomputer.eu/runjobs/scheduled-jobs/partitions/)
- [LUMI GPU billing policy](https://docs.lumi-supercomputer.eu/runjobs/lumi_env/billing/)
- [LUMI-G hardware](https://docs.lumi-supercomputer.eu/hardware/lumig/)
- [LUMI batch jobs and `/tmp` memory behavior](https://docs.lumi-supercomputer.eu/runjobs/scheduled-jobs/batch-job/)
- [LUMI-F flash storage](https://docs.lumi-supercomputer.eu/storage/parallel-filesystems/lumif/)
- [LUMI Lustre striping](https://docs.lumi-supercomputer.eu/storage/parallel-filesystems/lustre/)
- [Official StarDist source](https://github.com/stardist/stardist)
