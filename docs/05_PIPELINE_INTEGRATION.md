# 05 — Pipeline Integration

## Canonical image workflow

```text
Raw images
 → BaSiC illumination correction
 → Ashlar stitching/registration
 → Mesmer or StarDist segmentation
 → Quantification
 → Filtered-marker workflow
 → Phenotyping
 → Spatial analysis
 → Feature matrices
 → Clinical/statistical/AI integration
```

## Every stage needs a manifest

Example:

```yaml
pipeline_run_code: imageproc_2026_06_02_001
pipeline_name: image_processing
pipeline_version: 1.0.0
git_commit: abc123
executor: snakemake_slurm
project_code: SPACE
dataset_name: tCyCIF_batch2
status: success
config:
  segmentation_method: mesmer
  nuclear_channel: 0
  marker_channel_file: data/channels_quantification.csv
inputs:
  - sample_code: S253_iOme
    file_role: raw_image
outputs:
  - sample_code: S253_iOme
    file_role: stitched_image
  - sample_code: S253_iOme
    file_role: nuclear_mask
  - sample_code: S253_iOme
    file_role: quantification_table
qc:
  - metric: cell_count
    value: 123456
```

## Output contract

Preferred logical outputs:

```text
processed/illumination/<sample>/*-ffp.tif
processed/illumination/<sample>/*-dfp.tif
processed/stitching/<sample>/<sample>.ome.tif
processed/segmentation/<method>/<sample>.ome.tif
processed/quantification/<method>/<sample>.parquet or .csv
processed/filtering/<method>/<marker>/<sample>...
processed/phenotyping/<method>/<sample>...
processed/spatial_features/<feature_set>/<sample>...
```

## tCyCIF integration details

Register:

- raw image file
- stitched image file
- segmentation mask
- quantification table
- filtered outputs
- channel map
- segmentation method
- quantification method
- phenotype logic
- QC metrics
- feature matrices

## Tribus / phenotyping integration

Store:

- logic file
- depth
- thresholds
- final labels
- confidence/probability if available
- UMAP/heatmap QC outputs
- accepted phenotype version
- reviewer notes

## SPACEstat / spatial analysis integration

Spatial features should be named and versioned.

Feature groups:

- cell abundance
- cell density
- marker intensity
- nearest-neighbor distance
- co-occurrence
- hotspot
- community
- component
- ROI matching
- tumor-stroma interface
- TLS/milky spot
- functional gradients

## GeoMx integration

Register:

- DCC files
- PKC file
- annotation Excel
- QC object
- normalized object
- batch-corrected object
- deconvolution results
- pathway scores
- DGE outputs
- ROI metadata
- ROI coordinates

## ROI/community harmonization

Support multiple integration strategies:

1. Directly match GeoMx ROIs to tCyCIF communities.
2. Use ROI-sized windows around spatial components.
3. Compare community labels versus ROI labels.
4. Store mismatch/caveat flags.

## Clinical curation integration

Clinical curation must output:

- curated table
- discarded table
- warning/missingness report
- endpoint definition file
- source column mapping
- curation version

Do not calculate PFS/PFI/OS without a documented endpoint definition.

## Analysis dataset contract

Every analysis-ready dataset must include:

- dataset code
- project
- entity level
- inclusion/exclusion criteria
- clinical variables
- feature list
- source feature matrices
- source pipeline runs
- row/column count
- QC status
