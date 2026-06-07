# rules/illumination.smk

def illum_mem(wc, attempt):
    p = Path(raw_input_for_exp(wc))
    gib = file_size_gib(str(p))
    return auto_mem_mb(gib, "illum", attempt)

def illum_runtime(wc, attempt):
    p = Path(raw_input_for_exp(wc))
    gib = file_size_gib(str(p))
    return auto_runtime(gib, "illum", attempt)

def illum_threads(wc):
    return int(os.environ.get("ILLUMINATION_THREADS", "4"))

def java_xmx(wc):
    p = Path(raw_input_for_exp(wc))
    gb = file_size_gib(str(p))
    if gb <= 8: return "48g"
    elif gb <= 16: return "96g"
    elif gb <= 25: return "192g"
    elif gb <= 40: return "384g"
    else: return "700g"

rule illumination_basic:
    input:
        rcpnl=raw_input_for_exp
    output:
        ffp=str(ILLUM_DIR / "{sample}" / "{exp}-ffp.tif"),
        dfp=str(ILLUM_DIR / "{sample}" / "{exp}-dfp.tif")
    params:
        sample="{sample}",
        exp="{exp}",
        log_file=lambda wc: str(LOG_ROOT / "illumination" / wc.sample / f"{wc.exp}.log"),
        java_xmx=java_xmx,
        sif_image=os.environ.get("SIF_IMAGE_ILLUMINATION"),
        imagej_bin=os.environ.get("IMAGEJ_BIN"),
        ij_script=os.environ.get("IJ_SCRIPT"),
        lambda_flat=os.environ.get("LAMBDA_FLAT", "0.1"),
        lambda_dark=os.environ.get("LAMBDA_DARK", "0.01"),
        copy_input=os.environ.get("COPY_INPUT_TO_SCRATCH", "1"),
        base=str(BASE),
    threads:
        illum_threads
    resources:
        mem_mb=illum_mem,
        runtime=illum_runtime,
        cpus_per_task=illum_threads,
        slurm_account=os.environ.get("SLURM_ACCOUNT", os.environ.get("PROJECT_ID", "")),
        slurm_partition="small"
    shell:
        r'''
        set -euo pipefail

        mkdir -p \
          "$(dirname "{output.ffp}")" \
          "$(dirname "{output.dfp}")" \
          "$(dirname "{params.log_file}")"
        : > "{params.log_file}"

        {{
          [[ -f "{params.base}/scripts/lib/job_log_ui.sh" ]] && source "{params.base}/scripts/lib/job_log_ui.sh"

          if declare -F job_log_open >/dev/null 2>&1; then
              job_log_open \
                "Lighting correction (BaSiC)" \
                "Sample {params.sample} · imaging cycle {params.exp}" \
                "Estimating flat-field and dark-field profiles so illumination is even before stitching"
              log() {{ job_log "$@"; }}
              fail() {{ job_log_fail "$@"; exit 1; }}
          else
              log() {{ printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }}
              fail() {{ log "ERROR: $*"; exit 1; }}
          fi

          INPUT_PATH="{input.rcpnl}"
          FFP_FINAL="{output.ffp}"
          DFP_FINAL="{output.dfp}"

          SAMPLE_NAME="{params.sample}"
          EXP_NAME="{params.exp}"
          FILENAME="$(basename "${{INPUT_PATH}}")"

          SIF_IMAGE="{params.sif_image}"
          IMAGEJ_BIN="{params.imagej_bin}"
          IJ_SCRIPT="{params.ij_script}"

          THREADS="{threads}"
          JAVA_XMS="4g"
          JAVA_XMX="{params.java_xmx}"

          LAMBDA_FLAT="{params.lambda_flat}"
          LAMBDA_DARK="{params.lambda_dark}"

          COPY_INPUT_TO_SCRATCH="{params.copy_input}"

          SCRATCH_ROOT="${{LOCAL_SCRATCH:-/tmp}}/${{USER}}"
          SCRATCH_BASE="${{SCRATCH_ROOT}}/illum_${{SLURM_JOB_ID:-manual}}_${{EXP_NAME}}"

          SCRATCH_INPUT="${{SCRATCH_BASE}}/${{FILENAME}}"
          SCRATCH_FFP="${{SCRATCH_BASE}}/${{EXP_NAME}}-ffp.tif"
          SCRATCH_DFP="${{SCRATCH_BASE}}/${{EXP_NAME}}-dfp.tif"

          TMP_FFP="${{FFP_FINAL}}.tmp.$$"
          TMP_DFP="${{DFP_FINAL}}.tmp.$$"

          cleanup() {{
              rm -rf "${{SCRATCH_BASE}}"
          }}

          trap cleanup EXIT INT TERM

          [[ -f "${{INPUT_PATH}}" ]] || fail "Input file not found: ${{INPUT_PATH}}"
          [[ -f "${{SIF_IMAGE}}" ]] || fail "SIF image not found: ${{SIF_IMAGE}}"
          [[ -f "${{IJ_SCRIPT}}" ]] || fail "ImageJ script not found: ${{IJ_SCRIPT}}"

          mkdir -p "${{SCRATCH_BASE}}"

          if [[ "${{COPY_INPUT_TO_SCRATCH}}" == "1" ]]; then
              log "Copying input to local scratch"
              cp -f "${{INPUT_PATH}}" "${{SCRATCH_INPUT}}"
              RUN_INPUT="${{SCRATCH_INPUT}}"
          else
              RUN_INPUT="${{INPUT_PATH}}"
          fi

          log "Running headless ImageJ/BaSiC inside Singularity"

          singularity exec --cleanenv \
              --env JAVA_OPTS="-Xms${{JAVA_XMS}} -Xmx${{JAVA_XMX}}" \
              --env _JAVA_OPTIONS="-Xms${{JAVA_XMS}} -Xmx${{JAVA_XMX}}" \
              --env JVM_OPTS="-Xms${{JAVA_XMS}} -Xmx${{JAVA_XMX}}" \
              --env OMP_NUM_THREADS="${{THREADS}}" \
              --env OPENBLAS_NUM_THREADS=1 \
              --env MKL_NUM_THREADS=1 \
              --env NUMEXPR_NUM_THREADS=1 \
              --bind "${{SCRATCH_BASE}}:${{SCRATCH_BASE}}" \
              --bind "{params.base}:{params.base}" \
              "${{SIF_IMAGE}}" \
              "${{IMAGEJ_BIN}}" --ij2 --headless \
              --run "${{IJ_SCRIPT}}" \
              "filename='${{RUN_INPUT}}',output_dir='${{SCRATCH_BASE}}',experiment_name='${{EXP_NAME}}',lambda_flat=${{LAMBDA_FLAT}},lambda_dark=${{LAMBDA_DARK}}"

          [[ -s "${{SCRATCH_FFP}}" ]] || fail "Missing flat-field output in scratch"
          [[ -s "${{SCRATCH_DFP}}" ]] || fail "Missing dark-field output in scratch"

          log "Copying outputs from scratch to final destination"

          cp "${{SCRATCH_FFP}}" "${{TMP_FFP}}"
          cp "${{SCRATCH_DFP}}" "${{TMP_DFP}}"

          mv "${{TMP_FFP}}" "${{FFP_FINAL}}"
          mv "${{TMP_DFP}}" "${{DFP_FINAL}}"

          if declare -F job_log_close_ok >/dev/null 2>&1; then
              job_log_close_ok "Lighting profiles saved for this cycle."
          else
              log "Job finished successfully"
          fi

        }} 2>&1 | tee -a "{params.log_file}"
        '''
