#!/bin/bash

# Open WebUI Setup and Run Script
# This script sets up the environment and runs Open WebUI with Ollama

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/venv_webui"  # Separate venv for open-webui (needs Python 3.11-3.12)
OLLAMA_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
OPEN_WEBUI_PORT="${OPEN_WEBUI_PORT:-8080}"

# Find Python 3.11 or 3.12
find_python() {
    if command -v python3.12 &> /dev/null; then
        echo "python3.12"
    elif command -v python3.11 &> /dev/null; then
        echo "python3.11"
    else
        echo ""
    fi
}

echo "=========================================="
echo "Open WebUI Setup & Run"
echo "=========================================="
echo ""

# Function to check if Ollama is running
check_ollama() {
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
        if check_ollama; then
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
            if check_ollama; then
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

# Setup virtual environment
setup_venv() {
    echo "🐍 Setting up Python virtual environment..."
    
    PYTHON_CMD=$(find_python)
    if [ -z "$PYTHON_CMD" ]; then
        echo "❌ Python 3.11 or 3.12 not found. open-webui requires Python 3.11-3.12"
        echo "   Install with: sudo dnf install python3.12"
        exit 1
    fi
    
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
    echo "   Using $PYTHON_VERSION"
    
    if [ ! -d "$VENV_DIR" ]; then
        echo "   Creating virtual environment with $PYTHON_CMD..."
        $PYTHON_CMD -m venv "$VENV_DIR"
        echo "✅ Virtual environment created"
    else
        echo "✅ Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Verify Python version in venv
    VENV_PYTHON_VERSION=$(python --version 2>&1)
    echo "   Virtual environment Python: $VENV_PYTHON_VERSION"
    
    # Upgrade pip
    echo "   Upgrading pip..."
    pip install --quiet --upgrade pip
}

# Cleanup function
cleanup() {
    echo ""
    echo "🧹 Cleaning up..."
    # Don't kill Ollama - let it keep running for other tools
    # Only deactivate the virtual environment
    deactivate 2>/dev/null || true
}

# Trap to cleanup on exit
trap cleanup EXIT INT TERM

# Main execution
main() {
    # Check for Python 3.11 or 3.12 (required for open-webui)
    PYTHON_CMD=$(find_python)
    if [ -z "$PYTHON_CMD" ]; then
        echo "❌ Python 3.11 or 3.12 not found. open-webui requires Python 3.11-3.12"
        echo "   Install with: sudo dnf install python3.12"
        exit 1
    fi
    
    # Start Ollama
    if ! start_ollama; then
        echo ""
        echo "❌ Failed to start Ollama"
        echo "   Try starting it manually: ollama serve"
        exit 1
    fi
    
    # Verify Ollama is still running before starting open-webui
    echo "   Verifying Ollama connection..."
    sleep 1
    if ! check_ollama; then
        echo "⚠️  Warning: Ollama connection check failed"
        echo "   Ollama may have stopped. Try starting it manually: ollama serve"
        echo "   Continuing anyway..."
    fi
    
    # Setup virtual environment
    setup_venv
    
    # Install/upgrade requirements
    if [ -f "requirements_webui.txt" ]; then
        echo "📦 Installing/updating open-webui dependencies..."
        pip install --quiet -r requirements_webui.txt
        echo "✅ Dependencies installed"
    else
        echo "⚠️  requirements_webui.txt not found, installing open-webui directly..."
        pip install --quiet open-webui
        echo "✅ open-webui installed"
    fi
    
    # Run Open WebUI
    echo ""
    echo "=========================================="
    echo "Starting Open WebUI..."
    echo "=========================================="
    echo ""
    echo "🌐 Open WebUI will be available at: http://localhost:$OPEN_WEBUI_PORT"
    echo "🔗 Connecting to Ollama at: $OLLAMA_URL"
    echo ""
    echo "Press Ctrl+C to stop"
    echo ""
    
    # Set environment variable for Ollama URL
    export OLLAMA_BASE_URL="$OLLAMA_URL"
    
    # Run open-webui
    open-webui serve --host 0.0.0.0 --port "$OPEN_WEBUI_PORT"
}

# Run main function
main
