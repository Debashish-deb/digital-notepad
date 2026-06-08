# OMEIA imaging worker — scientific imaging stack in Docker.
# Basic TIFF streaming only needs tifffile+imagecodecs on the API host.
#
# Build:
#   docker compose --profile imaging build imaging-worker
# Slim (no napari GUI):
#   IMAGING_INCLUDE_NAPARI=0 docker compose --profile imaging build imaging-worker
#
# CycIF packages (bioformats2raw, raw2ometiff, ashlar) install only on linux/amd64.
# On Apple Silicon (linux-aarch64) build succeeds with core stack; build on x86 Linux
# workstation for the full CycIF conda packages.

FROM condaforge/mambaforge:latest

ARG IMAGING_INCLUDE_NAPARI=1
ARG TARGETARCH
ENV PYTHONUNBUFFERED=1
ENV MAMBA_NO_LOW_SPEED_LIMIT=1

WORKDIR /opt/omeia

COPY docker/imaging-worker/environment-core.yml /tmp/environment-core.yml
COPY docker/imaging-worker/environment-cycif-amd64.yml /tmp/environment-cycif-amd64.yml

RUN if [ "$IMAGING_INCLUDE_NAPARI" = "0" ]; then \
      grep -v -E '^\s*-\s*(napari|pyqt)\s*$' /tmp/environment-core.yml > /tmp/environment.slim.yml; \
    else \
      cp /tmp/environment-core.yml /tmp/environment.slim.yml; \
    fi \
 && mamba env create -f /tmp/environment.slim.yml \
 && mamba clean -afy

# bioformats2raw / raw2ometiff / ashlar are not published for linux-aarch64 on conda-forge.
RUN if [ "$TARGETARCH" = "amd64" ]; then \
      echo "Installing CycIF conda packages for amd64..." \
      && mamba env update -n omeia-imaging -f /tmp/environment-cycif-amd64.yml \
      && mamba clean -afy; \
    else \
      echo "Skipping CycIF conda packages on ${TARGETARCH} (available on linux/amd64 only)"; \
    fi

ENV PATH=/opt/conda/envs/omeia-imaging/bin:$PATH

COPY omeia/api/imaging_capabilities.py /opt/omeia/imaging_capabilities.py
COPY docker/imaging-worker/healthcheck.py /opt/omeia/healthcheck.py

CMD ["python", "/opt/omeia/healthcheck.py"]
