#!/bin/bash
# Run Qwen3-TTS (CustomVoice) using venv-qwen3-tts and src/tts_qwen.py

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/venv-qwen3-tts"
PYTHON="$VENV_DIR/bin/python"

if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Venv not found: $VENV_DIR"
    echo "   Create it and install qwen-tts:"
    echo "   python3.12 -m venv venv-qwen3-tts"
    echo "   venv-qwen3-tts/bin/pip install -U qwen-tts"
    exit 1
fi

if ! "$PYTHON" -c "import qwen_tts" 2>/dev/null; then
    echo "❌ qwen-tts not installed in venv-qwen3-tts"
    echo "   Run: venv-qwen3-tts/bin/pip install -U qwen-tts"
    exit 1
fi

mkdir -p "$SCRIPT_DIR/music_tts"
export PYTHONPATH="$SCRIPT_DIR/src:$PYTHONPATH"
exec "$PYTHON" src/tts_qwen.py "$@"
