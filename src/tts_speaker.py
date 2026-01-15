#!/usr/bin/env python3
"""
Simple Text-to-Speech Speaker
Just converts text to natural-sounding speech - no AI, no LLM needed
"""

import os
import sys
import asyncio
import tempfile
from pathlib import Path
from dotenv import load_dotenv
import edge_tts
import sounddevice as sd
import soundfile as sf

# Load environment variables from .env file if it exists
load_dotenv()

# Configuration
TTS_VOICE = os.getenv("TTS_VOICE", "en-US-AriaNeural")  # Edge TTS voice

def list_available_voices():
    """List all available Edge TTS voices"""
    async def _list_voices():
        voices = await edge_tts.list_voices()
        return voices
    
    try:
        voices = asyncio.run(_list_voices())
        print("\n📢 Available Voices:\n")
        for voice in voices:
            if voice['Locale'].startswith('en'):  # Show English voices
                print(f"  {voice['ShortName']:30} - {voice['Gender']:6} - {voice['Locale']}")
        return voices
    except Exception as e:
        print(f"❌ Error listing voices: {e}")
        return []

async def text_to_speech_async(text: str, voice: str, output_path: str):
    """Async helper for Edge TTS"""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

def speak_text(text: str, voice: str = TTS_VOICE, save_file: str = None):
    """
    Convert text to speech and play it
    
    Args:
        text: Text to speak
        voice: Voice to use (default: from TTS_VOICE env var)
        save_file: Optional path to save the audio file
    """
    try:
        print(f"🔊 Speaking: {text}")
        
        # Generate speech to temporary file if no output path specified
        if save_file is None:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            output_path = temp_file.name
            temp_file.close()
            delete_after = True
        else:
            output_path = save_file
            delete_after = False
        
        # Generate speech using Edge TTS (async)
        asyncio.run(text_to_speech_async(text, voice, output_path))
        
        # Play the audio
        try:
            audio_data, sample_rate = sf.read(output_path)
            sd.play(audio_data, samplerate=sample_rate)
            sd.wait()  # Wait until playback is finished
        except Exception:
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
        
        # Clean up temporary file if needed
        if delete_after:
            try:
                os.unlink(output_path)
            except:
                pass
        
        if save_file:
            print(f"💾 Audio saved to: {save_file}")
                
    except Exception as e:
        print(f"❌ Error with text-to-speech: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main interactive loop"""
    print("=" * 60)
    print("Text-to-Speech Speaker")
    print("=" * 60)
    print(f"Voice: {TTS_VOICE}")
    print("\nCommands:")
    print("  - Type text and press ENTER to speak it")
    print("  - Type 'list' to see available voices")
    print("  - Type 'voice <name>' to change voice (e.g., 'voice en-US-DavisNeural')")
    print("  - Type 'save <filename>' to save next audio to file")
    print("  - Type 'exit' or 'quit' to stop")
    print("\n" + "-" * 60)
    
    current_voice = TTS_VOICE
    save_next_to = None
    
    while True:
        try:
            user_input = input("\n📝 Enter text to speak: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            if user_input.lower() == 'list':
                list_available_voices()
                continue
            
            if user_input.lower().startswith('voice '):
                new_voice = user_input[6:].strip()
                if new_voice:
                    current_voice = new_voice
                    print(f"✅ Voice changed to: {current_voice}")
                    # Test the new voice
                    speak_text("Voice changed successfully.", current_voice)
                else:
                    print("❌ Please specify a voice name")
                continue
            
            if user_input.lower().startswith('save '):
                filename = user_input[5:].strip()
                if filename:
                    save_next_to = filename
                    if not filename.endswith('.mp3'):
                        save_next_to += '.mp3'
                    print(f"✅ Next audio will be saved to: {save_next_to}")
                else:
                    print("❌ Please specify a filename")
                continue
            
            # Speak the text
            speak_text(user_input, current_voice, save_next_to)
            save_next_to = None  # Reset after use
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
