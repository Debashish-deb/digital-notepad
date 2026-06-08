# rules/mesmer.smk
#
# One Mesmer run produces the compartment selected by the launcher. DeepTile
# owns edge coverage and instance-label stitching. In "both" mode, the worker
# validates the compartment relationship before either output is published.
#
# DeepCell Mesmer output mapping for compartment="both":
#   Mesmer output channel 0 -> {sample}_mask_whole_cell.tif
#   Mesmer output channel 1 -> {sample}_mask_nuclear.tif


def mesmer_mem(wc, attempt):
    gib = file_size_gib(str(STITCHED_DIR / wc.sample / f"{wc.sample}.ome.tif"))
    return auto_mem_mb(gib, "mesmer", attempt)


def mesmer_runtime(wc, attempt):
    gib = file_size_gib(str(STITCHED_DIR / wc.sample / f"{wc.sample}.ome.tif"))
    return auto_runtime(gib, "mesmer", attempt)


def mesmer_gpu(wc, attempt):
    # Mesmer/TensorFlow runs on one GCD. Additional GCDs do not accelerate
    # this worker and only increase queue pressure and GPU-hour billing.
    return 1


def mesmer_threads(wc):
    return int(os.environ.get("MESMER_THREADS", "8"))


def _mesmer_output_dir(wc):
    return str(Path(segmentation_mask("mesmer", wc.sample, "nuclear")).parent)


_MESMER_RULE_OUTPUTS = []
if MESMER_COMPARTMENT in {"nuclear", "both"}:
    _MESMER_RULE_OUTPUTS.append(
        segmentation_mask("mesmer", "{sample}", "nuclear")
    )
if MESMER_COMPARTMENT in {"whole-cell", "both"}:
    _MESMER_RULE_OUTPUTS.append(
        segmentation_mask("mesmer", "{sample}", "whole-cell")
    )


_MESMER_SHELL = r'''
        set -euo pipefail

        mkdir -p \
          "{params.output_dir}" \
          "$(dirname "{params.log_file}")" \
          "{params.cache_root}" \
          "{params.deepcell_cache_host}/models"
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
          OUTPUT_DIR="{params.output_dir}"

          SIF_IMAGE="{params.sif_image}"
          PY_SCRIPT="{params.py_script}"
          PYTHON_BIN="{params.python_bin}"
          PYTHON_USER_PACKAGES="{params.python_user_packages}"
          ROCM_BIND="{params.rocm_bind}"
          ROCM_BITCODE="{params.rocm_bitcode}"
          USE_PROJECT_PACKAGES="{params.use_project_packages}"
          REQUIRE_GPU="{params.require_gpu}"

          PYTHONPATH_MESMER="{params.base}/scripts"
          if [[ "${{USE_PROJECT_PACKAGES}}" == "1" ]]; then
              PYTHONPATH_MESMER="${{PYTHON_USER_PACKAGES}}:${{PYTHONPATH_MESMER}}"
          fi

          THREADS="{threads}"

          IMAGE_MPP="{params.image_mpp}"
          NUCLEAR_CHANNEL="{params.nuclear_channel}"
          MEMBRANE_CHANNEL="{params.membrane_channel}"
          NUCLEAR_CHANNEL_NAME="{params.nuclear_channel_name}"
          MEMBRANE_CHANNEL_NAME="{params.membrane_channel_name}"
          TILE_SIZE="{params.tile_size}"
          BATCH_SIZE="{params.batch_size}"
          OVERLAP_FRACTION="{params.overlap_fraction}"
          PREPROCESS_GAMMA="{params.preprocess_gamma}"
          PREPROCESS_MODE="{params.preprocess_mode}"
          BACKGROUND_THRESHOLD="{params.background_threshold}"
          PAD_MODE="{params.pad_mode}"
          STRICT_CHANNEL_NAMES="{params.strict_channel_names}"
          WARMUP="{params.warmup}"
          COMPARTMENT="{params.compartment}"

          DEEPCELL_TOKEN="${{DEEPCELL_ACCESS_TOKEN:-}}"

          CACHE_ROOT="{params.cache_root}"
          DEEPCELL_CACHE_HOST="{params.deepcell_cache_host}"
          CACHE_LOCK="${{CACHE_ROOT}}/mesmer_cache_setup.lock"
          CACHE_VERSION="lumi_rocm63_tf217_deepcell013_v1"
          CONTAINER_READY="${{CACHE_ROOT}}/.mesmer_container_${{CACHE_VERSION}}.ready"
          MODEL_READY="${{DEEPCELL_CACHE_HOST}}/.mesmer_model_${{CACHE_VERSION}}.ready"
          MIOPEN_SHARED_CACHE_HOST="${{CACHE_ROOT}}/miopen_${{CACHE_VERSION}}"

          SCRATCH_ROOT="${{LOCAL_SCRATCH:-/tmp}}/${{USER}}"
          SCRATCH_BASE="${{SCRATCH_ROOT}}/mesmer_${{SLURM_JOB_ID:-manual}}_${{SAMPLE_NAME}}"

          HOME_DEEPCELL_CACHE="${{HOME:-${{SCRATCH_ROOT}}}}/.deepcell"

          TMP_HOST="${{SCRATCH_BASE}}/tmp"
          MPL_CACHE_HOST="${{SCRATCH_BASE}}/matplotlib"
          XDG_CACHE_HOST="${{SCRATCH_BASE}}/xdg"
          FONTCONFIG_CACHE_HOST="${{XDG_CACHE_HOST}}/fontconfig"
          MIOPEN_CACHE_HOST="${{SCRATCH_BASE}}/miopen-cache"
          DEEPCELL_RUNTIME_CACHE_HOST="${{SCRATCH_BASE}}/deepcell_runtime"

          clean_deepcell_model_cache() {{
              log "Cleaning potentially corrupted DeepCell/Mesmer model caches"
              rm -rf "${{DEEPCELL_CACHE_HOST}}/models/MultiplexSegmentation" || true
              rm -f  "${{DEEPCELL_CACHE_HOST}}/models/MultiplexSegmentation-9.tar.gz" || true
              rm -f  "${{MODEL_READY:-}}" || true
              rm -rf "${{HOME_DEEPCELL_CACHE}}/models/MultiplexSegmentation" || true
              rm -f  "${{HOME_DEEPCELL_CACHE}}/models/MultiplexSegmentation-9.tar.gz" || true
          }}

          cleanup() {{
              local status="$?"
              rm -rf "${{SCRATCH_BASE}}" || true
              if [[ -n "${{STAGING_DIR:-}}" && -d "${{STAGING_DIR}}" ]]; then
                  rm -rf "${{STAGING_DIR}}" || true
              fi
              if [[ "${{status}}" -ne 0 ]]; then
                  log "Mesmer job exited before publishing masks (exit status ${{status}}). If there is no Python traceback above, SLURM likely killed the worker; check the per-job SLURM log for OUT_OF_MEMORY, TIMEOUT, CANCELLED, or node failure."
              fi
              if [[ "${{status}}" -eq 0 && "${{MESMER_CLEAN_MODEL_CACHE_AFTER_SUCCESS:-0}}" == "1" ]]; then
                  log "MESMER_CLEAN_MODEL_CACHE_AFTER_SUCCESS=1, cleaning model cache after successful run"
                  clean_deepcell_model_cache || true
              fi
              return "${{status}}"
          }}

          trap cleanup EXIT INT TERM

          test_container_imports() {{
              singularity exec \
                --rocm \
                --home "{params.cache_root}:/workspace" \
                -B "${{ROCM_BIND}}" \
                -B "{params.base}:{params.base}" \
                -B "${{CACHE_ROOT}}:${{CACHE_ROOT}}" \
                --env PYTHONUNBUFFERED="1" \
                --env PYTHONPATH="${{PYTHONPATH_MESMER}}" \
                --env LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:/opt/rocm/lib:/opt/rocm/lib64:/.singularity.d/libs" \
                --env HIP_DEVICE_LIB_PATH="${{ROCM_BITCODE}}" \
                "${{SIF_IMAGE}}" \
                "${{PYTHON_BIN}}" - <<'PY_IMPORTS'
import numpy
import tensorflow as tf
import tifffile
import zarr
import cv2
from deeptile import load, lift
from deeptile.extensions import stitch
from deepcell.applications import Mesmer
if not tf.sysconfig.get_build_info().get("is_rocm_build"):
    raise RuntimeError("TensorFlow is not a ROCm build.")
if not tf.config.list_physical_devices("GPU"):
    raise RuntimeError("ROCm TensorFlow cannot see the allocated GPU.")
print("Mesmer Python environment OK")
PY_IMPORTS
          }}

          test_mesmer_model_cache() {{
              singularity exec \
                --rocm \
                --home "{params.cache_root}:/workspace" \
                -B "${{ROCM_BIND}}" \
                -B "{params.base}:{params.base}" \
                -B "${{DEEPCELL_CACHE_HOST}}:/workspace/.deepcell" \
                -B "${{TMP_HOST}}:/tmp" \
                -B "${{MIOPEN_SHARED_CACHE_HOST}}:/tmp/miopen-cache" \
                --env TMPDIR="/tmp" \
                --env TMP="/tmp" \
                --env TEMP="/tmp" \
                --env DEEPCELL_HOME="/workspace/.deepcell" \
                --env DEEPCELL_CACHE_DIR="/workspace/.deepcell" \
                --env DEEPCELL_ACCESS_TOKEN="${{DEEPCELL_TOKEN}}" \
                --env PYTHONUNBUFFERED="1" \
                --env PYTHONPATH="${{PYTHONPATH_MESMER}}" \
                --env TF_CPP_MIN_LOG_LEVEL="3" \
                --env TF_USE_LEGACY_KERAS="1" \
                --env TF_XLA_FLAGS="--tf_xla_auto_jit=-1" \
                --env TF_ENABLE_ONEDNN_OPTS="0" \
                --env TF_ENABLE_MLIR_BRIDGE="0" \
                --env ROCM_PATH="/opt/rocm" \
                --env HIP_DEVICE_LIB_PATH="${{ROCM_BITCODE}}" \
                --env LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:/opt/rocm/lib:/opt/rocm/lib64:/.singularity.d/libs" \
                --env MIOPEN_USER_DB_PATH="/tmp/miopen-cache" \
                --env MIOPEN_CUSTOM_CACHE_DIR="/tmp/miopen-cache" \
                --env ROCR_VISIBLE_DEVICES="0" \
                --env HIP_VISIBLE_DEVICES="0" \
                "${{SIF_IMAGE}}" \
                "${{PYTHON_BIN}}" - <<'PY_MODEL'
import numpy as np
import tensorflow as tf
from deepcell.applications import Mesmer
gpus = tf.config.list_physical_devices("GPU")
if not tf.sysconfig.get_build_info().get("is_rocm_build") or not gpus:
    raise RuntimeError("Mesmer GPU validation failed before model loading.")
app = Mesmer()
test_image = np.random.default_rng(1).random(
    (1, 256, 256, 2),
    dtype=np.float32,
)
prediction = app.predict(test_image, image_mpp=0.5, compartment="both")
if prediction.shape[:3] != test_image.shape[:3] or prediction.shape[-1] != 2:
    raise RuntimeError(
        f"Unexpected Mesmer GPU smoke-test output shape: {{prediction.shape}}"
    )
print("Mesmer model cache and GPU inference OK")
PY_MODEL
          }}

          if declare -F job_log_open >/dev/null 2>&1; then
              job_log_open \
                "Cell segmentation (Mesmer)" \
                "Sample ${{SAMPLE_NAME}} · compartment ${{COMPARTMENT}}" \
                "Deep learning finds the requested cellular boundaries"
              job_log "Reading stitched image: ${{INPUT_FILE}}"
          else
              log "Mesmer segmentation job started — sample ${{SAMPLE_NAME}} (${{COMPARTMENT}})"
          fi

          [[ -f "${{INPUT_FILE}}" ]] || fail "Input file not found: ${{INPUT_FILE}}"
          [[ -f "${{SIF_IMAGE}}" ]] || fail "Container not found: ${{SIF_IMAGE}}"
          [[ -f "${{PY_SCRIPT}}" ]] || fail "Python script not found: ${{PY_SCRIPT}}"

          if [[ -z "${{DEEPCELL_TOKEN}}" ]]; then
              fail "DEEPCELL_ACCESS_TOKEN is not set"
          fi

          ALL_OUTPUTS=({output:q})
          MISSING=0
          for OUT_FILE in "${{ALL_OUTPUTS[@]}}"; do
              if [[ ! -s "${{OUT_FILE}}" ]]; then
                  MISSING=1
                  break
              fi
          done

          if [[ "${{MISSING}}" == "0" ]]; then
              log "All requested output masks already exist. Job complete."
              exit 0
          fi

          for OUT_FILE in "${{ALL_OUTPUTS[@]}}"; do
              rm -f "${{OUT_FILE}}"
              mkdir -p "$(dirname "${{OUT_FILE}}")"
          done

          STAGING_DIR="${{OUTPUT_DIR}}/.partial.$$"
          rm -rf "${{STAGING_DIR}}"
          mkdir -p "${{STAGING_DIR}}"
          if command -v lfs >/dev/null 2>&1; then
              lfs setstripe \
                --stripe-count "{params.stripe_count}" \
                --stripe-size "{params.stripe_size}" \
                "${{STAGING_DIR}}" >/dev/null 2>&1 || \
                log "WARNING: could not set Lustre striping on ${{STAGING_DIR}}"
          fi

          mkdir -p \
            "${{TMP_HOST}}" \
            "${{MPL_CACHE_HOST}}" \
            "${{XDG_CACHE_HOST}}/config" \
            "${{FONTCONFIG_CACHE_HOST}}" \
            "${{MIOPEN_CACHE_HOST}}" \
            "${{MIOPEN_SHARED_CACHE_HOST}}" \
            "${{DEEPCELL_CACHE_HOST}}/models" \
            "${{DEEPCELL_RUNTIME_CACHE_HOST}}/models" \
            "${{PYTHON_USER_PACKAGES}}" \
            "$(dirname "${{CACHE_LOCK}}")"

          unset LD_PRELOAD || true
          unset JAVA_HOME || true
          unset SINGULARITYENV_HOME || true
          unset APPTAINERENV_HOME || true

          [[ -e /dev/kfd ]] && log "/dev/kfd exists" || log "WARNING: /dev/kfd is missing; ROCm GPU access may fail"
          [[ -d /dev/dri ]] && log "/dev/dri exists" || log "WARNING: /dev/dri is missing; ROCm GPU access may fail"

          log "Checking immutable Mesmer container and shared model cache"

          if [[ ! -f "${{CONTAINER_READY}}" || ! -f "${{MODEL_READY}}" ]]; then
              (
                  flock -w 1800 9 || {{
                      log "ERROR: Could not acquire one-time cache setup lock: ${{CACHE_LOCK}}"
                      exit 1
                  }}

                  if [[ ! -f "${{CONTAINER_READY}}" ]]; then
                      log "Validating ROCm TensorFlow, GPU visibility, and Mesmer imports once"
                      if ! test_container_imports; then
                          log "ERROR: Mesmer container is incomplete or cannot see the allocated GPU"
                          exit 1
                      fi
                      touch "${{CONTAINER_READY}}"
                      log "Mesmer container validation complete"
                  fi

                  if [[ ! -f "${{MODEL_READY}}" ]]; then
                      log "Validating the shared Mesmer model with a real GPU prediction once"
                      if ! test_mesmer_model_cache; then
                          log "Shared model validation failed; cleaning the model cache and retrying once"
                          clean_deepcell_model_cache
                          mkdir -p "${{DEEPCELL_CACHE_HOST}}/models"
                          if ! test_mesmer_model_cache; then
                              log "ERROR: Mesmer model GPU smoke test still fails after cache repair"
                              exit 1
                          fi
                      fi
                      touch "${{MODEL_READY}}"
                      log "Mesmer shared model and GPU inference validation complete"
                  fi
              ) 9>"${{CACHE_LOCK}}"
          else
              log "Container and model validation markers already present"
          fi

          # The lock protects only one-time mutation/validation. Concurrent
          # samples copy the completed read-only caches independently.
          rm -rf "${{DEEPCELL_RUNTIME_CACHE_HOST}}"
          mkdir -p "${{DEEPCELL_RUNTIME_CACHE_HOST}}/models"
          cp -a "${{DEEPCELL_CACHE_HOST}}/models/." "${{DEEPCELL_RUNTIME_CACHE_HOST}}/models/"
          if [[ -d "${{MIOPEN_SHARED_CACHE_HOST}}" ]]; then
              cp -a "${{MIOPEN_SHARED_CACHE_HOST}}/." "${{MIOPEN_CACHE_HOST}}/" || true
          fi
          chmod -R u+rwX "${{DEEPCELL_RUNTIME_CACHE_HOST}}" "${{MIOPEN_CACHE_HOST}}" || true
          log "Job-local DeepCell and MIOpen caches ready"

          select_first_gpu() {{
              local visible="${{ROCR_VISIBLE_DEVICES:-${{SLURM_JOB_GPUS:-0}}}}"
              visible="${{visible%%,*}}"
              printf '%s\n' "${{visible:-0}}"
          }}

          GPU_ID="$(select_first_gpu)"
          log "Container GPU selected : ${{GPU_ID}}"
          log "SLURM GCD allocation   : ${{SLURM_JOB_GPUS:-unknown}}"
          log "SLURM step GCD         : ${{SLURM_STEP_GPUS:-unknown}}"
          log "SLURM host memory MiB  : ${{SLURM_MEM_PER_NODE:-unknown}}"
          log "Running Mesmer inside Singularity"

          STRICT_CHANNEL_FLAG=""
          if [[ "${{STRICT_CHANNEL_NAMES}}" == "1" ]]; then
              STRICT_CHANNEL_FLAG="--strict-channel-names"
          fi

          WARMUP_FLAG=""
          if [[ "${{WARMUP}}" == "1" ]]; then
              WARMUP_FLAG="--warmup"
          fi

          if ! singularity exec \
            --rocm \
            --home "{params.cache_root}:/workspace" \
            -B "${{ROCM_BIND}}" \
            -B "{params.base}:{params.base}" \
            -B "${{DEEPCELL_RUNTIME_CACHE_HOST}}:/workspace/.deepcell" \
            -B "${{MPL_CACHE_HOST}}:/cache/matplotlib" \
            -B "${{XDG_CACHE_HOST}}:/cache/xdg" \
            -B "${{TMP_HOST}}:/tmp" \
            -B "${{MIOPEN_CACHE_HOST}}:/tmp/miopen-cache" \
            --env TMPDIR="/tmp" \
            --env TMP="/tmp" \
            --env TEMP="/tmp" \
            --env XDG_CACHE_HOME="/cache/xdg" \
            --env XDG_CONFIG_HOME="/cache/xdg/config" \
            --env MPLCONFIGDIR="/cache/matplotlib" \
            --env FONTCONFIG_PATH="/cache/xdg/fontconfig" \
            --env DEEPCELL_HOME="/workspace/.deepcell" \
            --env DEEPCELL_CACHE_DIR="/workspace/.deepcell" \
            --env DEEPCELL_ACCESS_TOKEN="${{DEEPCELL_TOKEN}}" \
            --env PYTHONUNBUFFERED="1" \
            --env PYTHONPATH="${{PYTHONPATH_MESMER}}" \
            --env MESMER_REQUIRE_GPU="${{REQUIRE_GPU}}" \
            --env MESMER_MASK_COMPRESSION="{params.mask_compression}" \
            --env MESMER_WRITE_PYRAMID="{params.write_pyramid}" \
            --env TF_CPP_MIN_LOG_LEVEL="3" \
            --env TF_USE_LEGACY_KERAS="1" \
            --env TF_XLA_FLAGS="--tf_xla_auto_jit=-1" \
            --env TF_ENABLE_ONEDNN_OPTS="0" \
            --env TF_ENABLE_MLIR_BRIDGE="0" \
            --env ROCM_PATH="/opt/rocm" \
            --env HIP_DEVICE_LIB_PATH="${{ROCM_BITCODE}}" \
            --env LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:/opt/rocm/lib:/opt/rocm/lib64:/.singularity.d/libs" \
            --env MIOPEN_DEBUG_DISABLE_FIND_DB="1" \
            --env MIOPEN_USER_DB_PATH="/tmp/miopen-cache" \
            --env MIOPEN_CUSTOM_CACHE_DIR="/tmp/miopen-cache" \
            --env MIOPEN_FIND_MODE="NORMAL" \
            --env HSA_ENABLE_SDMA="0" \
            --env HIP_VISIBLE_DEVICES="${{GPU_ID}}" \
            --env ROCR_VISIBLE_DEVICES="${{GPU_ID}}" \
            --env OMP_NUM_THREADS="${{THREADS}}" \
            --env OPENBLAS_NUM_THREADS="${{THREADS}}" \
            --env MKL_NUM_THREADS="${{THREADS}}" \
            --env NUMEXPR_NUM_THREADS="${{THREADS}}" \
            --env TF_NUM_INTRAOP_THREADS="${{THREADS}}" \
            --env TF_NUM_INTEROP_THREADS="1" \
            "${{SIF_IMAGE}}" \
            "${{PYTHON_BIN}}" "${{PY_SCRIPT}}" \
              --input "${{INPUT_FILE}}" \
              --output-dir "${{STAGING_DIR}}" \
              --mpp "${{IMAGE_MPP}}" \
              --channel "${{NUCLEAR_CHANNEL}}" \
              --membrane-channel "${{MEMBRANE_CHANNEL}}" \
              --nuclear-channel-name "${{NUCLEAR_CHANNEL_NAME}}" \
              --membrane-channel-name "${{MEMBRANE_CHANNEL_NAME}}" \
              --tile-size "${{TILE_SIZE}}" \
              --batch-size "${{BATCH_SIZE}}" \
              --overlap-fraction "${{OVERLAP_FRACTION}}" \
              --preprocess-gamma "${{PREPROCESS_GAMMA}}" \
              --preprocess-mode "${{PREPROCESS_MODE}}" \
              --background-threshold "${{BACKGROUND_THRESHOLD}}" \
              --pad-mode "${{PAD_MODE}}" \
              --compartment "${{COMPARTMENT}}" \
              ${{STRICT_CHANNEL_FLAG}} \
              ${{WARMUP_FLAG}}; then
              fail "Mesmer Python worker failed. Scroll up in this log for the Python traceback."
          fi

          log "Promoting staged masks into final output directory"

          for OUT_FILE in "${{ALL_OUTPUTS[@]}}"; do
              STAGED_FILE="${{STAGING_DIR}}/$(basename "${{OUT_FILE}}")"
              [[ -s "${{STAGED_FILE}}" ]] || {{
                  log "Staging dir contents:"
                  find "${{STAGING_DIR}}" -maxdepth 2 -type f -ls || true
                  fail "Expected staged mask not found or empty: ${{STAGED_FILE}}"
              }}
              mv -f "${{STAGED_FILE}}" "${{OUT_FILE}}"
              log "Final mask written: ${{OUT_FILE}}"
          done

          for QC_FILE in "${{STAGING_DIR}}"/*_mesmer_qc.json; do
              [[ -e "${{QC_FILE}}" ]] || continue
              mv -f "${{QC_FILE}}" "${{OUTPUT_DIR}}/$(basename "${{QC_FILE}}")"
              log "QC summary written: ${{OUTPUT_DIR}}/$(basename "${{QC_FILE}}")"
          done

          rmdir "${{STAGING_DIR}}" 2>/dev/null || rm -rf "${{STAGING_DIR}}" || true

          for OUT_FILE in "${{ALL_OUTPUTS[@]}}"; do
              [[ -s "${{OUT_FILE}}" ]] || fail "Expected output mask not found or empty: ${{OUT_FILE}}"
          done

          if declare -F job_log_close_ok >/dev/null 2>&1; then
              job_log_close_ok "Requested Mesmer mask(s) saved for this sample."
          else
              log "Job finished successfully at $(date '+%Y-%m-%d %H:%M:%S')"
          fi

        }} 2>&1 | tee -a "{params.log_file}"
        '''


rule mesmer:
    input:
        stitched=str(STITCHED_DIR / "{sample}" / "{sample}.ome.tif")
    output:
        _MESMER_RULE_OUTPUTS
    params:
        sample="{sample}",
        output_dir=_mesmer_output_dir,
        log_file=lambda wc: str(LOG_ROOT / "segmentation" / "mesmer" / wc.sample / f"mesmer_{wc.sample}.log"),
        sif_image=os.environ.get("SIF_IMAGE_MESMER"),
        py_script=os.environ.get("PY_SCRIPT_MESMER"),
        python_bin=os.environ.get("MESMER_PYTHON_BIN", "/usr/local/bin/python3.10"),
        python_user_packages=os.environ.get("MESMER_PYTHON_USER_PACKAGES", str(BASE / "python_user_packages")),
        rocm_bind=os.environ.get("MESMER_ROCM_BIND", "/opt/rocm-6.3.4:/opt/rocm"),
        rocm_bitcode=os.environ.get(
            "MESMER_ROCM_BITCODE",
            "/opt/rocm/lib/llvm/lib/clang/18/lib/amdgcn/bitcode",
        ),
        use_project_packages=os.environ.get("MESMER_USE_PROJECT_PACKAGES", "0"),
        require_gpu=os.environ.get("MESMER_REQUIRE_GPU", "1"),
        cache_root=os.environ.get("PIPELINE_CACHE_DIR", str(BASE / "cache")),
        deepcell_cache_host=os.environ.get("DEEPCELL_CACHE_DIR", str(BASE / "cache" / "deepcell")),
        image_mpp=os.environ.get("IMAGE_MPP", "auto"),
        nuclear_channel=os.environ.get("NUCLEAR_CHANNEL", "0"),
        membrane_channel=os.environ.get("MEMBRANE_CHANNEL", "1"),
        nuclear_channel_name=os.environ.get("NUCLEAR_CHANNEL_NAME", "unknown"),
        membrane_channel_name=os.environ.get("MEMBRANE_CHANNEL_NAME", "unknown"),
        tile_size=os.environ.get("TILE_SIZE", "1024"),
        batch_size=os.environ.get("MESMER_BATCH_SIZE", "4"),
        overlap_fraction=os.environ.get("OVERLAP_FRACTION", "0.10"),
        preprocess_gamma=os.environ.get("PREPROCESS_GAMMA", "1.5"),
        preprocess_mode=os.environ.get("MESMER_PREPROCESS_MODE", "gamma-unsharp"),
        background_threshold=os.environ.get("BACKGROUND_THRESHOLD", "600"),
        pad_mode=os.environ.get("MESMER_PAD_MODE", "constant"),
        strict_channel_names=os.environ.get("MESMER_STRICT_CHANNEL_NAMES", "1"),
        mask_compression=os.environ.get("MESMER_MASK_COMPRESSION", "none"),
        write_pyramid=os.environ.get("MESMER_WRITE_PYRAMID", "0"),
        warmup=os.environ.get("WARMUP", "1"),
        compartment=MESMER_COMPARTMENT,
        stripe_count=os.environ.get("SEGMENTATION_STRIPE_COUNT", "4"),
        stripe_size=os.environ.get("SEGMENTATION_STRIPE_SIZE", "4M"),
        base=str(BASE),
    threads:
        mesmer_threads
    resources:
        mem_mb=mesmer_mem,
        runtime=mesmer_runtime,
        cpus_per_task=mesmer_threads,
        gpus=mesmer_gpu,
        slurm_account=os.environ.get("SLURM_ACCOUNT", os.environ.get("PROJECT_ID", "")),
        slurm_partition=os.environ.get("SLURM_PARTITION_GPU", "small-g")
    shell:
        _MESMER_SHELL
