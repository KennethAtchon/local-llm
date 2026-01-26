"""
Qwen3-TTS: Simple text-to-speech using Qwen3-TTS CustomVoice model.

Requires: pip install qwen-tts (use the venv-qwen3-tts environment).
Run via: ./run_qwen_tts.sh [optional text to speak]
"""

import argparse
import datetime
import json
import os
import sys
import time

# -----------------------------------------------------------------------------
# Constants: change these to adjust defaults without touching CLI logic below.
# -----------------------------------------------------------------------------

# Output folder for generated WAV files.
# Examples: "music_tts", "output", "generated_audio", "./my_tts"
OUTPUT_DIR = "music_tts"

# Default filename (used with timestamp prefix when no -o is given).
# Examples: "output_custom_voice.wav", "speech.wav", "reading.wav"
DEFAULT_OUTPUT_FILENAME = "output_custom_voice.wav"

# Language. Use "Auto" to let the model detect.
# Examples: "English", "Chinese", "Japanese", "Korean", "Auto"
DEFAULT_LANGUAGE = "English"

# Speaker (CustomVoice model). Match to language for best quality.
# Examples (Chinese): "Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric"
# Examples (English): "Ryan", "Aiden"
# Examples (Japanese): "Ono_Anna" | (Korean): "Sohee"
DEFAULT_SPEAKER = "Aiden"

# Optional tone/style instruction. Empty = neutral.
# Examples: "", "Very happy.", "用特别愤怒的语气说", "Speak in a calm, slow voice.", "体现撒娇稚嫩的萝莉女声"
DEFAULT_INSTRUCT = "Autistic"

# HuggingFace model id.
# Examples: "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice", "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
#           "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign", "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
DEFAULT_MODEL = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"

# Device passed to CLI by default. "auto" = use PREFER_DEVICE / GPU if available.
# Examples: "auto", "cpu", "cuda:0", "cuda:1"
DEFAULT_DEVICE = "auto"

# When DEFAULT_DEVICE is "auto", this chooses the device. "cpu" often faster on AMD (avoids slow MIOpen).
# Examples: "auto", "cpu", "cuda", "cuda:0", "cuda:1"
PREFER_DEVICE = "cpu"

# Default text when no text is passed on the command line.
# Examples: "I owe my soul to the company store.", "Hello, world.", "其实我真的有发现，我是一个特别善于观察别人情绪的人。"
DEFAULT_EXAMPLE_TEXT = "I owe my soul to the company store."


def main():
    parser = argparse.ArgumentParser(description="Qwen3-TTS: generate speech from text (CustomVoice).")
    parser.add_argument(
        "text",
        nargs="*",
        default=None,
        help="Text to speak (default: built-in example).",
    )
    default_output = os.path.join(OUTPUT_DIR, datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + DEFAULT_OUTPUT_FILENAME)
    parser.add_argument(
        "-o", "--output",
        default=default_output,
        help=f"Output WAV path (default: {default_output}).",
    )
    parser.add_argument(
        "-l", "--language",
        default=DEFAULT_LANGUAGE,
        help=f"Language (default: {DEFAULT_LANGUAGE}). Use 'Auto' for auto-detect.",
    )
    parser.add_argument(
        "-s", "--speaker",
        default=DEFAULT_SPEAKER,
        help=f"Speaker name (default: {DEFAULT_SPEAKER}).",
    )
    parser.add_argument(
        "-i", "--instruct",
        default=DEFAULT_INSTRUCT,
        help="Optional instruction for tone/style (e.g. 'Very happy.').",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="HuggingFace model id (default: CustomVoice 1.7B).",
    )
    parser.add_argument(
        "--device",
        default=DEFAULT_DEVICE,
        help=f"Device: auto (GPU if available, else CPU), cuda:0, or cpu (default: {DEFAULT_DEVICE}). Use cpu on AMD/no NVIDIA GPU.",
    )
    parser.add_argument(
        "--flash-attn",
        action="store_true",
        help="Use FlashAttention 2 (faster, less VRAM). Requires: pip install flash-attn --no-build-isolation",
    )
    args = parser.parse_args()
    run_start_time = time.perf_counter()

    text = " ".join(args.text).strip() if args.text else DEFAULT_EXAMPLE_TEXT

    try:
        import torch
        import soundfile as sf
        from qwen_tts import Qwen3TTSModel
    except ImportError as e:
        print("Missing dependency. Activate venv-qwen3-tts and run: pip install -U qwen-tts", file=sys.stderr)
        raise SystemExit(1) from e

    device = args.device
    if device == "auto":
        pref = (PREFER_DEVICE or "").strip().lower()
        if pref == "cpu" or pref == "cuda" or pref.startswith("cuda:"):
            device = "cuda:0" if pref == "cuda" else pref
            print(f"Device auto: using {device} (PREFER_DEVICE)")
        elif torch.cuda.is_available():
            device = "cuda:0"
            print(f"Device auto: using {device}")
        else:
            device = "cpu"
            print("Device auto: using cpu")

    attn = "flash_attention_2" if args.flash_attn else "eager"
    dtype = torch.bfloat16
    if device == "cpu":
        dtype = torch.float32
        attn = "eager"

    def load_model(dev, dt, attn_impl):
        return Qwen3TTSModel.from_pretrained(
            args.model,
            device_map=dev,
            dtype=dt,
            attn_implementation=attn_impl,
        )

    print(f"Loading model: {args.model} (device={device}, attn={attn})...")
    try:
        model = load_model(device, dtype, attn)
    except RuntimeError as e:
        if "NVIDIA" in str(e) or "CUDA" in str(e).upper() or "cuda" in str(e):
            print(f"GPU not available ({e}), falling back to CPU...", file=sys.stderr)
            device = "cpu"
            dtype = torch.float32
            attn = "eager"
            model = load_model(device, dtype, attn)
        else:
            raise

    print(f"Generating speech: \"{text[:60]}{'...' if len(text) > 60 else ''}\"")
    wavs, sr = model.generate_custom_voice(
        text=text,
        language=args.language if args.language else "Auto",
        speaker=args.speaker,
        instruct=args.instruct or "",
    )
    out_path = args.output
    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    sf.write(out_path, wavs[0], sr)

    execution_time_seconds = time.perf_counter() - run_start_time
    output_duration_seconds = float(len(wavs[0])) / sr
    meta = {
        "output_path": out_path,
        "constants_used": {
            "OUTPUT_DIR": OUTPUT_DIR,
            "DEFAULT_OUTPUT_FILENAME": DEFAULT_OUTPUT_FILENAME,
            "DEFAULT_LANGUAGE": DEFAULT_LANGUAGE,
            "DEFAULT_SPEAKER": DEFAULT_SPEAKER,
            "DEFAULT_INSTRUCT": DEFAULT_INSTRUCT,
            "DEFAULT_MODEL": DEFAULT_MODEL,
            "DEFAULT_DEVICE": DEFAULT_DEVICE,
            "PREFER_DEVICE": PREFER_DEVICE,
            "DEFAULT_EXAMPLE_TEXT": DEFAULT_EXAMPLE_TEXT,
        },
        "run_settings": {
            "language": args.language or "Auto",
            "speaker": args.speaker,
            "instruct": args.instruct or "",
            "model": args.model,
            "device": device,
            "text": text,
            "sample_rate": sr,
        },
        "execution_time_seconds": round(execution_time_seconds, 3),
        "output_duration_seconds": round(output_duration_seconds, 3),
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    json_path = os.path.splitext(out_path)[0] + ".json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"Saved: {out_path} (sample rate {sr}, duration {output_duration_seconds:.2f}s, ran in {execution_time_seconds:.2f}s)")


if __name__ == "__main__":
    main()
