#!/bin/bash
# check_gpu.sh

echo "🔌 Checking NVIDIA GPU & CUDA environment..."
echo "--------------------------------------------"

if ! command -v nvidia-smi &> /dev/null; then
    echo "[WARNING] nvidia-smi tool not found in path."
    echo "This environment may not possess an active NVIDIA GPU, or drivers are not installed."
    echo "Recommended Fix: If running locally, install NVIDIA drivers. On LUMI/HPC, verify partition request allocations."
else
    echo "[PASS] nvidia-smi utility is online."
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
fi

# Check CUDA environment paths
if [ -z "${CUDA_HOME:-}" ]; then
    echo "[WARNING] CUDA_HOME environment variable is not defined."
else
    echo "[PASS] CUDA_HOME points to $CUDA_HOME"
fi

# PyTorch CUDA check
python3 -c "
try:
    import torch
    if torch.cuda.is_available():
        print(f'[PASS] PyTorch detects GPU: {torch.cuda.get_device_name(0)}')
    else:
        print('[FAIL] PyTorch is installed but cannot detect a CUDA-compatible GPU.')
except ImportError:
    print('[WARNING] PyTorch library not found in this Python package scope.')
"

exit 0
