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

- **`src/voice_agent.py`** - Voice agent with speech-to-text and text-to-speech
  - Voice input using Whisper (speech-to-text)
  - Voice output using Edge TTS (text-to-speech)
  - Supports both voice and text input
  - Includes long-term memory
  - Full AI conversation capabilities

- **`src/tts_speaker.py`** - Simple text-to-speech tool (no AI needed)
  - Just converts text to natural-sounding speech
  - No LLM, no Whisper, no AI required
  - Lightweight and fast
  - Perfect for simple TTS needs

- **`src/tts_qwen.py`** - Qwen3-TTS text-to-speech (CustomVoice)
  - Uses Qwen3-TTS model for high-quality, multi-speaker TTS
  - Requires separate venv: `venv-qwen3-tts` and `pip install qwen-tts`
  - Run via `./run_qwen_tts.sh`; supports custom text, language, speaker, and style

- **`src/memory.py`** - Long-term memory system
  - SQLite-based persistent storage for conversation history
  - Stores all user messages and AI responses
  - Loads conversation history on startup
  - Provides context to the LLM across sessions

### Configuration

- **`requirements.txt`** - Python dependencies for main agents (agent.py, voice_agent.py, image_generation_agent.py)
- **`requirements_webui.txt`** - Python dependencies for Open WebUI (requires Python 3.11-3.12, uses separate venv_webui)
- **`docker-compose.yml`** - Docker configuration for services
- **`run.sh`** - Script to run the CLI agent
- **`run_gui.sh`** - Script to run the GUI agent
- **`run_image_generation_agent.sh`** - Script to run the image generation agent
- **`run_voice_agent.sh`** - Script to run the voice agent
- **`run_tts_speaker.sh`** - Script to run the simple TTS speaker (no AI needed)
- **`run_qwen_tts.sh`** - Script to run Qwen3-TTS (CustomVoice; uses `venv-qwen3-tts`)
- **`setup_qwen_tts_rocm.sh`** - One-time setup: install PyTorch with ROCm in `venv-qwen3-tts` for AMD GPU
- **`run_open_webui.sh`** - Script to run Open WebUI (web interface for Ollama)
- **`setup_opencode.sh`** - Script to install and configure OpenCode CLI (coding assistant)

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
- `OLLAMA_MODEL` - Model to use for text agent (default: `qwen3:8b`)
- `OLLAMA_VISION_MODEL` - Vision model for image analysis (default: `qwen3-vl:8b`)
- `STABLE_DIFFUSION_MODEL` - Stable Diffusion model for image generation (default: `runwayml/stable-diffusion-v1-5`)
- `IMAGE_OUTPUT_DIR` - Directory for generated images (default: `./generated_images`)
- `DEVICE` - Device for image generation: auto, cuda, cpu, mps (default: `auto`)
- `NUM_INFERENCE_STEPS` - Number of inference steps (default: `25`, optimized for speed)
- `GUIDANCE_SCALE` - Guidance scale (default: `7.5`)
- `AGENT_MEMORY_DB` - Path to memory database (default: `./agent_memory.db`)
- `WHISPER_MODEL` - Whisper model for speech-to-text: tiny, base, small, medium, large (default: `base`)
- `TTS_VOICE` - Edge TTS voice for natural speech (default: `en-US-AriaNeural`)
- `AUDIO_CHUNK` - Audio chunk size for recording (default: `1024`)
- `AUDIO_CHANNELS` - Number of audio channels (default: `1` for mono)
- `AUDIO_RATE` - Audio sample rate in Hz (default: `16000`)
- `RECORDING_TIMEOUT` - Seconds of silence before stopping recording (default: `5.0`)
- `OPEN_WEBUI_PORT` - Port for Open WebUI web interface (default: `8080`)

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

### Voice Agent
```bash
./run_voice_agent.sh
# or
python src/voice_agent.py
```

### Simple TTS Speaker (No AI Required)
```bash
./run_tts_speaker.sh
# or
python src/tts_speaker.py
```

**Note**: The TTS speaker is a lightweight tool that just converts text to speech. No LLM, no Whisper, no AI needed - perfect if you just want natural-sounding text-to-speech!

### Qwen3-TTS (CustomVoice)
```bash
# One-time: create venv and install
python3.12 -m venv venv-qwen3-tts
venv-qwen3-tts/bin/pip install -U qwen-tts

# Optional: use AMD GPU (ROCm) instead of CPU
./setup_qwen_tts_rocm.sh

# Run (default example or pass text)
./run_qwen_tts.sh
./run_qwen_tts.sh "Hello, this is Qwen TTS."
./run_qwen_tts.sh -o my.wav -s Vivian -l Chinese "你好世界"
```

**Note**: Qwen3-TTS uses a dedicated Python 3.12 venv (`venv-qwen3-tts`) and the `qwen-tts` package. First run downloads the model. On AMD systems, run `./setup_qwen_tts_rocm.sh` once to install PyTorch with ROCm so the script uses GPU. Optional: install FlashAttention 2 for lower GPU memory (NVIDIA only).

### Open WebUI (Web Interface)
```bash
./run_open_webui.sh
```

**Note**: Open WebUI provides a modern web interface for interacting with your local Ollama models. It automatically starts Ollama if needed and connects to it. Access the interface at `http://localhost:8080` (or the port specified by `OPEN_WEBUI_PORT`).

### OpenCode (CLI Coding Assistant)
```bash
# First-time setup
./setup_opencode.sh

# Then use OpenCode
opencode run "your coding request"
# or start interactive TUI
opencode .
```

**Note**: OpenCode is a CLI-based coding assistant that works with local Ollama models. It's completely separate from Open WebUI and uses Node.js/npm. It can read files, write code, refactor, and perform coding tasks using your local LLM.

**Setup:**
- Requires Node.js and npm (install with: `sudo dnf install nodejs npm`)
- Automatically configures to use your local Ollama instance
- Uses the model specified by `OLLAMA_MODEL` environment variable (default: `qwen3:8b`)

**Usage Examples:**
- `opencode run "read the file README.md"`
- `opencode run "create a Python script that prints hello world"`
- `opencode run "refactor the code in src/agent.py"`
- `opencode run "add error handling to the main function"`
- `opencode .` - Start interactive TUI in current directory

**Configuration:**
- Config file: `~/.config/opencode/opencode.json`
- Model format: `ollama/qwen3:8b` (provider/model)
- Can be edited to change model, base URL, etc.

All agents maintain conversation history across sessions automatically.

## Main Agent Features

The main agent (`agent.py`) now includes image analysis capabilities:

- **Image Reading**: Automatically detects image file paths in user input
- **Vision Model Integration**: Uses Ollama vision models (qwen3-vl, llava, bakllava, etc.) for image analysis
- **Automatic Detection**: Detects image paths in various formats (quoted, absolute, relative)
- **Supported Formats**: JPG, JPEG, PNG, GIF, BMP, WEBP, TIFF

**Popular Vision Models:**
- `qwen3-vl:8b` - Qwen3 vision model, excellent OCR and spatial understanding (default)
- `qwen3-vl:2b` - Smaller, faster Qwen3 vision model
- `qwen3-vl:32b` - Larger, higher quality Qwen3 vision model
- `llava:7b` - Alternative vision model
- `llava:13b` - Higher quality, slower alternative
- `bakllava:1` - Alternative vision model

**Usage Examples:**
- "analyze this image: /path/to/image.jpg"
- "what's in this image: ./photo.png"
- "describe the image at /home/user/picture.jpg"
- "what colors are in 'image.png'?"

**Note**: Install a vision model first with: `ollama pull qwen3-vl:8b` (or your preferred vision model)

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

## Voice Agent Features

The voice agent provides natural voice-based interaction with the local LLM:
- **Speech-to-Text**: Uses OpenAI Whisper for accurate transcription (fully local)
- **Natural Text-to-Speech**: Uses Microsoft Edge TTS for high-quality, natural-sounding voice output
- **Dual Input**: Supports both voice recording and text input
- **Direct Speech**: Type `say <text>` to have the AI speak text directly without LLM processing
- **Automatic Recording**: Stops recording after detecting silence
- **Note**: Edge TTS requires internet connection for voice synthesis (but Whisper STT is local)

**Whisper Models:**
- `tiny` - Fastest, ~75MB, lower accuracy
- `base` - Good balance (default, ~150MB)
- `small` - Better accuracy, ~500MB
- `medium` - High accuracy, ~1.5GB
- `large` - Best accuracy, ~3GB

**System Requirements:**
- Microphone for voice input
- Audio output (speakers/headphones)
- On Linux: `portaudio19-dev` and `espeak` packages
- On macOS: Audio libraries included
- On Windows: SAPI5 (included with Windows)

**Usage:**
- Press ENTER to start recording (voice input)
- Speak into microphone - recording stops automatically after silence (default: 5 seconds)
- Type text and press ENTER for text input
- Type `say <text>` to have the AI speak text directly (e.g., `say Hello, how are you?`)
- Type 'exit' or 'quit' to stop

**Popular Edge TTS Voices (set via `TTS_VOICE` env var):**
- `en-US-AriaNeural` - Female, natural (default)
- `en-US-DavisNeural` - Male, natural
- `en-US-JaneNeural` - Female, friendly
- `en-US-GuyNeural` - Male, casual
- `en-GB-SoniaNeural` - British English, female
- `en-AU-NatashaNeural` - Australian English, female

To list all available voices, run: `edge-tts --list-voices`

**Note**: 
- First run downloads Whisper model (~75MB-3GB depending on model)
- Edge TTS requires internet connection but provides very natural voices
- No local model download needed for TTS (uses Microsoft's cloud service)

## Simple TTS Speaker

A lightweight text-to-speech tool that just converts text to natural-sounding speech:
- **No AI required**: No LLM, no Whisper, no complex setup
- **Natural voices**: Uses Microsoft Edge TTS for high-quality speech
- **Simple interface**: Just type text and it speaks
- **Voice selection**: Change voices on the fly
- **Save audio**: Optionally save audio files
- **Internet required**: Edge TTS needs internet connection

**Usage:**
- Type text and press ENTER to speak it
- Type `list` to see all available voices
- Type `voice <name>` to change voice (e.g., `voice en-US-DavisNeural`)
- Type `save <filename>` to save next audio to file
- Type `exit` to quit

**Perfect for**: Reading text aloud, simple announcements, testing voices, or any scenario where you just need text-to-speech without AI conversation.

## Qwen3-TTS (CustomVoice)

Local high-quality TTS using the Qwen3-TTS CustomVoice model:

- **Separate environment**: Uses `venv-qwen3-tts` (Python 3.12) and `qwen-tts` from PyPI
- **Speakers/languages**: Multiple built-in speakers (e.g. Ryan, Vivian) and languages; optional tone/style via `--instruct`
- **Output**: WAV file (default `output_custom_voice.wav`); override with `-o`
- **GPU**: Uses CUDA by default; use `--device cpu` or `--no-flash-attn` if needed

**Setup:** Create venv and install once: `python3.12 -m venv venv-qwen3-tts` then `venv-qwen3-tts/bin/pip install -U qwen-tts`. On AMD GPU, run `./setup_qwen_tts_rocm.sh` to install PyTorch with ROCm so TTS uses GPU.

## Open WebUI Features

Open WebUI provides a modern, user-friendly web interface for interacting with your local Ollama models:

- **Web-based Interface**: Access via browser at `http://localhost:8080` (configurable port)
- **Model Management**: View and switch between installed Ollama models
- **Chat Interface**: Clean, modern chat UI similar to ChatGPT
- **Local & Private**: All data stays on your machine - no external API calls
- **Auto-start Ollama**: Script automatically starts Ollama if not running
- **GPU Support**: Works with locally running Ollama that has GPU access
- **No Docker Required**: Runs natively in Python, easier to manage and debug

**Usage:**
- Run `./run_open_webui.sh` to start the web interface
- Open your browser to `http://localhost:8080`
- Select a model and start chatting
- All conversations are stored locally

**Note**: Open WebUI connects to Ollama running at `http://localhost:11434`. Make sure Ollama is running locally (not in Docker) if you need GPU acceleration.

## OpenCode Features

OpenCode is a CLI-based coding assistant that uses your local Ollama models for code generation, refactoring, and file operations:

- **CLI Interface**: Command-line tool for coding tasks
- **Local & Private**: All processing stays on your machine - no external API calls
- **File Operations**: Can read, write, and modify files
- **Code Generation**: Creates code from natural language descriptions
- **Refactoring**: Helps refactor and improve existing code
- **Tool Calling**: Uses models that support function/tool calling for agentic behavior
- **Separate from Open WebUI**: Independent Node.js-based tool, doesn't interfere with Python tools

**Setup:**
- Run `./setup_opencode.sh` to install and configure
- Requires Node.js and npm
- Automatically configures to use your local Ollama instance
- Config file: `~/.config/opencode/opencode.json`

**Usage:**
- `opencode run "your coding request"` - Natural language coding requests
- `opencode .` - Start interactive TUI in current directory
- Works best with models that support tool calling (instruct models)

**Note**: OpenCode requires models that support tool calling. Some smaller models may have limited tool support. Use instruct models or models specifically trained for agentic behavior for best results.

## Recent Changes

- **Added Qwen3-TTS**: `run_qwen_tts.sh` and `src/tts_qwen.py` for CustomVoice TTS (separate `venv-qwen3-tts` env)
- **Added OpenCode**: CLI coding assistant that works with local Ollama models (separate from Open WebUI)
- **Added Open WebUI**: Web interface for Ollama models, runs locally (not in Docker)
- **Added simple TTS speaker**: Lightweight text-to-speech tool (no AI needed)
- **Added voice agent**: New voice-based agent with speech-to-text and text-to-speech capabilities
- **Integrated image analysis**: Image reading capabilities now built into main agent (`agent.py`)
- **Added image generation agent**: New agent for creating images from text prompts using Stable Diffusion
- **Reorganized project structure**: All source code moved to `src/` directory
- **Added long-term memory**: SQLite-based persistent storage for all conversations
- **Context awareness**: Agent now has access to previous conversations
- **Cross-session continuity**: Conversations persist between agent restarts
