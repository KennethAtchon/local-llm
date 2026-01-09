# AI Orchestrator - Project Documentation

This document provides an overview of the local LLM agent system architecture and where to find key components.

## Project Structure

### Source Code (`src/` directory)

All source code is organized in the `src/` directory:

- **`src/agent.py`** - Main CLI agent with file editing, web search, and image analysis capabilities
  - Uses LangChain with Ollama for LLM interactions
  - Includes tools for file operations, web search, and directory navigation
  - **NEW**: Image reading and analysis using vision models (llava, etc.)
  - **NEW**: Now includes long-term memory via SQLite

- **`src/agent_gui.py`** - GUI version using Gradio
  - Same functionality as `agent.py` but with a web-based interface
  - **NEW**: Now includes long-term memory via SQLite

- **`src/image_generation_agent.py`** - Image generation agent
  - Generates images from text prompts
  - Uses Stable Diffusion (local, no API keys needed)
  - Saves generated images automatically
  - Includes long-term memory
  - Supports GPU acceleration (CUDA/ROCm) or CPU

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
- `STABLE_DIFFUSION_MODEL` - Stable Diffusion model for image generation (default: `runwayml/stable-diffusion-v1-5`)
- `IMAGE_OUTPUT_DIR` - Directory for generated images (default: `./generated_images`)
- `DEVICE` - Device for image generation: auto, cuda, cpu, mps (default: `auto`)
- `NUM_INFERENCE_STEPS` - Number of inference steps (default: `25`, optimized for speed)
- `GUIDANCE_SCALE` - Guidance scale (default: `7.5`)
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

### Image Generation Agent
```bash
./run_image_generation_agent.sh
# or
python src/image_generation_agent.py
```


All agents maintain conversation history across sessions automatically.

## Main Agent Features

The main agent (`agent.py`) now includes image analysis capabilities:

- **Image Reading**: Automatically detects image file paths in user input
- **Vision Model Integration**: Uses Ollama vision models (llava, bakllava, etc.) for image analysis
- **Automatic Detection**: Detects image paths in various formats (quoted, absolute, relative)
- **Supported Formats**: JPG, JPEG, PNG, GIF, BMP, WEBP, TIFF

**Popular Vision Models:**
- `llava:7b` - Fast, good quality (default)
- `llava:13b` - Higher quality, slower
- `bakllava:1` - Alternative vision model

**Usage Examples:**
- "analyze this image: /path/to/image.jpg"
- "what's in this image: ./photo.png"
- "describe the image at /home/user/picture.jpg"
- "what colors are in 'image.png'?"

**Note**: Install a vision model first with: `ollama pull llava:7b`

## Image Generation Agent Features

The image generation agent creates images from text prompts:
- Generate images from text descriptions
- Create multiple variations
- Save images automatically to `generated_images/` directory
- Uses Stable Diffusion for high-quality generation
- Runs locally - no API keys needed
- Supports GPU acceleration (CUDA/ROCm) or CPU

**Stable Diffusion Models:**
- `runwayml/stable-diffusion-v1-5` - Standard model (default, ~4GB)
- `stabilityai/stable-diffusion-2-1` - Version 2.1
- `CompVis/stable-diffusion-v1-4` - Original v1.4

**Note:** First run downloads the model (~4GB). Subsequent runs are faster.

**Usage Examples:**
- "a cat wearing a hat"
- "futuristic city at sunset, cyberpunk style"
- "watercolor painting of mountains and lakes"
- "generate 3 images of a robot in space"

**Note**: The run scripts automatically set up the Python path to include `src/` for imports.

## Recent Changes

- **Integrated image analysis**: Image reading capabilities now built into main agent (`agent.py`)
- **Added image generation agent**: New agent for creating images from text prompts using Stable Diffusion
- **Reorganized project structure**: All source code moved to `src/` directory
- **Added long-term memory**: SQLite-based persistent storage for all conversations
- **Context awareness**: Agent now has access to previous conversations
- **Cross-session continuity**: Conversations persist between agent restarts
