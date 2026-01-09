#!/bin/bash

# Image Generation Agent Setup and Run Script
# This script sets up the environment and runs Ollama + Image Generation Agent

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/venv"
OLLAMA_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
OLLAMA_IMAGE_MODEL="${OLLAMA_IMAGE_MODEL:-flux:1.1-pro}"

echo "=========================================="
echo "Image Generation Agent Setup & Run"
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

# Function to check if model exists
check_model() {
    if curl -s "$OLLAMA_URL/api/tags" | grep -q "$OLLAMA_IMAGE_MODEL"; then
        return 0
    else
        return 1
    fi
}

# Function to pull model if needed
ensure_model() {
    echo "📦 Checking for image generation model: $OLLAMA_IMAGE_MODEL"
    if check_model; then
        echo "✅ Image generation model already downloaded"
    else
        echo "📥 Downloading image generation model (this may take a while)..."
        echo "   Popular models:"
        echo "     - flux:1.1-pro (high quality, slower) - recommended"
        echo "     - flux:dev (good quality, faster)"
        echo "     - flux:schnell (fast, lower quality)"
        ollama pull "$OLLAMA_IMAGE_MODEL"
        echo "✅ Image generation model downloaded"
    fi
}

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
        echo "   Installing dependencies..."
        pip install --quiet -r requirements.txt
        echo "✅ Dependencies installed"
    else
        echo "⚠️  requirements.txt not found"
    fi
}

# Cleanup function
cleanup() {
    echo ""
    echo "🧹 Cleaning up..."
    if [ ! -z "$OLLAMA_PID" ]; then
        echo "   Stopping Ollama (PID: $OLLAMA_PID)..."
        kill "$OLLAMA_PID" 2>/dev/null || true
    fi
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
    
    # Start Ollama
    if ! start_ollama; then
        exit 1
    fi
    
    # Ensure image generation model is available
    ensure_model
    
    # Setup virtual environment
    setup_venv
    
    # Run the image generation agent
    echo ""
    echo "=========================================="
    echo "Starting Image Generation Agent..."
    echo "=========================================="
    echo ""
    
    # Add src to PYTHONPATH and run image generation agent
    export PYTHONPATH="$SCRIPT_DIR/src:$PYTHONPATH"
    python src/image_generation_agent.py
}

# Run main function
main
