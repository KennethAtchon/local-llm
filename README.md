# Local LLM Agent with File Editing & Web Search

A Python agent that uses your local Ollama LLM with file editing and web search capabilities.

## Quick Start

**Easiest way - use the setup script:**
```bash
cd local-llm
./run.sh
```

This script will:
- ✅ Check if Ollama is running, start it if needed
- ✅ Download the model if not already present
- ✅ Create virtual environment if needed
- ✅ Install dependencies
- ✅ Run the agent

## Manual Setup

1. **Make sure Ollama is running:**
   ```bash
   ollama serve
   ```

2. **Create a virtual environment:**
   ```bash
   cd local-llm
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the agent:**
   ```bash
   python agent.py
   ```

## Configuration

Set environment variables to customize:

```bash
export OLLAMA_BASE_URL="http://localhost:11434"
export OLLAMA_MODEL="qwen3:8b"
```

## Usage Examples

- "Read the file README.md"
- "Search the web for Python best practices"
- "Write 'Hello World' to test.txt"
- "List files in the current directory"
- "Search for LangChain documentation and write a summary to langchain_summary.md"

## Available Tools

- **read_file**: Read content from files
- **write_file**: Write/edit files
- **search_web**: Search the internet using DuckDuckGo
- **list_directory**: List files in a directory
- **get_current_directory**: Get current working directory

## Troubleshooting

### Ollama Connection Error
If you see "Error connecting to Ollama", make sure:
- Ollama is running: `ollama serve`
- The model is downloaded: `ollama pull qwen3:8b`
- The base URL is correct (default: http://localhost:11434)

### Import Errors
If you get import errors, make sure you:
- Activated the virtual environment
- Installed all requirements: `pip install -r requirements.txt`
