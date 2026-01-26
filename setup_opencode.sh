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
    sudo npm install -g opencode-ai
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
# Note: baseURL needs /v1 for OpenAI-compatible API
OLLAMA_V1_URL="${OLLAMA_URL%/}/v1"
cat > "$CONFIG_FILE" << EOF
{
  "\$schema": "https://opencode.ai/config.json",
  "model": "ollama/$OLLAMA_MODEL",
  "provider": {
    "ollama": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Ollama (local)",
      "options": {
        "baseURL": "$OLLAMA_V1_URL"
      },
      "models": {
        "$OLLAMA_MODEL": {
          "name": "Qwen 3 8B",
          "tools": true,
          "limit": {
            "context": 32768,
            "output": 4096
          }
        }
      }
    }
  }
}
EOF

echo "✅ Configuration saved to $CONFIG_FILE"
echo ""
echo "Configuration:"
echo "  - Provider: ollama (using @ai-sdk/openai-compatible)"
echo "  - Base URL: $OLLAMA_V1_URL"
echo "  - Model: ollama/$OLLAMA_MODEL"
echo "  - Tools enabled: true"
echo "  - Context window: 32768"
echo ""
echo "⚠️  Note: Make sure Ollama is running and the model supports tool calling"
echo "   Some models may not work well with OpenCode's tool calling features"
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
    echo "  opencode run \"your coding request\""
    echo "  opencode [project-directory]  # Start interactive TUI"
    echo ""
    echo "Examples:"
    echo "  opencode run 'read the file README.md'"
    echo "  opencode run 'create a Python script that prints hello world'"
    echo "  opencode run 'refactor the code in src/agent.py'"
    echo "  opencode .  # Start interactive mode in current directory"
    echo ""
    echo "Note: Make sure Ollama is running and the model '$OLLAMA_MODEL' is available"
    echo "      Install model with: ollama pull $OLLAMA_MODEL"
    echo ""
else
    echo "⚠️  OpenCode installation may have issues"
    echo "   Try running: opencode --version"
fi
