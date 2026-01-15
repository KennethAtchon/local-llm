#!/usr/bin/env python3
"""
Voice Agent - Local LLM with Natural Voice Input/Output
Uses Whisper for speech-to-text and Edge TTS for natural-sounding text-to-speech
Supports voice conversations and direct text-to-speech commands
"""

import os
import sys
import threading
import time
from pathlib import Path
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage
from memory import AgentMemory
import whisper
import sounddevice as sd
import soundfile as sf
import numpy as np
import tempfile
import requests
import edge_tts
import asyncio

# Load environment variables from .env file if it exists
load_dotenv()

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct-q5_K_M")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")  # tiny, base, small, medium, large
TTS_VOICE = os.getenv("TTS_VOICE", "en-US-AriaNeural")  # Edge TTS voice (very natural)
AUDIO_CHUNK = int(os.getenv("AUDIO_CHUNK", "1024"))
AUDIO_CHANNELS = int(os.getenv("AUDIO_CHANNELS", "1"))
AUDIO_RATE = int(os.getenv("AUDIO_RATE", "16000"))
RECORDING_TIMEOUT = float(os.getenv("RECORDING_TIMEOUT", "5.0"))  # seconds of silence before stopping

# Global instances
whisper_model = None
tts_voice = None  # Edge TTS voice name
llm = None
memory = None

def load_whisper_model():
    """Load the Whisper model for speech-to-text"""
    global whisper_model
    
    if whisper_model is not None:
        return whisper_model
    
    print(f"🔄 Loading Whisper model: {WHISPER_MODEL}...")
    try:
        whisper_model = whisper.load_model(WHISPER_MODEL)
        print("✅ Whisper model loaded!")
        return whisper_model
    except Exception as e:
        print(f"❌ Error loading Whisper model: {e}")
        print("\n💡 Make sure you have:")
        print("   - Internet connection for first-time download")
        print("   - Sufficient disk space (models range from ~75MB to ~3GB)")
        print("   - whisper package installed: pip install openai-whisper")
        raise

def init_tts_engine():
    """Initialize Edge TTS for natural-sounding speech"""
    global tts_voice
    
    if tts_voice is not None:
        return tts_voice
    
    print(f"🔄 Initializing Edge TTS (voice: {TTS_VOICE})...")
    try:
        # Test if we can list voices (requires internet)
        async def test_connection():
            voices = await edge_tts.list_voices()
            return voices
        
        # Run async test
        try:
            voices = asyncio.run(test_connection())
            print("✅ Edge TTS ready!")
            print(f"   Voice: {TTS_VOICE}")
            print("   (Using Microsoft Edge TTS - requires internet connection)")
            tts_voice = TTS_VOICE
            return tts_voice
        except Exception as e:
            print(f"⚠️  Warning: Could not connect to Edge TTS: {e}")
            print("   Edge TTS requires internet connection")
            print("   Falling back to default voice")
            tts_voice = TTS_VOICE
            return tts_voice
    except Exception as e:
        print(f"❌ Error initializing TTS: {e}")
        print("\n💡 Make sure you have:")
        print("   - edge-tts installed: pip install edge-tts")
        print("   - Internet connection (Edge TTS requires internet)")
        raise

def test_ollama_connection():
    """Test if Ollama is accessible"""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        return response.status_code == 200
    except Exception:
        return False

def init_llm():
    """Initialize the LLM"""
    global llm
    
    if llm is not None:
        return llm
    
    print(f"🔄 Connecting to Ollama ({OLLAMA_MODEL})...")
    
    # Test connection first
    if not test_ollama_connection():
        error_msg = f"❌ Cannot connect to Ollama at {OLLAMA_BASE_URL}"
        print(error_msg)
        print(f"\n💡 Make sure Ollama is running:")
        print("   Start it with: ollama serve")
        print("   Or run: ./run_voice_agent.sh (it will start Ollama automatically)")
        raise ConnectionError(error_msg)
    
    try:
        llm = ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.7,
        )
        # Test with a simple invocation to ensure model is available
        try:
            llm.invoke("test")
        except Exception as model_error:
            if "model" in str(model_error).lower() or "not found" in str(model_error).lower():
                print(f"⚠️  Model '{OLLAMA_MODEL}' may not be available")
                print(f"   Install it with: ollama pull {OLLAMA_MODEL}")
            raise
        print("✅ LLM ready!")
        return llm
    except ConnectionError:
        raise
    except Exception as e:
        print(f"❌ Error initializing LLM: {e}")
        print(f"\n💡 Make sure:")
        print(f"   - Ollama is running at {OLLAMA_BASE_URL}")
        print(f"   - Model '{OLLAMA_MODEL}' is installed (run: ollama pull {OLLAMA_MODEL})")
        raise

def record_audio(timeout_seconds=RECORDING_TIMEOUT):
    """
    Record audio from microphone until silence is detected
    
    Args:
        timeout_seconds: Seconds of silence before stopping recording
    
    Returns:
        Path to temporary WAV file with recorded audio
    """
    try:
        print("🎤 Recording... (speak now, silence to stop)")
        
        all_frames = []
        silent_chunks = 0
        silence_threshold = 0.01  # RMS threshold for silence (adjust based on microphone sensitivity)
        chunk_duration = AUDIO_CHUNK / AUDIO_RATE  # Duration of each chunk in seconds
        max_silent_chunks = int(timeout_seconds / chunk_duration)
        
        while True:
            # Record one chunk
            chunk = sd.rec(
                int(AUDIO_CHUNK),
                samplerate=AUDIO_RATE,
                channels=AUDIO_CHANNELS,
                dtype='float32'
            )
            sd.wait()  # Wait until recording is finished
            
            all_frames.append(chunk)
            
            # Calculate RMS amplitude
            rms = np.sqrt(np.mean(chunk**2))
            
            # Check for silence
            if rms < silence_threshold:
                silent_chunks += 1
                if silent_chunks > max_silent_chunks:
                    break
            else:
                silent_chunks = 0
        
        print("✅ Recording stopped")
        
        # Concatenate all frames
        audio_data = np.concatenate(all_frames, axis=0)
        
        # Save to temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_path = temp_file.name
        temp_file.close()
        
        # Save as WAV file
        sf.write(temp_path, audio_data, AUDIO_RATE)
        
        return temp_path
        
    except Exception as e:
        print(f"❌ Error recording audio: {e}")
        return None

def speech_to_text(audio_path: str) -> str:
    """
    Convert audio file to text using Whisper
    
    Args:
        audio_path: Path to audio file
    
    Returns:
        Transcribed text
    """
    if whisper_model is None:
        load_whisper_model()
    
    try:
        print("🔄 Transcribing audio...")
        result = whisper_model.transcribe(audio_path)
        text = result["text"].strip()
        print(f"📝 Transcribed: {text}")
        return text
    except Exception as e:
        print(f"❌ Error transcribing audio: {e}")
        return ""

async def _text_to_speech_async(text: str, output_path: str):
    """Async helper for Edge TTS"""
    communicate = edge_tts.Communicate(text, tts_voice)
    await communicate.save(output_path)

def text_to_speech(text: str, output_path: str = None):
    """
    Convert text to speech using Edge TTS and play it
    
    Args:
        text: Text to speak
        output_path: Optional path to save the audio file
    """
    if tts_voice is None:
        init_tts_engine()
    
    try:
        print(f"🔊 Speaking: {text[:50]}..." if len(text) > 50 else f"🔊 Speaking: {text}")
        
        # Generate speech to temporary file if no output path specified
        if output_path is None:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            output_path = temp_file.name
            temp_file.close()
            delete_after = True
        else:
            delete_after = False
        
        # Generate speech using Edge TTS (async)
        asyncio.run(_text_to_speech_async(text, output_path))
        
        # Play the audio
        # Edge TTS outputs MP3, convert to WAV for playback
        # Try to read MP3 directly (if soundfile supports it)
        try:
            audio_data, sample_rate = sf.read(output_path)
            sd.play(audio_data, samplerate=sample_rate)
            sd.wait()
        except Exception:
            # If MP3 reading fails, try using pydub to convert
            try:
                from pydub import AudioSegment
                from pydub.playback import play
                audio = AudioSegment.from_mp3(output_path)
                play(audio)
            except ImportError:
                # Fallback: use system player if available
                import subprocess
                import platform
                system = platform.system()
                if system == "Linux":
                    # Try common Linux audio players
                    played = False
                    for player in ["mpv", "mplayer", "ffplay", "paplay"]:
                        try:
                            subprocess.run([player, output_path], check=True, 
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            played = True
                            break
                        except (subprocess.CalledProcessError, FileNotFoundError):
                            continue
                    if not played:
                        print(f"⚠️  Could not play audio automatically")
                        print(f"   Audio file saved at: {output_path}")
                        print(f"   Install pydub for better MP3 support: pip install pydub")
                elif system == "Darwin":  # macOS
                    try:
                        subprocess.run(["afplay", output_path], check=True)
                    except:
                        print(f"⚠️  Could not play audio. File saved at: {output_path}")
                elif system == "Windows":
                    try:
                        subprocess.run(["start", output_path], shell=True, check=True)
                    except:
                        print(f"⚠️  Could not play audio. File saved at: {output_path}")
            except Exception as e:
                print(f"⚠️  Could not play audio: {e}")
                print(f"   Audio file saved at: {output_path}")
                print(f"   Install pydub for better MP3 support: pip install pydub")
        
        # Clean up temporary file if needed
        if delete_after:
            try:
                os.unlink(output_path)
            except:
                pass
                
    except Exception as e:
        print(f"❌ Error with text-to-speech: {e}")
        import traceback
        traceback.print_exc()

def process_with_llm(user_text: str, conversation_history: list) -> str:
    """
    Process user input with LLM and return response
    
    Args:
        user_text: User's text input
        conversation_history: List of previous messages
    
    Returns:
        LLM response text
    """
    if llm is None:
        init_llm()
    
    try:
        # Add user message to history
        conversation_history.append(HumanMessage(content=user_text))
        
        # Get response from LLM (use recent messages to avoid token limits)
        recent_messages = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
        response = llm.invoke(recent_messages)
        
        # Extract response text
        if hasattr(response, 'content'):
            response_text = response.content
        else:
            response_text = str(response)
        
        # Add AI response to history
        conversation_history.append(AIMessage(content=response_text))
        
        # Keep history manageable
        if len(conversation_history) > 50:
            conversation_history = conversation_history[-50:]
        
        return response_text.strip()
    except Exception as e:
        error_msg = f"Error processing with LLM: {e}"
        print(f"❌ {error_msg}")
        return error_msg

def main():
    """Main interactive loop for voice agent"""
    global memory
    
    print("=" * 60)
    print("Voice Agent - Local LLM with Voice Input/Output")
    print("=" * 60)
    print(f"LLM Model: {OLLAMA_MODEL}")
    print(f"Whisper Model: {WHISPER_MODEL}")
    print(f"Ollama URL: {OLLAMA_BASE_URL}")
    print("\nControls:")
    print("  - Press ENTER to start recording (voice input)")
    print("  - Type text and press ENTER for text input")
    print("  - Type 'say <text>' to have the AI speak text directly")
    print("  - Recording stops automatically after silence")
    print("  - Type 'exit' or 'quit' to stop")
    print("\nType 'exit' or 'quit' to stop\n")
    print("-" * 60)
    
    # Initialize memory system
    memory = AgentMemory()
    message_count = memory.get_message_count()
    if message_count > 0:
        print(f"\n📚 Loaded {message_count} messages from memory")
    
    # Load models
    try:
        load_whisper_model()
        init_tts_engine()
        init_llm()
    except Exception as e:
        print(f"\n❌ Failed to initialize: {e}")
        sys.exit(1)
    
    # Load conversation history
    conversation_history = memory.get_recent_messages(limit=50)
    
    print("\n✅ Voice agent ready!\n")
    
    # Greeting
    greeting = "Hello! I'm your voice assistant. Press Enter to start recording, or type your message."
    print(f"🤖 {greeting}")
    text_to_speech(greeting)
    
    while True:
        try:
            # Wait for user input (Enter key or text)
            user_input = input("\n📝 Press ENTER to record, or type a message: ").strip()
            
            if not user_input:
                # Record audio
                audio_path = record_audio()
                if audio_path is None:
                    print("❌ Failed to record audio")
                    continue
                
                # Transcribe
                user_text = speech_to_text(audio_path)
                
                # Clean up temporary file
                try:
                    os.unlink(audio_path)
                except:
                    pass
                
                if not user_text:
                    print("❌ Could not transcribe audio. Please try again.")
                    continue
            else:
                # Text input
                if user_input.lower() in ['exit', 'quit', 'q']:
                    goodbye = "Goodbye! It was nice talking with you."
                    print(f"\n👋 {goodbye}")
                    text_to_speech(goodbye)
                    break
                
                # Check for direct speak command: "say <text>"
                if user_input.lower().startswith('say '):
                    text_to_speak = user_input[4:].strip()
                    if text_to_speak:
                        print(f"\n🔊 Speaking: {text_to_speak}")
                        text_to_speech(text_to_speak)
                    else:
                        print("❌ No text provided. Usage: say <your text here>")
                    continue
                
                user_text = user_input
            
            # Save user message to memory
            memory.add_message("human", user_text)
            
            # Process with LLM
            print("\n🤖 Thinking...")
            response_text = process_with_llm(user_text, conversation_history)
            
            if response_text:
                print(f"\n🤖 Agent: {response_text}")
                
                # Save AI response to memory
                memory.add_message("ai", response_text)
                
                # Speak response
                text_to_speech(response_text)
            else:
                print("\n❌ No response from LLM")
                
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Try again or check the error above.")

if __name__ == "__main__":
    main()
