#!/bin/bash
# Install PyTorch with ROCm in venv-qwen3-tts so Qwen3-TTS can use AMD GPU.
# Run once; then ./run_qwen_tts.sh will use GPU when available.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
VENV_DIR="$SCRIPT_DIR/venv-qwen3-tts"
PIP="$VENV_DIR/bin/pip"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating venv-qwen3-tts..."
    python3.12 -m venv "$VENV_DIR"
fi

echo "Detecting ROCm..."
ROCM_VERSION=""
if command -v rocminfo &>/dev/null; then
    if rpm -q rocm-core &>/dev/null; then
        # Fedora: e.g. rocm-core-6.4.4 -> 6.4
        ROCM_VERSION=$(rpm -q rocm-core 2>/dev/null | sed -n 's/rocm-core-\([0-9]*\.[0-9]*\).*/\1/p')
    fi
    [ -z "$ROCM_VERSION" ] && ROCM_VERSION="6.2"
fi

if [ -n "$ROCM_VERSION" ]; then
    # Use PyTorch ROCm index; 6.x wheels are under rocm6.0 or rocm6.2
    ROCM_INDEX="rocm6.2"
    case "$ROCM_VERSION" in
        5.*) ROCM_INDEX="rocm5.7" ;;
        6.0|6.1) ROCM_INDEX="rocm6.0" ;;
        6.*) ROCM_INDEX="rocm6.2" ;;
    esac
    echo "ROCm detected (${ROCM_VERSION}). Installing PyTorch with ${ROCM_INDEX}..."
    "$PIP" uninstall -y torch torchvision torchaudio 2>/dev/null || true
    "$PIP" install torch torchvision torchaudio --index-url "https://download.pytorch.org/whl/${ROCM_INDEX}"
else
    echo "No ROCm found. Installing default PyTorch (CPU/CUDA)..."
    "$PIP" uninstall -y torch torchvision torchaudio 2>/dev/null || true
    "$PIP" install torch torchvision torchaudio
fi

echo "Ensuring qwen-tts is installed..."
"$PIP" install -U qwen-tts

echo ""
echo "Done. Run: ./run_qwen_tts.sh"
echo "Device will be auto (GPU if PyTorch sees it, else CPU)."
