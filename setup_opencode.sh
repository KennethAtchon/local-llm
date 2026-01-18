#!/bin/bash

# OpenCode Setup Script
# This script installs and configures OpenCode CLI to work with local Ollama

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

OLLAMA_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3:8b}"

echo "=========================================="
echo "OpenCode Setup"
echo "=========================================="
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js first."
    echo "   On Fedora: sudo dnf install nodejs npm"
    exit 1
fi

NODE_VERSION=$(node --version)
echo "✅ Node.js version: $NODE_VERSION"
echo ""

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm not found. Please install npm first."
    echo "   On Fedora: sudo dnf install npm"
    exit 1
fi

# Check if Ollama is running
check_ollama() {
    if curl -s "$OLLAMA_URL/api/tags" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

if ! check_ollama; then
    echo "⚠️  Ollama is not running at $OLLAMA_URL"
    echo "   Start it with: ollama serve"
    echo "   Or run: ./run.sh (it will start Ollama automatically)"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Install OpenCode CLI globally
echo "📦 Installing OpenCode CLI..."
if command -v opencode &> /dev/null; then
    echo "✅ OpenCode is already installed"
    OPENCODE_VERSION=$(opencode --version 2>&1 || echo "unknown")
    echo "   Version: $OPENCODE_VERSION"
else
    echo "   Installing via npm (this may take a moment)..."
    sudo npm install -g opencode-cli
    echo "✅ OpenCode installed"
fi

echo ""

# Configure OpenCode to use Ollama
echo "⚙️  Configuring OpenCode to use Ollama..."
CONFIG_DIR="$HOME/.config/opencode"
mkdir -p "$CONFIG_DIR"

# Create or update opencode.json
CONFIG_FILE="$CONFIG_DIR/opencode.json"

if [ -f "$CONFIG_FILE" ]; then
    echo "   Found existing config at $CONFIG_FILE"
    echo "   Backing up to ${CONFIG_FILE}.backup"
    cp "$CONFIG_FILE" "${CONFIG_FILE}.backup"
fi

# Create configuration for Ollama
cat > "$CONFIG_FILE" << EOF
{
  "provider": "ollama",
  "baseURL": "$OLLAMA_URL",
  "model": "$OLLAMA_MODEL",
  "localOnly": true,
  "contextWindow": 32768
}
EOF

echo "✅ Configuration saved to $CONFIG_FILE"
echo ""
echo "Configuration:"
echo "  - Provider: ollama"
echo "  - Base URL: $OLLAMA_URL"
echo "  - Model: $OLLAMA_MODEL"
echo "  - Local Only: true"
echo "  - Context Window: 32768"
echo ""

# Test OpenCode
echo "🧪 Testing OpenCode installation..."
if opencode --version &> /dev/null; then
    echo "✅ OpenCode is working!"
    echo ""
    echo "=========================================="
    echo "Setup Complete!"
    echo "=========================================="
    echo ""
    echo "Usage:"
    echo "  opencode <your-request>"
    echo ""
    echo "Examples:"
    echo "  opencode 'read the file README.md'"
    echo "  opencode 'create a Python script that prints hello world'"
    echo "  opencode 'refactor the code in src/agent.py'"
    echo ""
    echo "Note: Make sure Ollama is running and the model '$OLLAMA_MODEL' is available"
    echo "      Install model with: ollama pull $OLLAMA_MODEL"
    echo ""
else
    echo "⚠️  OpenCode installation may have issues"
    echo "   Try running: opencode --version"
fi
