# LUMI image processing pipeline

Snakemake + SLURM whole-slide microscopy pipeline for the Färkkilä Lab CyCIF / multiplex imaging workflow.

**Entry point:** `scripts/run_pipeline.sh`

**In-app guide:** CyCIF → Imaging pipeline (overview diagram and step-by-step tabs).

## Quick start on LUMI

```bash
ssh <user>@lumi.csc.fi
cd /scratch/project_<ID>/image_processing/<dataset>/scripts
module load cray-python/3.11.7
source <snakemake_venv>/bin/activate
bash run_pipeline.sh --doctor
bash run_pipeline.sh
```

## Stages

1. Illumination correction (BaSiC) + Ashlar stitching — **human review gate**
2. Mesmer and/or StarDist segmentation — **human review gate**
3. Marker quantification + per-marker tophat filtering

## Data layout

Place raw `.rcpnl` tiles under `data/raw/<sample>/` and marker names in `data/channels_quantification.csv`.

See `MESMER_INDEX_AUDIT.md` and `SEGMENTATION_LUMI_OPTIMIZATION.md` for channel-index and GPU tuning notes.
