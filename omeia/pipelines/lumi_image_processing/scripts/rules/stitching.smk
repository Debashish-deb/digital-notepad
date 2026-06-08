# rules/stitching.smk


def stitch_mem(wc, attempt):
    return auto_mem_mb(effective_stitch_size_gib(wc.sample), "stitch", attempt)


def stitch_runtime(wc, attempt):
    return auto_runtime(effective_stitch_size_gib(wc.sample), "stitch", attempt)


def stitch_threads(wc):
    return int(os.environ.get("STITCHING_THREADS", "4"))


rule stitching:
    input:
        raw=raw_inputs_for_wc,
        illum=illum_outputs_for_wc
    output:
        ome_tif=str(STITCHED_DIR / "{sample}" / "{sample}.ome.tif")
    params:
        sample="{sample}",
        input_dir=lambda wc: str(RAW_DIR / wc.sample),
        illum_dir=lambda wc: str(ILLUM_DIR / wc.sample),
        has_illumination=lambda wc, input: "1" if len(input.illum) > 0 else "0",
        log_file=lambda wc: str(LOG_ROOT / "stitching" / wc.sample / f"stitching_{wc.sample}.log"),
        sif_image=os.environ.get("SIF_IMAGE_STITCHING"),
        py_script=os.environ.get("PY_SCRIPT_STITCHING"),
        workflows_dir=str(BASE / "scripts" / "1-stitching"),
        stripe_count=os.environ.get("SEGMENTATION_STRIPE_COUNT", "4"),
        stripe_size=os.environ.get("SEGMENTATION_STRIPE_SIZE", "4M"),
        base=str(BASE),
    threads:
        stitch_threads
    resources:
        mem_mb=stitch_mem,
        runtime=stitch_runtime,
        cpus_per_task=stitch_threads,
        slurm_account=os.environ.get("SLURM_ACCOUNT", os.environ.get("PROJECT_ID", "")),
        slurm_partition="small"
    shell:
        r'''
        set -euo pipefail

        mkdir -p \
          "$(dirname "{output.ome_tif}")" \
          "$(dirname "{params.log_file}")"
        : > "{params.log_file}"

        {{
          [[ -f "{params.base}/scripts/lib/job_log_ui.sh" ]] && source "{params.base}/scripts/lib/job_log_ui.sh"

          if declare -F job_log_open >/dev/null 2>&1; then
              job_log_open \
                "Tile stitching (Ashlar)" \
                "Sample {params.sample}" \
                "Combining individual microscope tiles into one whole-slide image"
              log() {{ job_log "$@"; }}
              fail() {{ job_log_fail "$@"; exit 1; }}
          else
              log() {{ printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }}
              fail() {{ log "ERROR: $*"; exit 1; }}
          fi

          SAMPLE_NAME="{params.sample}"
          INPUT_DIR="{params.input_dir}"
          OUTPUT_FILE="{output.ome_tif}"
          ILLUM_DIR_HOST="{params.illum_dir}"
          HAS_ILLUMINATION="{params.has_illumination}"

          SIF_IMAGE="{params.sif_image}"
          PY_SCRIPT="{params.py_script}"
          WORKFLOWS_DIR="{params.workflows_dir}"

          THREADS="{threads}"

          SCRATCH_ROOT="${{LOCAL_SCRATCH:-/tmp}}/${{USER}}"
          SCRATCH_BASE="${{SCRATCH_ROOT}}/ashlar_${{SLURM_JOB_ID:-manual}}_${{SAMPLE_NAME}}"

          SCRATCH_INPUT_ROOT="${{SCRATCH_BASE}}/input"
          SCRATCH_INPUT="${{SCRATCH_INPUT_ROOT}}/${{SAMPLE_NAME}}"

          SCRATCH_ILLUM_ROOT="${{SCRATCH_BASE}}/illumination"
          SCRATCH_ILLUM="${{SCRATCH_ILLUM_ROOT}}/${{SAMPLE_NAME}}"

          SCRATCH_OUTPUT_ROOT="${{SCRATCH_BASE}}/output"
          SCRATCH_JAVA_SERVER="${{SCRATCH_BASE}}/java_server_fix"

          EXPECTED_OUTPUT="${{SCRATCH_OUTPUT_ROOT}}/${{SAMPLE_NAME}}/${{SAMPLE_NAME}}.ome.tif"
          TMP_OUTPUT="${{OUTPUT_FILE}}.tmp.$$"

          cleanup() {{
              rm -rf "${{SCRATCH_BASE}}"
          }}

          trap cleanup EXIT INT TERM

          [[ -d "${{INPUT_DIR}}" ]] || fail "Input directory not found: ${{INPUT_DIR}}"
          [[ -f "${{SIF_IMAGE}}" ]] || fail "Singularity image not found: ${{SIF_IMAGE}}"
          [[ -f "${{PY_SCRIPT}}" ]] || fail "Ashlar workflow script not found: ${{PY_SCRIPT}}"

          mkdir -p \
            "${{SCRATCH_INPUT}}" \
            "${{SCRATCH_ILLUM}}" \
            "${{SCRATCH_OUTPUT_ROOT}}" \
            "${{SCRATCH_JAVA_SERVER}}"

          log "Collecting raw .rcpnl files"
          mapfile -d '' FILES < <(find "${{INPUT_DIR}}" -maxdepth 1 -type f -iname "*.rcpnl" -print0 | sort -z)
          if [[ "${{#FILES[@]}}" -eq 0 ]]; then
              fail "No .rcpnl files found in ${{INPUT_DIR}}"
          fi
          log "Raw file count        : ${{#FILES[@]}}"

          log "Copying raw files to local scratch"
          for INPUT_PATH in "${{FILES[@]}}"; do
              cp -f "${{INPUT_PATH}}" "${{SCRATCH_INPUT}}/"
          done

          if [[ "${{HAS_ILLUMINATION}}" == "1" ]]; then
              log "Preparing illumination files"
              [[ -d "${{ILLUM_DIR_HOST}}" ]] || fail "Illumination directory missing after dependency build: ${{ILLUM_DIR_HOST}}"

              mapfile -d '' FFP_FILES < <(find "${{ILLUM_DIR_HOST}}" -maxdepth 1 -type f -name "*-ffp.tif" -print0 | sort -z)
              mapfile -d '' DFP_FILES < <(find "${{ILLUM_DIR_HOST}}" -maxdepth 1 -type f -name "*-dfp.tif" -print0 | sort -z)

              if [[ "${{#FFP_FILES[@]}}" -ne "${{#DFP_FILES[@]}}" ]]; then
                  fail "Illumination file mismatch: ${{#FFP_FILES[@]}} FFP vs ${{#DFP_FILES[@]}} DFP"
              fi

              if [[ "${{#FFP_FILES[@]}}" -eq 0 ]]; then
                  fail "No illumination files found in ${{ILLUM_DIR_HOST}}"
              fi

              for f in "${{FFP_FILES[@]}}" "${{DFP_FILES[@]}}"; do
                  cp -f "${{f}}" "${{SCRATCH_ILLUM}}/"
              done
          fi

          log "Preparing JVM compatibility path"
          REAL_LIBJVM="/opt/conda/envs/ashlar3/lib/jvm/lib/server/libjvm.so"
          LINKED_LIBJVM="${{SCRATCH_JAVA_SERVER}}/libjvm.so"
          ln -sf "${{REAL_LIBJVM}}" "${{LINKED_LIBJVM}}"

          export OMP_NUM_THREADS="${{THREADS}}"
          export OPENBLAS_NUM_THREADS=1
          export MKL_NUM_THREADS=1
          export NUMEXPR_NUM_THREADS=1

          log "Running Ashlar inside Singularity"
          singularity exec --cleanenv \
            --env JAVA_HOME="/opt/conda/envs/ashlar3/lib/jvm" \
            --env JDK_HOME="/opt/conda/envs/ashlar3/lib/jvm" \
            --env LD_LIBRARY_PATH="/opt/conda/envs/ashlar3/lib/server:/opt/conda/envs/ashlar3/lib/jvm/lib/server" \
            --env PATH="/opt/conda/envs/ashlar3/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
            --env ASHLAR_BIN="/opt/conda/envs/ashlar3/bin/ashlar" \
            --env OMP_NUM_THREADS="${{THREADS}}" \
            --env OPENBLAS_NUM_THREADS=1 \
            --env MKL_NUM_THREADS=1 \
            --env NUMEXPR_NUM_THREADS=1 \
            --bind "${{SCRATCH_BASE}}:${{SCRATCH_BASE}}" \
            --bind "${{WORKFLOWS_DIR}}:${{WORKFLOWS_DIR}}" \
            --bind "${{SCRATCH_JAVA_SERVER}}:/opt/conda/envs/ashlar3/lib/server" \
            "${{SIF_IMAGE}}" \
            /opt/conda/envs/ashlar3/bin/python "${{PY_SCRIPT}}" \
              --input "${{SCRATCH_INPUT}}" \
              --output "${{SCRATCH_OUTPUT_ROOT}}" \
              --illumination "${{SCRATCH_ILLUM_ROOT}}"

          [[ -s "${{EXPECTED_OUTPUT}}" ]] || fail "Expected output not found or empty: ${{EXPECTED_OUTPUT}}"

          log "Copying stitched OME-TIFF to final destination"
          if command -v lfs >/dev/null 2>&1; then
              rm -f "${{TMP_OUTPUT}}"
              lfs setstripe \
                --stripe-count "{params.stripe_count}" \
                --stripe-size "{params.stripe_size}" \
                "${{TMP_OUTPUT}}" >/dev/null 2>&1 || \
                log "WARNING: could not set Lustre striping on ${{TMP_OUTPUT}}"
          fi
          cp -f "${{EXPECTED_OUTPUT}}" "${{TMP_OUTPUT}}"
          mv "${{TMP_OUTPUT}}" "${{OUTPUT_FILE}}"

          if declare -F job_log_close_ok >/dev/null 2>&1; then
              job_log_close_ok "Stitched whole-slide image saved."
          else
              log "Job finished successfully"
          fi

        }} 2>&1 | tee -a "{params.log_file}"
        '''
