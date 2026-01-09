#!/bin/bash

# Image Generation Agent Setup and Run Script
# This script sets up the environment and runs Stable Diffusion Image Generation Agent

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/venv"

echo "=========================================="
echo "Image Generation Agent Setup & Run"
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
        echo "   Note: PyTorch and Stable Diffusion models are large (~4GB+)"
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
    
    # Check for GPU (optional but recommended)
    if command -v nvidia-smi &> /dev/null; then
        echo "✅ NVIDIA GPU detected - will use CUDA for faster generation"
    elif command -v rocm-smi &> /dev/null; then
        echo "✅ AMD GPU detected - will use ROCm if available"
    else
        echo "⚠️  No GPU detected - will use CPU (slower but works)"
    fi
    
    # Setup virtual environment
    setup_venv
    
    # Run the image generation agent
    echo ""
    echo "=========================================="
    echo "Starting Image Generation Agent..."
    echo "=========================================="
    echo ""
    echo "💡 First run will download the Stable Diffusion model (~4GB)"
    echo "   This only happens once. Subsequent runs will be faster."
    echo ""
    
    # Add src to PYTHONPATH and run image generation agent
    export PYTHONPATH="$SCRIPT_DIR/src:$PYTHONPATH"
    python src/image_generation_agent.py
}

# Run main function
main
