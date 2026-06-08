# rules/stardist.smk

def stardist_mem(wc, attempt):
    gib = file_size_gib(str(STITCHED_DIR / wc.sample / f"{wc.sample}.ome.tif"))
    return auto_mem_mb(gib, "stardist", attempt)


def stardist_runtime(wc, attempt):
    gib = file_size_gib(str(STITCHED_DIR / wc.sample / f"{wc.sample}.ome.tif"))
    return auto_runtime(gib, "stardist", attempt)


def stardist_gpu(wc, attempt):
    # StarDist's TensorFlow model uses one GCD. More allocated GCDs remain idle.
    return 1


def stardist_threads(wc):
    return int(os.environ.get("STARDIST_THREADS", "8"))


rule stardist_segmentation:
    input:
        stitched=str(STITCHED_DIR / "{sample}" / "{sample}.ome.tif")
    output:
        mask=segmentation_mask("stardist", "{sample}")
    params:
        sample="{sample}",
        log_file=lambda wc: str(LOG_ROOT / "segmentation" / "stardist" / wc.sample / f"stardist_{wc.sample}.log"),

        sif_image=os.environ.get("SIF_IMAGE_STARDIST"),
        py_script=os.environ.get("PY_SCRIPT_STARDIST"),
        python_bin=os.environ.get("STARDIST_PYTHON_BIN", "python3"),
        rocm_bind=os.environ.get("STARDIST_ROCM_BIND", "/opt/rocm-6.3.4:/opt/rocm"),

        channel=os.environ.get("STARDIST_CHANNEL", "0"),
        channel_name=os.environ.get("STARDIST_CHANNEL_NAME", "unknown"),
        model=os.environ.get("STARDIST_MODEL", "2D_versatile_fluo"),
        target_tile_edge=os.environ.get("STARDIST_TARGET_TILE_EDGE", "4096"),
        oom_retries=os.environ.get("STARDIST_OOM_RETRIES", "2"),
        require_gpu=os.environ.get("STARDIST_REQUIRE_GPU", "1"),
        strict_channel_names=os.environ.get("STARDIST_STRICT_CHANNEL_NAMES", "1"),
        mask_compression=os.environ.get("STARDIST_MASK_COMPRESSION", "none"),
        prob_thresh=os.environ.get("STARDIST_PROB_THRESH", ""),
        nms_thresh=os.environ.get("STARDIST_NMS_THRESH", ""),
        stripe_count=os.environ.get("SEGMENTATION_STRIPE_COUNT", "4"),
        stripe_size=os.environ.get("SEGMENTATION_STRIPE_SIZE", "4M"),
        base=str(BASE),
        cache_root=os.environ.get("PIPELINE_CACHE_DIR", str(BASE / "cache")),
    threads:
        stardist_threads
    resources:
        mem_mb=stardist_mem,
        runtime=stardist_runtime,
        cpus_per_task=stardist_threads,
        gpus=stardist_gpu,
        slurm_account=os.environ.get("SLURM_ACCOUNT", os.environ.get("PROJECT_ID", "")),
        slurm_partition=os.environ.get("SLURM_PARTITION_GPU", "small-g")
    shell:
        r'''
        set -euo pipefail

        mkdir -p \
          "$(dirname "{output.mask}")" \
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
          INPUT_FILE="{input.stitched}"
          OUTPUT_MASK="{output.mask}"

          SIF_IMAGE="{params.sif_image}"
          PY_SCRIPT="{params.py_script}"
          PYTHON_BIN="{params.python_bin}"
          ROCM_BIND="{params.rocm_bind}"

          THREADS="{threads}"

          SCRATCH_ROOT="${{LOCAL_SCRATCH:-/tmp}}/${{USER}}"
          SCRATCH_BASE="${{SCRATCH_ROOT}}/stardist_${{SLURM_JOB_ID:-manual}}_${{SAMPLE_NAME}}"
          TMP_HOST="${{SCRATCH_BASE}}/tmp"

	          cleanup() {{
	              local status="$?"
	              rm -rf "${{SCRATCH_BASE}}" || true
	              # Remove any leftover partial output (only on failure; on success
	              # it has already been mv'd into the final location).
	              if [[ -n "${{PARTIAL_MASK:-}}" && -e "${{PARTIAL_MASK}}" ]]; then
	                  rm -f "${{PARTIAL_MASK}}" || true
	              fi
	              if [[ -n "${{PARTIAL_QC:-}}" && -e "${{PARTIAL_QC}}" ]]; then
	                  rm -f "${{PARTIAL_QC}}" || true
	              fi
	              return "${{status}}"
	          }}

          trap cleanup EXIT INT TERM

          if declare -F job_log_open >/dev/null 2>&1; then
              job_log_open \
                "Cell segmentation (StarDist)" \
                "Sample ${{SAMPLE_NAME}}" \
                "Star-shaped nuclei are detected in your stitched image"
              job_log "Reading stitched image: ${{INPUT_FILE}}"
          else
              log "StarDist segmentation job started — sample ${{SAMPLE_NAME}}"
          fi

          [[ -f "${{INPUT_FILE}}" ]] || fail "Input file not found: ${{INPUT_FILE}}"
          [[ -f "${{SIF_IMAGE}}" ]] || fail "Container not found: ${{SIF_IMAGE}}"
          [[ -f "${{PY_SCRIPT}}" ]] || fail "Python script not found: ${{PY_SCRIPT}}"

          if [[ -s "${{OUTPUT_MASK}}" ]]; then
              log "Output mask already exists. Job complete."
              exit 0
          fi

          rm -f "${{OUTPUT_MASK}}"

          # Atomic publish: write to <OUT>.partial.<PID> then rename only on success.
          # Lustre rename is atomic, so a killed job leaves no half-written mask in
          # the final path that would be skipped on resume.
	          PARTIAL_MASK="${{OUTPUT_MASK}}.partial.$$"
	          PARTIAL_QC="${{OUTPUT_MASK%_mask_nuclear.tif}}_stardist_qc.json.partial.$$"
	          FINAL_QC="${{OUTPUT_MASK%_mask_nuclear.tif}}_stardist_qc.json"
	          rm -f "${{PARTIAL_MASK}}"
	          rm -f "${{PARTIAL_QC}}"
          if command -v lfs >/dev/null 2>&1; then
              lfs setstripe \
                --stripe-count "{params.stripe_count}" \
                --stripe-size "{params.stripe_size}" \
                "${{PARTIAL_MASK}}" >/dev/null 2>&1 || \
                log "WARNING: could not set Lustre striping on ${{PARTIAL_MASK}}"
          fi

	          mkdir -p "${{TMP_HOST}}"

          # Avoid leaking stdbuf preload from the launcher into the container.
          unset LD_PRELOAD || true

          if [[ -e /dev/kfd ]]; then
              log "/dev/kfd exists"
          else
              log "WARNING: /dev/kfd is missing; ROCm GPU access may fail"
          fi

          if [[ -d /dev/dri ]]; then
              log "/dev/dri exists"
          else
              log "WARNING: /dev/dri is missing; ROCm GPU access may fail"
          fi

          select_first_gpu() {{
              local visible="${{ROCR_VISIBLE_DEVICES:-${{SLURM_JOB_GPUS:-0}}}}"
              visible="${{visible%%,*}}"
              printf '%s\n' "${{visible:-0}}"
          }}

          GPU_ID="$(select_first_gpu)"
          log "Container GPU selected : ${{GPU_ID}}"
          log "SLURM GCD allocation   : ${{SLURM_JOB_GPUS:-unknown}}"
          log "SLURM host memory MiB  : ${{SLURM_MEM_PER_NODE:-unknown}}"

          # StarDist downloads pretrained models lazily on the first call to
          # StarDist2D.from_pretrained(...). When multiple parallel jobs cold-
          # start on a node, csbdeep's unzip-into-cache step can race and
          # produce a corrupted model directory. Serialize that first fetch
          # with a flock so only one job populates the cache; siblings then
          # see a healthy cache and skip straight to inference.
          STARDIST_CACHE_ROOT="{params.cache_root}"
          STARDIST_MODEL_LOCK="${{STARDIST_CACHE_ROOT}}/stardist_model_{params.model}.lock"
          mkdir -p "$(dirname "${{STARDIST_MODEL_LOCK}}")"

          (
              flock -w 600 9 || fail "Could not acquire stardist model cache lock: ${{STARDIST_MODEL_LOCK}}"

              log "Warming StarDist model cache under lock (${{STARDIST_MODEL_LOCK}})"

              if ! singularity exec \
                --rocm \
                -B "${{ROCM_BIND}}" \
                -B "{params.base}:{params.base}" \
                -B "${{TMP_HOST}}:/tmp" \
                --env TMPDIR="/tmp" \
                --env TF_CPP_MIN_LOG_LEVEL="3" \
                --env ROCM_PATH="/opt/rocm" \
                "${{SIF_IMAGE}}" \
                "${{PYTHON_BIN}}" -c "from stardist.models import StarDist2D; StarDist2D.from_pretrained('{params.model}'); print('stardist model cache OK')"; then
                  fail "StarDist model warmup failed under lock"
              fi

              log "StarDist model cache OK; releasing lock"
          ) 9>"${{STARDIST_MODEL_LOCK}}"

	          log "Running StarDist inside Singularity"

	          STRICT_CHANNEL_FLAG=""
	          if [[ "{params.strict_channel_names}" == "1" ]]; then
	              STRICT_CHANNEL_FLAG="--strict-channel-names"
	          fi

	          if ! singularity exec \
	            --rocm \
	            -B "${{ROCM_BIND}}" \
	            -B "{params.base}:{params.base}" \
	            -B "${{TMP_HOST}}:/tmp" \
	            --env TMPDIR="/tmp" \
	            --env TMP="/tmp" \
	            --env TEMP="/tmp" \
	            --env PYTHONUNBUFFERED="1" \
	            --env TF_CPP_MIN_LOG_LEVEL="3" \
	            --env STARDIST_REQUIRE_GPU="{params.require_gpu}" \
	            --env STARDIST_MASK_COMPRESSION="{params.mask_compression}" \
	            --env ROCM_PATH="/opt/rocm" \
	            --env HIP_VISIBLE_DEVICES="${{GPU_ID}}" \
	            --env ROCR_VISIBLE_DEVICES="${{GPU_ID}}" \
	            --env OMP_NUM_THREADS="${{THREADS}}" \
	            --env OPENBLAS_NUM_THREADS="${{THREADS}}" \
	            --env MKL_NUM_THREADS="${{THREADS}}" \
	            "${{SIF_IMAGE}}" \
	            "${{PYTHON_BIN}}" "${{PY_SCRIPT}}" \
	              --input "${{INPUT_FILE}}" \
	              --output "${{PARTIAL_MASK}}" \
	              --qc-output "${{PARTIAL_QC}}" \
	              --channel "{params.channel}" \
	              --channel-name "{params.channel_name}" \
	              ${{STRICT_CHANNEL_FLAG}} \
	              --model "{params.model}" \
	              --target-tile-edge "{params.target_tile_edge}" \
	              --oom-retries "{params.oom_retries}" \
	              --prob-thresh "{params.prob_thresh}" \
	              --nms-thresh "{params.nms_thresh}"; then
	              fail "StarDist Python worker failed. Scroll up in this log for the Python traceback."
	          fi

	          [[ -s "${{PARTIAL_MASK}}" ]] || fail "Partial mask not found or empty: ${{PARTIAL_MASK}}"
	          [[ -s "${{PARTIAL_QC}}" ]] || fail "Partial QC summary not found or empty: ${{PARTIAL_QC}}"
	          mv -f "${{PARTIAL_MASK}}" "${{OUTPUT_MASK}}"
	          mv -f "${{PARTIAL_QC}}" "${{FINAL_QC}}"

	          [[ -s "${{OUTPUT_MASK}}" ]] || fail "Expected output mask not found or empty: ${{OUTPUT_MASK}}"

	          log "Final mask written: ${{OUTPUT_MASK}}"
	          log "QC summary written: ${{FINAL_QC}}"
          if declare -F job_log_close_ok >/dev/null 2>&1; then
              job_log_close_ok "Nuclear mask saved for this sample."
          else
              log "Job finished successfully at $(date '+%Y-%m-%d %H:%M:%S')"
          fi

        }} 2>&1 | tee -a "{params.log_file}"
        '''
