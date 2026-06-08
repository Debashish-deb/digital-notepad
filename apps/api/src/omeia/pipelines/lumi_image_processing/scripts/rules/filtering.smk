# rules/filtering.smk

import json
import shlex
from pathlib import Path

ruleorder: quantify_filtered_whole_cell_mesmer > quantify_filtered_mesmer


def _load_filter_markers():
    raw = os.environ.get("MARKERS_JSON", "").strip()
    if not raw:
        return {}
    if raw.startswith("'") and raw.endswith("'"):
        raw = raw[1:-1].strip()
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1].strip()
    raw = raw.replace('\\"', '"')
    if not raw or raw == "{}":
        return {}
    try:
        markers = json.loads(raw)
    except Exception as e:
        raise ValueError(f"MARKERS_JSON must be valid JSON. Received {raw!r}. JSON error: {e}")
    if not isinstance(markers, dict):
        raise ValueError("MARKERS_JSON must be a JSON object: marker name -> channel index.")
    return {str(marker): int(channel) for marker, channel in markers.items()}


FILTER_MARKERS = _load_filter_markers()
FILTER_MARKER_NAMES = sorted(FILTER_MARKERS.keys())


def _stitched_size_gib(sample):
    return file_size_gib(str(STITCHED_DIR / sample / f"{sample}.ome.tif"))


def filter_mem(wc, attempt):
    # White-tophat on a single channel is roughly 2x channel-size in RAM. For
    # large stitched OME-TIFFs (multiple uint16 channels) per-channel size can
    # be tens of GiB. Scale by stitched image size like the other steps do
    # instead of using a fixed 32 GiB allocation.
    gib = _stitched_size_gib(wc.sample)
    base = auto_mem_mb(gib, "quant", attempt)
    # Floor at the previous default so small slides still get a reasonable budget.
    return max(base, auto_mem_mb(0, "filter", attempt))


def filter_runtime(wc, attempt):
    gib = _stitched_size_gib(wc.sample)
    base = auto_runtime(gib, "quant", attempt)
    return max(base, auto_runtime(0, "filter", attempt))


def filtered_quant_mem(wc, attempt):
    # Filtered-image quantification reads the mask plus one filtered TIFF per
    # marker. Memory follows the stitched image size, same as plain quantification.
    return auto_mem_mb(_stitched_size_gib(wc.sample), "quant", attempt)


def filtered_quant_runtime(wc, attempt):
    return auto_runtime(_stitched_size_gib(wc.sample), "quant", attempt)


def filter_threads(wc):
    return int(os.environ.get("FILTER_CPUS", "1"))


def filtered_quant_threads(wc):
    return int(os.environ.get("QUANT_CPUS", "4"))


def ensure_filter_markers_available():
    if not FILTER_MARKER_NAMES:
        raise ValueError("Filtering is required, but MARKERS_JSON is empty.")


def filtered_images_for_method_sample(method, sample):
    ensure_filter_markers_available()
    return [filtered_tif_path(method, sample, marker) for marker in FILTER_MARKER_NAMES]


def to_container_path(path):
    rel = Path(path).relative_to(BASE)
    return str(Path("/work") / rel)


def marker_images_json_for(method, sample, container=False):
    ensure_filter_markers_available()
    mapping = {}
    for marker in FILTER_MARKER_NAMES:
        p = filtered_tif_path(method, sample, marker)
        mapping[marker] = to_container_path(p) if container else p
    return json.dumps(mapping, sort_keys=True)


def _filter_rule_shell():
    return r'''
        set -euo pipefail
        mkdir -p "$(dirname "{output.tif}")" "$(dirname "{params.log_file}")"
        : > "{params.log_file}"
        {{
          [[ -f "{params.base}/scripts/lib/job_log_ui.sh" ]] && source "{params.base}/scripts/lib/job_log_ui.sh"
          SAMPLE_NAME="{params.sample}"; METHOD="{params.method}"; MARKER="{params.marker}"; CHANNEL="{params.channel}"
          IMAGE_FILE="{input.image}"; OUTPUT_FILE="{output.tif}"
          if declare -F job_log_open >/dev/null 2>&1; then
              job_log_open \
                "Marker enhancement (white top-hat)" \
                "Sample ${{SAMPLE_NAME}} · marker ${{MARKER}} (${{METHOD}})" \
                "Enhancing this marker channel before re-quantification"
              log() {{ job_log "$@"; }}
              fail() {{ job_log_fail "$@"; exit 1; }}
          else
              log() {{ printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }}
              fail() {{ log "ERROR: $*"; exit 1; }}
          fi
          [[ -f "${{IMAGE_FILE}}" ]] || fail "Image file not found: ${{IMAGE_FILE}}"
          [[ -f "{params.py_script}" ]] || fail "Filter script not found: {params.py_script}"
          if [[ -s "${{OUTPUT_FILE}}" ]]; then log "Output already exists. Job complete."; exit 0; fi
          rm -f "${{OUTPUT_FILE}}"
          # Atomic publish: write to <OUT>.partial.<PID>, then rename only on success.
          PARTIAL_FILE="${{OUTPUT_FILE}}.partial.$$"
          rm -f "${{PARTIAL_FILE}}"
          trap 'rm -f "${{PARTIAL_FILE}}" 2>/dev/null || true' EXIT INT TERM
          if [[ "{params.use_container}" == "1" ]]; then
              [[ -f "{params.sif_image}" ]] || fail "Container not found: {params.sif_image}"
              IMAGE_REL="$(realpath --relative-to="{params.base}" "${{IMAGE_FILE}}")"
              PARTIAL_REL="$(realpath --relative-to="{params.base}" "${{PARTIAL_FILE}}")"
              SCRIPT_REL="$(realpath --relative-to="{params.base}" "{params.py_script}")"
              singularity exec --bind "{params.base}:/work" --env PYTHONUNBUFFERED="1" "{params.sif_image}" "{params.python_bin}" -u "/work/${{SCRIPT_REL}}" filter-one --image-file "/work/${{IMAGE_REL}}" --output-file "/work/${{PARTIAL_REL}}" --marker "${{MARKER}}" --channel "${{CHANNEL}}" --size "{params.tophat_size}"
          else
              python3 "{params.py_script}" filter-one --image-file "${{IMAGE_FILE}}" --output-file "${{PARTIAL_FILE}}" --marker "${{MARKER}}" --channel "${{CHANNEL}}" --size "{params.tophat_size}"
          fi
          [[ -s "${{PARTIAL_FILE}}" ]] || fail "Partial filtered TIFF not found or empty: ${{PARTIAL_FILE}}"
          mv -f "${{PARTIAL_FILE}}" "${{OUTPUT_FILE}}"
          [[ -s "${{OUTPUT_FILE}}" ]] || fail "Expected filtered TIFF not found or empty: ${{OUTPUT_FILE}}"
          if declare -F job_log_close_ok >/dev/null 2>&1; then
              job_log_close_ok "Enhanced marker image saved."
          else
              log "Job finished successfully"
          fi
        }} 2>&1 | tee -a "{params.log_file}"
        '''


def _quant_filtered_shell():
    return r'''
        set -euo pipefail
        mkdir -p "$(dirname "{output.csv}")" "$(dirname "{params.log_file}")"
        : > "{params.log_file}"
        {{
          [[ -f "{params.base}/scripts/lib/job_log_ui.sh" ]] && source "{params.base}/scripts/lib/job_log_ui.sh"
          SAMPLE_NAME="{params.sample}"; METHOD="{params.method}"; MASK_FILE="{input.mask}"; OUTPUT_CSV="{output.csv}"
          if declare -F job_log_open >/dev/null 2>&1; then
              job_log_open \
                "Re-quantification after filtering" \
                "Sample ${{SAMPLE_NAME}} · method ${{METHOD}}" \
                "Measuring markers again on enhanced images"
              log() {{ job_log "$@"; }}
              fail() {{ job_log_fail "$@"; exit 1; }}
          else
              log() {{ printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }}
              fail() {{ log "ERROR: $*"; exit 1; }}
          fi
          [[ "{params.marker_count}" -gt 0 ]] || fail "No filter markers configured."
          [[ -f "${{MASK_FILE}}" ]] || fail "Mask file not found: ${{MASK_FILE}}"
          [[ -f "{params.py_script}" ]] || fail "Filter script not found: {params.py_script}"
          if [[ -s "${{OUTPUT_CSV}}" ]]; then log "Output already exists. Job complete."; exit 0; fi
          rm -f "${{OUTPUT_CSV}}"
          # Atomic publish.
          PARTIAL_CSV="${{OUTPUT_CSV}}.partial.$$"
          rm -f "${{PARTIAL_CSV}}"
          trap 'rm -f "${{PARTIAL_CSV}}" 2>/dev/null || true' EXIT INT TERM
          if [[ "{params.use_container}" == "1" ]]; then
              [[ -f "{params.sif_image}" ]] || fail "Container not found: {params.sif_image}"
              MASK_REL="$(realpath --relative-to="{params.base}" "${{MASK_FILE}}")"
              PARTIAL_REL="$(realpath --relative-to="{params.base}" "${{PARTIAL_CSV}}")"
              SCRIPT_REL="$(realpath --relative-to="{params.base}" "{params.py_script}")"
              singularity exec --bind "{params.base}:/work" --env PYTHONUNBUFFERED="1" "{params.sif_image}" "{params.python_bin}" -u "/work/${{SCRIPT_REL}}" quantify-one --slide-name "${{SAMPLE_NAME}}" --marker-images-json {params.marker_images_json_container} --mask-file "/work/${{MASK_REL}}" --output-csv "/work/${{PARTIAL_REL}}"
          else
              python3 "{params.py_script}" quantify-one --slide-name "${{SAMPLE_NAME}}" --marker-images-json {params.marker_images_json_host} --mask-file "${{MASK_FILE}}" --output-csv "${{PARTIAL_CSV}}"
          fi
          [[ -s "${{PARTIAL_CSV}}" ]] || fail "Partial filtered quantification CSV not found or empty: ${{PARTIAL_CSV}}"
          mv -f "${{PARTIAL_CSV}}" "${{OUTPUT_CSV}}"
          [[ -s "${{OUTPUT_CSV}}" ]] || fail "Expected filtered quantification CSV not found or empty: ${{OUTPUT_CSV}}"
          if declare -F job_log_close_ok >/dev/null 2>&1; then
              job_log_close_ok "Filtered quantification table saved."
          else
              log "Job finished successfully"
          fi
        }} 2>&1 | tee -a "{params.log_file}"
        '''

rule filter_one_marker_mesmer:
    input:
        image=str(STITCHED_DIR / "{sample}" / "{sample}.ome.tif")
    output:
        tif=filtered_tif_path("mesmer", "{sample}", "{marker}")
    params:
        sample="{sample}",
        method="mesmer",
        marker="{marker}",
        channel=lambda wc: FILTER_MARKERS[wc.marker],
        log_file=lambda wc: str(LOG_ROOT / "filtering" / "mesmer" / wc.sample / f"filter_mesmer_{wc.marker}_{wc.sample}.log"),
        tophat_size=os.environ.get("TOPHAT_SIZE", "10"),
        sif_image=os.environ.get("FILTER_SIF_IMAGE"),
        py_script=os.environ.get("PY_SCRIPT_FILTER"),
        python_bin=os.environ.get("FILTER_PYTHON_BIN", "/opt/conda/envs/quantification/bin/python"),
        use_container=os.environ.get("FILTER_USE_CONTAINER", "1"),
        base=str(BASE),
    threads:
        filter_threads
    resources:
        mem_mb=filter_mem,
        runtime=filter_runtime,
        cpus_per_task=filter_threads,
        slurm_account=os.environ.get("SLURM_ACCOUNT", os.environ.get("PROJECT_ID", "")),
        slurm_partition="small"
    shell:
        _filter_rule_shell()

rule filter_one_marker_stardist:
    input:
        image=str(STITCHED_DIR / "{sample}" / "{sample}.ome.tif")
    output:
        tif=filtered_tif_path("stardist", "{sample}", "{marker}")
    params:
        sample="{sample}",
        method="stardist",
        marker="{marker}",
        channel=lambda wc: FILTER_MARKERS[wc.marker],
        log_file=lambda wc: str(LOG_ROOT / "filtering" / "stardist" / wc.sample / f"filter_stardist_{wc.marker}_{wc.sample}.log"),
        tophat_size=os.environ.get("TOPHAT_SIZE", "10"),
        sif_image=os.environ.get("FILTER_SIF_IMAGE"),
        py_script=os.environ.get("PY_SCRIPT_FILTER"),
        python_bin=os.environ.get("FILTER_PYTHON_BIN", "/opt/conda/envs/quantification/bin/python"),
        use_container=os.environ.get("FILTER_USE_CONTAINER", "1"),
        base=str(BASE),
    threads:
        filter_threads
    resources:
        mem_mb=filter_mem,
        runtime=filter_runtime,
        cpus_per_task=filter_threads,
        slurm_account=os.environ.get("SLURM_ACCOUNT", os.environ.get("PROJECT_ID", "")),
        slurm_partition="small"
    shell:
        _filter_rule_shell()

rule quantify_filtered_mesmer:
    input:
        marker_tifs=lambda wc: filtered_images_for_method_sample("mesmer", wc.sample),
        mask=segmentation_mask("mesmer", "{sample}", "nuclear")
    output:
        csv=filtered_csv_path("mesmer", "{sample}")
    params:
        sample="{sample}",
        method="mesmer",
        log_file=lambda wc: str(LOG_ROOT / "filtering" / "mesmer" / wc.sample / f"quant_filtered_mesmer_{wc.sample}.log"),
        marker_count=lambda wc: len(FILTER_MARKER_NAMES),
        marker_images_json_host=lambda wc: shlex.quote(marker_images_json_for("mesmer", wc.sample, container=False)),
        marker_images_json_container=lambda wc: shlex.quote(marker_images_json_for("mesmer", wc.sample, container=True)),
        sif_image=os.environ.get("FILTER_SIF_IMAGE"),
        py_script=os.environ.get("PY_SCRIPT_FILTER"),
        python_bin=os.environ.get("FILTER_PYTHON_BIN", "/opt/conda/envs/quantification/bin/python"),
        use_container=os.environ.get("FILTER_USE_CONTAINER", "1"),
        base=str(BASE),
    threads:
        filtered_quant_threads
    resources:
        mem_mb=filtered_quant_mem,
        runtime=filtered_quant_runtime,
        cpus_per_task=filtered_quant_threads,
        slurm_account=os.environ.get("SLURM_ACCOUNT", os.environ.get("PROJECT_ID", "")),
        slurm_partition="small"
    shell:
        _quant_filtered_shell()

rule quantify_filtered_whole_cell_mesmer:
    input:
        marker_tifs=lambda wc: filtered_images_for_method_sample("mesmer", wc.sample),
        mask=segmentation_mask("mesmer", "{sample}", "whole-cell")
    output:
        csv=filtered_csv_path("mesmer", "{sample}", "whole-cell")
    params:
        sample="{sample}",
        method="mesmer",
        log_file=lambda wc: str(LOG_ROOT / "filtering" / "mesmer" / wc.sample / f"quant_filtered_wc_mesmer_{wc.sample}.log"),
        marker_count=lambda wc: len(FILTER_MARKER_NAMES),
        marker_images_json_host=lambda wc: shlex.quote(marker_images_json_for("mesmer", wc.sample, container=False)),
        marker_images_json_container=lambda wc: shlex.quote(marker_images_json_for("mesmer", wc.sample, container=True)),
        sif_image=os.environ.get("FILTER_SIF_IMAGE"),
        py_script=os.environ.get("PY_SCRIPT_FILTER"),
        python_bin=os.environ.get("FILTER_PYTHON_BIN", "/opt/conda/envs/quantification/bin/python"),
        use_container=os.environ.get("FILTER_USE_CONTAINER", "1"),
        base=str(BASE),
    threads:
        filtered_quant_threads
    resources:
        mem_mb=filtered_quant_mem,
        runtime=filtered_quant_runtime,
        cpus_per_task=filtered_quant_threads,
        slurm_account=os.environ.get("SLURM_ACCOUNT", os.environ.get("PROJECT_ID", "")),
        slurm_partition="small"
    shell:
        _quant_filtered_shell()

rule quantify_filtered_stardist:
    input:
        marker_tifs=lambda wc: filtered_images_for_method_sample("stardist", wc.sample),
        mask=segmentation_mask("stardist", "{sample}")
    output:
        csv=filtered_csv_path("stardist", "{sample}")
    params:
        sample="{sample}",
        method="stardist",
        log_file=lambda wc: str(LOG_ROOT / "filtering" / "stardist" / wc.sample / f"quant_filtered_stardist_{wc.sample}.log"),
        marker_count=lambda wc: len(FILTER_MARKER_NAMES),
        marker_images_json_host=lambda wc: shlex.quote(marker_images_json_for("stardist", wc.sample, container=False)),
        marker_images_json_container=lambda wc: shlex.quote(marker_images_json_for("stardist", wc.sample, container=True)),
        sif_image=os.environ.get("FILTER_SIF_IMAGE"),
        py_script=os.environ.get("PY_SCRIPT_FILTER"),
        python_bin=os.environ.get("FILTER_PYTHON_BIN", "/opt/conda/envs/quantification/bin/python"),
        use_container=os.environ.get("FILTER_USE_CONTAINER", "1"),
        base=str(BASE),
    threads:
        filtered_quant_threads
    resources:
        mem_mb=filtered_quant_mem,
        runtime=filtered_quant_runtime,
        cpus_per_task=filtered_quant_threads,
        slurm_account=os.environ.get("SLURM_ACCOUNT", os.environ.get("PROJECT_ID", "")),
        slurm_partition="small"
    shell:
        _quant_filtered_shell()
