# rules/quantification.smk


def quant_mem(wc, attempt):
    gib = file_size_gib(str(STITCHED_DIR / wc.sample / f"{wc.sample}.ome.tif"))
    return auto_mem_mb(gib, "quant", attempt)


def quant_runtime(wc, attempt):
    gib = file_size_gib(str(STITCHED_DIR / wc.sample / f"{wc.sample}.ome.tif"))
    return auto_runtime(gib, "quant", attempt)


def quant_threads(wc):
    return int(os.environ.get("QUANTIFICATION_THREADS", "4"))


rule quantify_nuclear_mesmer:
    input:
        image=str(STITCHED_DIR / "{sample}" / "{sample}.ome.tif"),
        mask=segmentation_mask("mesmer", "{sample}", "nuclear")
    output:
        csv=quant_csv("mesmer", "{sample}")
    params:
        sample="{sample}",
        method="mesmer",
        log_file=lambda wc: str(LOG_ROOT / "quantification" / "mesmer" / wc.sample / f"quant_mesmer_{wc.sample}.log"),
        sif_image=os.environ.get("SIF_IMAGE_QUANTIFICATION"),
        py_script=os.environ.get("PY_SCRIPT_QUANTIFICATION"),
        channel_names_file=lambda wc: str(CHANNEL_NAMES_FILE),
        base=str(BASE),
        container_base="/work",
        python_bin=os.environ.get("QUANTIFICATION_PYTHON_BIN", "/opt/conda/envs/quantification/bin/python"),
    threads:
        quant_threads
    resources:
        mem_mb=quant_mem,
        runtime=quant_runtime,
        cpus_per_task=quant_threads,
        slurm_account=os.environ.get("SLURM_ACCOUNT", os.environ.get("PROJECT_ID", "")),
        slurm_partition="small"
    shell:
        r'''
        set -euo pipefail

        mkdir -p \
          "$(dirname "{output.csv}")" \
          "$(dirname "{params.log_file}")"
        : > "{params.log_file}"

        {{
          [[ -f "{params.base}/scripts/lib/job_log_ui.sh" ]] && source "{params.base}/scripts/lib/job_log_ui.sh"

          if declare -F job_log_open >/dev/null 2>&1; then
              log() {{ job_log "$@"; }}
              fail() {{ job_log_fail "$@"; exit 1; }}
          else
              log() {{ printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }}
              fail() {{ log "ERROR: $*"; exit 1; }}
          fi

          SAMPLE_NAME="{params.sample}"
          METHOD="{params.method}"

          IMAGE_FILE="{input.image}"
          MASK_FILE="{input.mask}"
          OUTPUT_CSV="{output.csv}"
          OUTPUT_DIR="$(dirname "${{OUTPUT_CSV}}")"
          CHANNEL_FILE="{params.channel_names_file}"

          SIF_IMAGE="{params.sif_image}"
          PY_SCRIPT="{params.py_script}"
          THREADS="{threads}"

          SAFE_SAMPLE_NAME="$(echo "${{SAMPLE_NAME}}" | tr '/ :' '___')"
          SCRATCH_ROOT="${{LOCAL_SCRATCH:-/tmp}}/${{USER}}"
          TMPDIR_BASE="${{SCRATCH_ROOT}}/quant_${{METHOD}}_${{SLURM_JOB_ID:-manual}}_${{SAFE_SAMPLE_NAME}}"

          cleanup() {{
              rm -rf "${{TMPDIR_BASE}}" || true
          }}

          trap cleanup EXIT INT TERM

          if declare -F job_log_open >/dev/null 2>&1; then
              job_log_open \
                "Marker quantification (nuclei)" \
                "Sample ${{SAMPLE_NAME}} · method ${{METHOD}}" \
                "Measuring marker intensity inside each nucleus"
          else
              log "Nuclear quantification job started — sample ${{SAMPLE_NAME}}"
          fi

          [[ -f "${{IMAGE_FILE}}" ]] || fail "Image file not found: ${{IMAGE_FILE}}"
          [[ -f "${{MASK_FILE}}" ]] || fail "Mask file not found: ${{MASK_FILE}}"
          [[ -f "${{CHANNEL_FILE}}" ]] || fail "Channel names file not found: ${{CHANNEL_FILE}}"
          [[ -f "${{SIF_IMAGE}}" ]] || fail "Container not found: ${{SIF_IMAGE}}"
          [[ -f "${{PY_SCRIPT}}" ]] || fail "Quantification script not found: ${{PY_SCRIPT}}"

          if [[ -s "${{OUTPUT_CSV}}" ]]; then
              log "Output already exists. Job complete."
              exit 0
          fi

          rm -f "${{OUTPUT_CSV}}"

          mkdir -p "${{TMPDIR_BASE}}"

          IMAGE_REL="$(realpath --relative-to="{params.base}" "${{IMAGE_FILE}}")"
          MASK_REL="$(realpath --relative-to="{params.base}" "${{MASK_FILE}}")"
          SCRIPT_REL="$(realpath --relative-to="{params.base}" "${{PY_SCRIPT}}")"
          OUTDIR_REL="$(realpath --relative-to="{params.base}" "${{OUTPUT_DIR}}")"
          CHANNEL_REL="$(realpath --relative-to="{params.base}" "${{CHANNEL_FILE}}")"

          IMAGE_CONTAINER="{params.container_base}/${{IMAGE_REL}}"
          MASK_CONTAINER="{params.container_base}/${{MASK_REL}}"
          SCRIPT_CONTAINER="{params.container_base}/${{SCRIPT_REL}}"
          OUTPUT_DIR_CONTAINER="{params.container_base}/${{OUTDIR_REL}}"
          CHANNEL_CONTAINER="{params.container_base}/${{CHANNEL_REL}}"

          log "Running quantification inside Singularity"

          singularity exec \
            --bind "{params.base}:{params.container_base}" \
            --bind "${{TMPDIR_BASE}}:/tmp" \
            --env PYTHONUNBUFFERED="1" \
            --env TMPDIR="/tmp" \
            --env TMP="/tmp" \
            --env TEMP="/tmp" \
            --env OMP_NUM_THREADS="1" \
            --env OPENBLAS_NUM_THREADS="1" \
            --env MKL_NUM_THREADS="1" \
            --env NUMEXPR_NUM_THREADS="1" \
            --env VECLIB_MAXIMUM_THREADS="1" \
            "${{SIF_IMAGE}}" \
            "{params.python_bin}" -u "${{SCRIPT_CONTAINER}}" \
              --image-file "${{IMAGE_CONTAINER}}" \
              --mask-file "${{MASK_CONTAINER}}" \
              --sample-name "${{SAMPLE_NAME}}.partial.$$" \
              -o "${{OUTPUT_DIR_CONTAINER}}" \
              -ch "${{CHANNEL_CONTAINER}}" \
              -c "${{THREADS}}" \
              --output-suffix "_nuclear"

          # Atomic publish: python wrote <SAMPLE>.partial.<PID>_nuclear.csv; rename into
          # place only after a successful exit. Prevents resume-skipping of partial files.
          PARTIAL_CSV="${{OUTPUT_DIR}}/${{SAMPLE_NAME}}.partial.$$_nuclear.csv"
          [[ -s "${{PARTIAL_CSV}}" ]] || fail "Expected partial CSV not found or empty: ${{PARTIAL_CSV}}"
          mv -f "${{PARTIAL_CSV}}" "${{OUTPUT_CSV}}"

          [[ -s "${{OUTPUT_CSV}}" ]] || fail "Expected output CSV not found or empty: ${{OUTPUT_CSV}}"

          if declare -F job_log_close_ok >/dev/null 2>&1; then
              job_log_close_ok "Quantification table saved."
          else
              log "Job finished successfully"
          fi

        }} 2>&1 | tee -a "{params.log_file}"
        '''


rule quantify_whole_cell_mesmer:
    input:
        image=str(STITCHED_DIR / "{sample}" / "{sample}.ome.tif"),
        mask=segmentation_mask("mesmer", "{sample}", "whole-cell")
    output:
        csv=quant_csv("mesmer", "{sample}", "whole-cell")
    params:
        sample="{sample}",
        method="mesmer",
        log_file=lambda wc: str(LOG_ROOT / "quantification" / "mesmer" / wc.sample / f"quant_whole_cell_mesmer_{wc.sample}.log"),
        sif_image=os.environ.get("SIF_IMAGE_QUANTIFICATION"),
        py_script=os.environ.get("PY_SCRIPT_QUANTIFICATION"),
        channel_names_file=lambda wc: str(CHANNEL_NAMES_FILE),
        base=str(BASE),
        container_base="/work",
        python_bin=os.environ.get("QUANTIFICATION_PYTHON_BIN", "/opt/conda/envs/quantification/bin/python"),
    threads:
        quant_threads
    resources:
        mem_mb=quant_mem,
        runtime=quant_runtime,
        cpus_per_task=quant_threads,
        slurm_account=os.environ.get("SLURM_ACCOUNT", os.environ.get("PROJECT_ID", "")),
        slurm_partition="small"
    shell:
        r'''
        set -euo pipefail

        mkdir -p \
          "$(dirname "{output.csv}")" \
          "$(dirname "{params.log_file}")"
        : > "{params.log_file}"

        {{
          [[ -f "{params.base}/scripts/lib/job_log_ui.sh" ]] && source "{params.base}/scripts/lib/job_log_ui.sh"

          if declare -F job_log_open >/dev/null 2>&1; then
              log() {{ job_log "$@"; }}
              fail() {{ job_log_fail "$@"; exit 1; }}
          else
              log() {{ printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }}
              fail() {{ log "ERROR: $*"; exit 1; }}
          fi

          SAMPLE_NAME="{params.sample}"
          METHOD="{params.method}"

          IMAGE_FILE="{input.image}"
          MASK_FILE="{input.mask}"
          OUTPUT_CSV="{output.csv}"
          OUTPUT_DIR="$(dirname "${{OUTPUT_CSV}}")"
          CHANNEL_FILE="{params.channel_names_file}"

          SIF_IMAGE="{params.sif_image}"
          PY_SCRIPT="{params.py_script}"
          THREADS="{threads}"

          SAFE_SAMPLE_NAME="$(echo "${{SAMPLE_NAME}}" | tr '/ :' '___')"
          SCRATCH_ROOT="${{LOCAL_SCRATCH:-/tmp}}/${{USER}}"
          TMPDIR_BASE="${{SCRATCH_ROOT}}/quant_wc_${{METHOD}}_${{SLURM_JOB_ID:-manual}}_${{SAFE_SAMPLE_NAME}}"

          cleanup() {{
              rm -rf "${{TMPDIR_BASE}}" || true
          }}

          trap cleanup EXIT INT TERM

          if declare -F job_log_open >/dev/null 2>&1; then
              job_log_open \
                "Marker quantification (whole cell)" \
                "Sample ${{SAMPLE_NAME}} · method ${{METHOD}}" \
                "Measuring marker intensity inside each whole cell"
          else
              log "Whole-cell quantification job started — sample ${{SAMPLE_NAME}}"
          fi

          [[ -f "${{IMAGE_FILE}}" ]] || fail "Image file not found: ${{IMAGE_FILE}}"
          [[ -f "${{MASK_FILE}}" ]] || fail "Mask file not found: ${{MASK_FILE}}"
          [[ -f "${{CHANNEL_FILE}}" ]] || fail "Channel names file not found: ${{CHANNEL_FILE}}"
          [[ -f "${{SIF_IMAGE}}" ]] || fail "Container not found: ${{SIF_IMAGE}}"
          [[ -f "${{PY_SCRIPT}}" ]] || fail "Quantification script not found: ${{PY_SCRIPT}}"

          if [[ -s "${{OUTPUT_CSV}}" ]]; then
              log "Output already exists. Job complete."
              exit 0
          fi

          rm -f "${{OUTPUT_CSV}}"

          mkdir -p "${{TMPDIR_BASE}}"

          IMAGE_REL="$(realpath --relative-to="{params.base}" "${{IMAGE_FILE}}")"
          MASK_REL="$(realpath --relative-to="{params.base}" "${{MASK_FILE}}")"
          SCRIPT_REL="$(realpath --relative-to="{params.base}" "${{PY_SCRIPT}}")"
          OUTDIR_REL="$(realpath --relative-to="{params.base}" "${{OUTPUT_DIR}}")"
          CHANNEL_REL="$(realpath --relative-to="{params.base}" "${{CHANNEL_FILE}}")"

          IMAGE_CONTAINER="{params.container_base}/${{IMAGE_REL}}"
          MASK_CONTAINER="{params.container_base}/${{MASK_REL}}"
          SCRIPT_CONTAINER="{params.container_base}/${{SCRIPT_REL}}"
          OUTPUT_DIR_CONTAINER="{params.container_base}/${{OUTDIR_REL}}"
          CHANNEL_CONTAINER="{params.container_base}/${{CHANNEL_REL}}"

          log "Running quantification inside Singularity"

          singularity exec \
            --bind "{params.base}:{params.container_base}" \
            --bind "${{TMPDIR_BASE}}:/tmp" \
            --env PYTHONUNBUFFERED="1" \
            --env TMPDIR="/tmp" \
            --env TMP="/tmp" \
            --env TEMP="/tmp" \
            --env OMP_NUM_THREADS="1" \
            --env OPENBLAS_NUM_THREADS="1" \
            --env MKL_NUM_THREADS="1" \
            --env NUMEXPR_NUM_THREADS="1" \
            --env VECLIB_MAXIMUM_THREADS="1" \
            "${{SIF_IMAGE}}" \
            "{params.python_bin}" -u "${{SCRIPT_CONTAINER}}" \
              --image-file "${{IMAGE_CONTAINER}}" \
              --mask-file "${{MASK_CONTAINER}}" \
              --sample-name "${{SAMPLE_NAME}}.partial.$$" \
              -o "${{OUTPUT_DIR_CONTAINER}}" \
              -ch "${{CHANNEL_CONTAINER}}" \
              -c "${{THREADS}}" \
              --output-suffix "_whole_cell"

          # Atomic publish.
          PARTIAL_CSV="${{OUTPUT_DIR}}/${{SAMPLE_NAME}}.partial.$$_whole_cell.csv"
          [[ -s "${{PARTIAL_CSV}}" ]] || fail "Expected partial CSV not found or empty: ${{PARTIAL_CSV}}"
          mv -f "${{PARTIAL_CSV}}" "${{OUTPUT_CSV}}"

          [[ -s "${{OUTPUT_CSV}}" ]] || fail "Expected output CSV not found or empty: ${{OUTPUT_CSV}}"

          if declare -F job_log_close_ok >/dev/null 2>&1; then
              job_log_close_ok "Quantification table saved."
          else
              log "Job finished successfully"
          fi

        }} 2>&1 | tee -a "{params.log_file}"
        '''


rule quantify_nuclear_stardist:
    input:
        image=str(STITCHED_DIR / "{sample}" / "{sample}.ome.tif"),
        mask=segmentation_mask("stardist", "{sample}")
    output:
        csv=quant_csv("stardist", "{sample}")
    params:
        sample="{sample}",
        method="stardist",
        log_file=lambda wc: str(LOG_ROOT / "quantification" / "stardist" / wc.sample / f"quant_stardist_{wc.sample}.log"),
        sif_image=os.environ.get("SIF_IMAGE_QUANTIFICATION"),
        py_script=os.environ.get("PY_SCRIPT_QUANTIFICATION"),
        channel_names_file=lambda wc: str(CHANNEL_NAMES_FILE),
        base=str(BASE),
        container_base="/work",
        python_bin=os.environ.get("QUANTIFICATION_PYTHON_BIN", "/opt/conda/envs/quantification/bin/python"),
    threads:
        quant_threads
    resources:
        mem_mb=quant_mem,
        runtime=quant_runtime,
        cpus_per_task=quant_threads,
        slurm_account=os.environ.get("SLURM_ACCOUNT", os.environ.get("PROJECT_ID", "")),
        slurm_partition="small"
    shell:
        r'''
        set -euo pipefail

        mkdir -p \
          "$(dirname "{output.csv}")" \
          "$(dirname "{params.log_file}")"
        : > "{params.log_file}"

        {{
          [[ -f "{params.base}/scripts/lib/job_log_ui.sh" ]] && source "{params.base}/scripts/lib/job_log_ui.sh"

          if declare -F job_log_open >/dev/null 2>&1; then
              log() {{ job_log "$@"; }}
              fail() {{ job_log_fail "$@"; exit 1; }}
          else
              log() {{ printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }}
              fail() {{ log "ERROR: $*"; exit 1; }}
          fi

          SAMPLE_NAME="{params.sample}"
          METHOD="{params.method}"

          IMAGE_FILE="{input.image}"
          MASK_FILE="{input.mask}"
          OUTPUT_CSV="{output.csv}"
          OUTPUT_DIR="$(dirname "${{OUTPUT_CSV}}")"
          CHANNEL_FILE="{params.channel_names_file}"

          SIF_IMAGE="{params.sif_image}"
          PY_SCRIPT="{params.py_script}"
          THREADS="{threads}"

          SAFE_SAMPLE_NAME="$(echo "${{SAMPLE_NAME}}" | tr '/ :' '___')"
          SCRATCH_ROOT="${{LOCAL_SCRATCH:-/tmp}}/${{USER}}"
          TMPDIR_BASE="${{SCRATCH_ROOT}}/quant_${{METHOD}}_${{SLURM_JOB_ID:-manual}}_${{SAFE_SAMPLE_NAME}}"

          cleanup() {{
              rm -rf "${{TMPDIR_BASE}}" || true
          }}

          trap cleanup EXIT INT TERM

          if declare -F job_log_open >/dev/null 2>&1; then
              job_log_open \
                "Marker quantification (nuclei)" \
                "Sample ${{SAMPLE_NAME}} · method ${{METHOD}}" \
                "Measuring marker intensity inside each nucleus"
          else
              log "Nuclear quantification job started — sample ${{SAMPLE_NAME}}"
          fi

          [[ -f "${{IMAGE_FILE}}" ]] || fail "Image file not found: ${{IMAGE_FILE}}"
          [[ -f "${{MASK_FILE}}" ]] || fail "Mask file not found: ${{MASK_FILE}}"
          [[ -f "${{CHANNEL_FILE}}" ]] || fail "Channel names file not found: ${{CHANNEL_FILE}}"
          [[ -f "${{SIF_IMAGE}}" ]] || fail "Container not found: ${{SIF_IMAGE}}"
          [[ -f "${{PY_SCRIPT}}" ]] || fail "Quantification script not found: ${{PY_SCRIPT}}"

          if [[ -s "${{OUTPUT_CSV}}" ]]; then
              log "Output already exists. Job complete."
              exit 0
          fi

          rm -f "${{OUTPUT_CSV}}"

          mkdir -p "${{TMPDIR_BASE}}"

          IMAGE_REL="$(realpath --relative-to="{params.base}" "${{IMAGE_FILE}}")"
          MASK_REL="$(realpath --relative-to="{params.base}" "${{MASK_FILE}}")"
          SCRIPT_REL="$(realpath --relative-to="{params.base}" "${{PY_SCRIPT}}")"
          OUTDIR_REL="$(realpath --relative-to="{params.base}" "${{OUTPUT_DIR}}")"
          CHANNEL_REL="$(realpath --relative-to="{params.base}" "${{CHANNEL_FILE}}")"

          IMAGE_CONTAINER="{params.container_base}/${{IMAGE_REL}}"
          MASK_CONTAINER="{params.container_base}/${{MASK_REL}}"
          SCRIPT_CONTAINER="{params.container_base}/${{SCRIPT_REL}}"
          OUTPUT_DIR_CONTAINER="{params.container_base}/${{OUTDIR_REL}}"
          CHANNEL_CONTAINER="{params.container_base}/${{CHANNEL_REL}}"

          log "Running quantification inside Singularity"

          singularity exec \
            --bind "{params.base}:{params.container_base}" \
            --bind "${{TMPDIR_BASE}}:/tmp" \
            --env PYTHONUNBUFFERED="1" \
            --env TMPDIR="/tmp" \
            --env TMP="/tmp" \
            --env TEMP="/tmp" \
            --env OMP_NUM_THREADS="1" \
            --env OPENBLAS_NUM_THREADS="1" \
            --env MKL_NUM_THREADS="1" \
            --env NUMEXPR_NUM_THREADS="1" \
            --env VECLIB_MAXIMUM_THREADS="1" \
            "${{SIF_IMAGE}}" \
            "{params.python_bin}" -u "${{SCRIPT_CONTAINER}}" \
              --image-file "${{IMAGE_CONTAINER}}" \
              --mask-file "${{MASK_CONTAINER}}" \
              --sample-name "${{SAMPLE_NAME}}.partial.$$" \
              -o "${{OUTPUT_DIR_CONTAINER}}" \
              -ch "${{CHANNEL_CONTAINER}}" \
              -c "${{THREADS}}" \
              --output-suffix "_nuclear"

          # Atomic publish: python wrote <SAMPLE>.partial.<PID>_nuclear.csv.
          PARTIAL_CSV="${{OUTPUT_DIR}}/${{SAMPLE_NAME}}.partial.$$_nuclear.csv"
          [[ -s "${{PARTIAL_CSV}}" ]] || fail "Expected partial CSV not found or empty: ${{PARTIAL_CSV}}"
          mv -f "${{PARTIAL_CSV}}" "${{OUTPUT_CSV}}"

          [[ -s "${{OUTPUT_CSV}}" ]] || fail "Expected output CSV not found or empty: ${{OUTPUT_CSV}}"

          if declare -F job_log_close_ok >/dev/null 2>&1; then
              job_log_close_ok "Quantification table saved."
          else
              log "Job finished successfully"
          fi

        }} 2>&1 | tee -a "{params.log_file}"
        '''

