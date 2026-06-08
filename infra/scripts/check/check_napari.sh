#!/bin/bash
# check_napari.sh

echo "🖥️ Checking Napari Visual & Qt configurations..."
echo "------------------------------------------------"

python3 -c "
try:
    import napari
    print(f'[PASS] napari package is installed (version {napari.__version__}).')
except ImportError:
    print('[FAIL] napari package is not installed in the active environment.')
    print('Recommended Fix: Run \"pip install napari[all]\" or \"mamba install -c conda-forge napari\".')
"

# Check GUI environment
if [ -z "${DISPLAY:-}" ]; then
    echo "[WARNING] No DISPLAY environment variable is set."
    echo "If running on remote workstations, ensure X11 forwarding is active (ssh -X/-Y) or use Offscreen plugin configs."
    echo "Headless rendering check: export QT_QPA_PLATFORM=offscreen"
else
    echo "[PASS] DISPLAY variable is set to: $DISPLAY"
fi

# Check PySide2 / PyQt5 availability
python3 -c "
backends = ['PyQt5', 'PySide2', 'PyQt6', 'PySide6']
found = []
for b in backends:
    try:
        __import__(b)
        found.append(b)
    except ImportError:
        pass
if found:
    print(f'[PASS] Supported Qt bindings found: {found}')
else:
    print('[FAIL] No PyQt or PySide bindings detected in environment. Napari will fail to launch.')
"

exit 0
