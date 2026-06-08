#!/bin/bash
# check_python_env.sh

echo "🧬 Checking Python Environment..."
echo "---------------------------------"

# Check Python availability
if ! command -v python3 &> /dev/null; then
    echo "[FAIL] Python3 binary not found in path."
    echo "Recommended Fix: Install python3 via apt, brew, or conda."
    exit 1
fi

PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
echo "[PASS] Python3 is installed (version $PY_VERSION)."

# Check Virtual Environment active
if [ -z "${VIRTUAL_ENV:-}" ] && [ -z "${CONDA_DEFAULT_ENV:-}" ]; then
    echo "[WARNING] No active python virtualenv or conda environment detected!"
    echo "Recommended Fix: Run 'source .venv/bin/activate' or 'conda activate <env_name>'."
else
    echo "[PASS] Active environment: ${VIRTUAL_ENV:-${CONDA_DEFAULT_ENV}}"
fi

# Check package managers
if command -v mamba &> /dev/null; then
    echo "[PASS] mamba is available."
elif command -v conda &> /dev/null; then
    echo "[PASS] conda is available."
else
    echo "[WARNING] Neither conda nor mamba is installed."
fi

exit 0
