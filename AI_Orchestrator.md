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

- **`src/image_agent.py`** - Image analysis agent (NEW)
  - Specialized agent for analyzing and understanding images
  - Uses Ollama vision models (llava, bakllava, etc.)
  - Can describe images, answer questions about image content
  - Includes long-term memory via SQLite

- **`src/image_agent_gui.py`** - Image agent GUI version
  - Web-based interface for image analysis
  - Image upload support
  - Interactive image analysis with questions

- **`src/image_generation_agent.py`** - Image generation agent (NEW)
  - Generates images from text prompts
  - Uses Ollama flux models (flux:1.1-pro, flux:dev, flux:schnell)
  - Saves generated images automatically
  - Includes long-term memory

- **`src/image_generation_agent_gui.py`** - Image generation GUI (NEW)
  - Web interface for image generation
  - Real-time image display
  - Generate multiple variations

- **`src/memory.py`** - Long-term memory system
  - SQLite-based persistent storage for conversation history
  - Stores all user messages and AI responses
  - Loads conversation history on startup
  - Provides context to the LLM across sessions

### Configuration

- **`requirements.txt`** - Python dependencies
- **`docker-compose.yml`** - Docker configuration for services
- **`run.sh`** - Script to run the CLI agent
- **`run_gui.sh`** - Script to run the GUI agent
- **`run_image_agent.sh`** - Script to run the image analysis agent
- **`run_image_generation_agent.sh`** - Script to run the image generation agent

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
- `OLLAMA_MODEL` - Model to use for text agent (default: `qwen2.5:7b-instruct-q5_K_M`)
- `OLLAMA_VISION_MODEL` - Vision model for image analysis (default: `llava:7b`)
- `OLLAMA_IMAGE_MODEL` - Image generation model (default: `flux:1.1-pro`)
- `IMAGE_OUTPUT_DIR` - Directory for generated images (default: `./generated_images`)
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

### Image Analysis Agent
```bash
./run_image_agent.sh
# or
python src/image_agent.py
```

### Image Agent GUI
```bash
python src/image_agent_gui.py
```

### Image Generation Agent
```bash
./run_image_generation_agent.sh
# or
python src/image_generation_agent.py
```

### Image Generation Agent GUI
```bash
python src/image_generation_agent_gui.py
```

All agents maintain conversation history across sessions automatically.

## Image Agent Features

The image agent uses vision models to:
- Analyze and describe images in detail
- Answer questions about image content
- Identify objects, people, text, and scenes
- Provide visual descriptions

**Popular Vision Models:**
- `llava:7b` - Fast, good quality (default)
- `llava:13b` - Higher quality, slower
- `bakllava:1` - Alternative vision model

**Usage Examples:**
- "Analyze this image: /path/to/image.jpg"
- "What's in this image?"
- "Describe the colors and composition"

## Image Generation Agent Features

The image generation agent creates images from text prompts:
- Generate images from text descriptions
- Create multiple variations
- Save images automatically to `generated_images/` directory
- Uses Ollama flux models for high-quality generation

**Popular Image Generation Models:**
- `flux:1.1-pro` - Highest quality, slower (default)
- `flux:dev` - Good quality, balanced speed
- `flux:schnell` - Fast generation, lower quality

**Usage Examples:**
- "a cat wearing a hat"
- "futuristic city at sunset, cyberpunk style"
- "watercolor painting of mountains and lakes"
- "generate 3 images of a robot in space"

**Note**: The run scripts automatically set up the Python path to include `src/` for imports.

## Recent Changes

- **Added image generation agent**: New agent for creating images from text prompts using flux models
- **Image generation GUI**: Web interface for image generation with real-time display
- **Added image analysis agent**: Agent specialized for image understanding using vision models
- **Image agent GUI**: Web interface for image upload and analysis
- **Reorganized project structure**: All source code moved to `src/` directory
- **Added long-term memory**: SQLite-based persistent storage for all conversations
- **Context awareness**: Agent now has access to previous conversations
- **Cross-session continuity**: Conversations persist between agent restarts
