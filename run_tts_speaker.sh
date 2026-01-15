#!/bin/bash

# Simple TTS Speaker Setup and Run Script
# Just text-to-speech, no AI/LLM needed

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/venv"

echo "=========================================="
echo "Text-to-Speech Speaker Setup & Run"
echo "=========================================="
echo ""

# Setup virtual environment
setup_venv() {
    echo "🐍 Setting up Python virtual environment..."
    
    if [ ! -d "$VENV_DIR" ]; then
        echo "   Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
        echo "✅ Virtual environment created"
    else
        echo "✅ Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip
    echo "   Upgrading pip..."
    pip install --quiet --upgrade pip
    
    # Install/upgrade requirements (minimal - just TTS)
    echo "   Installing dependencies..."
    pip install --quiet edge-tts sounddevice soundfile numpy python-dotenv
    echo "✅ Dependencies installed"
}

# Cleanup function
cleanup() {
    echo ""
    echo "🧹 Cleaning up..."
    deactivate 2>/dev/null || true
}

# Trap to cleanup on exit
trap cleanup EXIT INT TERM

# Main execution
main() {
    # Check for Python
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python 3 not found. Please install Python 3 first."
        exit 1
    fi
    
    # Setup virtual environment
    setup_venv
    
    # Run the TTS speaker
    echo ""
    echo "=========================================="
    echo "Starting Text-to-Speech Speaker..."
    echo "=========================================="
    echo ""
    echo "💡 Edge TTS requires internet connection"
    echo "   (No local models to download!)"
    echo ""
    
    # Add src to PYTHONPATH and run TTS speaker
    export PYTHONPATH="$SCRIPT_DIR/src:$PYTHONPATH"
    python src/tts_speaker.py
}

# Run main function
main
