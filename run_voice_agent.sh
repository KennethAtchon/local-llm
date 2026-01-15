#!/bin/bash

# Voice Agent Setup and Run Script
# This script sets up the environment and runs the Voice Agent

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/venv"
OLLAMA_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5:7b-instruct-q5_K_M}"

echo "=========================================="
echo "Voice Agent Setup & Run"
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
    
    # Install/upgrade requirements
    if [ -f "requirements.txt" ]; then
        echo "   Installing dependencies (this may take a while)..."
        echo "   Note: Whisper models will be downloaded on first use"
        pip install --quiet -r requirements.txt
        echo "✅ Dependencies installed"
    else
        echo "⚠️  requirements.txt not found"
    fi
}

# Check for audio dependencies
check_audio_deps() {
    echo ""
    echo "🔊 Checking audio dependencies..."
    
    # Check for TTS dependencies
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Check for espeak (for text-to-speech)
        if command -v espeak &> /dev/null; then
            echo "✅ espeak found (for text-to-speech)"
        else
            # Try to detect package manager
            if command -v dnf &> /dev/null; then
                echo "⚠️  Warning: espeak may be needed for text-to-speech"
                echo "   Install with: sudo dnf install espeak espeak-data"
            elif command -v apt-get &> /dev/null; then
                echo "⚠️  Warning: espeak may be needed for text-to-speech"
                echo "   Install with: sudo apt-get install espeak espeak-data"
            else
                echo "⚠️  Warning: espeak may be needed for text-to-speech"
                echo "   Please install espeak using your package manager"
            fi
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "✅ macOS detected - audio libraries should be available"
    else
        echo "⚠️  Unknown OS - please ensure audio libraries are installed"
    fi
    
    # Note: sounddevice doesn't require system libraries, it uses PortAudio dynamically
    echo "✅ sounddevice will use system audio (no additional packages needed)"
}

# Function to check if Ollama is running
check_ollama_running() {
    if curl -s "$OLLAMA_URL/api/tags" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to start Ollama in background
start_ollama() {
    echo "🚀 Starting Ollama server..."
    if command -v ollama &> /dev/null; then
        # Check if already running
        if check_ollama_running; then
            echo "✅ Ollama is already running"
            return 0
        fi
        
        # Start Ollama in background
        nohup ollama serve > ollama.log 2>&1 &
        OLLAMA_PID=$!
        echo "   Started Ollama (PID: $OLLAMA_PID)"
        
        # Wait for Ollama to be ready
        echo "   Waiting for Ollama to be ready..."
        for i in {1..30}; do
            if check_ollama_running; then
                echo "✅ Ollama is ready!"
                return 0
            fi
            sleep 1
        done
        
        echo "❌ Ollama failed to start after 30 seconds"
        return 1
    else
        echo "❌ Ollama command not found. Please install Ollama first."
        echo "   Visit: https://ollama.ai"
        return 1
    fi
}

# Function to check if model exists
check_model() {
    if curl -s "$OLLAMA_URL/api/tags" | grep -q "$OLLAMA_MODEL"; then
        return 0
    else
        return 1
    fi
}

# Function to pull model if needed
ensure_model() {
    if check_model; then
        echo "✅ Model '$OLLAMA_MODEL' is available"
    else
        echo "📥 Model '$OLLAMA_MODEL' not found. Downloading..."
        if ollama pull "$OLLAMA_MODEL"; then
            echo "✅ Model downloaded successfully"
        else
            echo "❌ Failed to download model"
            return 1
        fi
    fi
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
    
    # Check for audio dependencies
    check_audio_deps
    
    # Start Ollama
    if ! start_ollama; then
        exit 1
    fi
    
    # Ensure model is available
    ensure_model
    
    # Setup virtual environment
    setup_venv
    
    # Run the voice agent
    echo ""
    echo "=========================================="
    echo "Starting Voice Agent..."
    echo "=========================================="
    echo ""
    echo "💡 First run will download Whisper model (~75MB-3GB depending on model size)"
    echo "   This only happens once. Subsequent runs will be faster."
    echo ""
    echo "💡 Edge TTS requires internet connection for voice synthesis"
    echo "   (Whisper speech-to-text works fully offline)"
    echo ""
    echo "💡 Make sure your microphone is connected and working"
    echo ""
    echo "💡 Use 'say <text>' command to have the AI speak text directly"
    echo ""
    
    # Add src to PYTHONPATH and run voice agent
    export PYTHONPATH="$SCRIPT_DIR/src:$PYTHONPATH"
    python src/voice_agent.py
}

# Run main function
main
