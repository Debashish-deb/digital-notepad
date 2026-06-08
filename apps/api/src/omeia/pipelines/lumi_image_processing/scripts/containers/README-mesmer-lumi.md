# Mesmer LUMI ROCm Container

Build from this directory so the `%files` path resolves correctly:

```bash
cd /path/to/ada/scripts/containers
sudo singularity build mesmer-lumi-rocm63.sif mesmer-lumi-rocm63.def
```

With Apptainer:

```bash
cd /path/to/ada/scripts/containers
sudo apptainer build mesmer-lumi-rocm63.sif mesmer-lumi-rocm63.def
```

The build context must contain both:

```text
mesmer-lumi-rocm63.def
deepcell-tf/
└── deepcell-tf/
    ├── setup.py
    └── deepcell/
```

The image deliberately uses AMD's ROCm TensorFlow base and installs DeepCell
with `--no-deps`. This prevents pip from replacing `tensorflow-rocm` with CPU
TensorFlow.

Use the `-dev` ROCm TensorFlow base from the supplied definition. The matching
`-runtime` image does not provide an importable TensorFlow installation.

After building, upload the image to LUMI:

```bash
scp mesmer-lumi-rocm63.sif \
  debdebas@lumi.csc.fi:/projappl/project_462001415/envs/
```

Basic metadata test:

```bash
singularity test mesmer-lumi-rocm63.sif
```

The final GPU prediction test must be run on a LUMI GPU allocation. Import
success alone is insufficient.
