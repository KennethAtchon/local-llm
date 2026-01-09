# AI Orchestrator - Project Documentation

This document provides an overview of the local LLM agent system architecture and where to find key components.

## Project Structure

### Source Code (`src/` directory)

All source code is organized in the `src/` directory:

- **`src/agent.py`** - Main CLI agent with file editing and web search capabilities
  - Uses LangChain with Ollama for LLM interactions
  - Includes tools for file operations, web search, and directory navigation
  - **NEW**: Now includes long-term memory via SQLite

- **`src/agent_gui.py`** - GUI version using Gradio
  - Same functionality as `agent.py` but with a web-based interface
  - **NEW**: Now includes long-term memory via SQLite

- **`src/memory.py`** - Long-term memory system (NEW)
  - SQLite-based persistent storage for conversation history
  - Stores all user messages and AI responses
  - Loads conversation history on startup
  - Provides context to the LLM across sessions

### Configuration

- **`requirements.txt`** - Python dependencies
- **`docker-compose.yml`** - Docker configuration for services
- **`run.sh`** - Script to run the CLI agent
- **`run_gui.sh`** - Script to run the GUI agent

## Memory System

The memory system (`src/memory.py`) provides persistent long-term memory for the agent:

- **Database**: SQLite database stored at project root `agent_memory.db` (configurable via `AGENT_MEMORY_DB` env var)
- **Storage**: All conversations are stored with timestamps, roles (human/ai), and content
- **Retrieval**: Loads last 50 messages on startup for context
- **Features**:
  - Automatic message storage
  - Conversation history loading
  - Search functionality
  - Session management support

### Memory Database Schema

```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    role TEXT NOT NULL,  -- 'human' or 'ai'
    content TEXT NOT NULL,
    session_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
```

## How It Works

1. **Startup**: Agent loads recent conversation history (last 50 messages) from SQLite
2. **Interaction**: Each user message and AI response is saved to the database
3. **Context**: Full conversation history is passed to the LLM for context-aware responses
4. **Persistence**: All conversations persist across sessions

## Environment Variables

- `OLLAMA_BASE_URL` - Ollama server URL (default: `http://localhost:11434`)
- `OLLAMA_MODEL` - Model to use (default: `qwen2.5:7b-instruct-q5_K_M`)
- `AGENT_MEMORY_DB` - Path to memory database (default: `./agent_memory.db`)

## Usage

### CLI Agent
```bash
./run.sh
# or
python src/agent.py
```

### GUI Agent
```bash
./run_gui.sh
# or
python src/agent_gui.py
```

Both agents now maintain conversation history across sessions automatically.

**Note**: The run scripts automatically set up the Python path to include `src/` for imports.

## Recent Changes

- **Reorganized project structure**: All source code moved to `src/` directory
- **Added long-term memory**: SQLite-based persistent storage for all conversations
- **Context awareness**: Agent now has access to previous conversations
- **Cross-session continuity**: Conversations persist between agent restarts
