#!/bin/bash
# check_lumi_modules.sh

echo "💻 Checking LUMI HPC software modular structures..."
echo "--------------------------------------------------"

if ! command -v sbatch &> /dev/null; then
    echo "[WARNING] Slurm job controller 'sbatch' is not active in paths."
    echo "This indicates you are not logged into a Slurm login node (LUMI/HPC)."
else
    echo "[PASS] sbatch utility detected."
fi

# Check module subsystem
if ! command -v module &> /dev/null; then
    echo "[WARNING] 'module' subcommand system not found."
else
    echo "[PASS] module system online. Listing active loads:"
    module list 2>&1
fi

# Check folder layouts
if [ -d "/scratch" ]; then
    echo "[PASS] Active /scratch directory detected."
else
    echo "[WARNING] /scratch path not found. Ensure running on LUMI or target cluster partition."
fi

exit 0
