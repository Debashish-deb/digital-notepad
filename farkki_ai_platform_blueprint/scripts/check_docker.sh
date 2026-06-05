#!/bin/bash
# check_docker.sh

echo "🐳 Checking Docker engine & socket permissions..."
echo "------------------------------------------------"

if ! command -v docker &> /dev/null; then
    echo "[FAIL] docker client tool not found in command paths."
    echo "Recommended Fix: Install Docker Desktop (macOS/Windows) or docker-ce (Linux)."
    exit 1
fi
echo "[PASS] docker binary resides in paths."

# Verify engine running
if ! docker info &> /dev/null; then
    echo "[FAIL] Docker daemon is offline or socket permissions are missing."
    echo "Recommended Fix: Start Docker service or add user to group: 'sudo usermod -aG docker \$USER'."
    exit 1
fi

echo "[PASS] Docker engine is running and responsive."
exit 0
