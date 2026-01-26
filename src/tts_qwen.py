"""
Qwen3-TTS: Text-to-speech with CustomVoice, VoiceDesign, or Base (clone) modes.

Requires: pip install qwen-tts (use the venv-qwen3-tts environment).
Run via: ./run_qwen_tts.sh [optional text to speak]
Modes: --mode custom_voice | voice_design | base (base needs --ref-audio and --ref-text).
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
DEFAULT_INSTRUCT = "Very happy."

# Mode: "custom_voice" (built-in speakers), "voice_design" (describe voice in text), "base" (clone from reference audio).
# Examples: "custom_voice", "voice_design", "base"
DEFAULT_MODE = "custom_voice"

# Model per mode (used when --model is not passed). Base and VoiceDesign use different checkpoints.
MODEL_CUSTOM_VOICE = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
MODEL_VOICE_DESIGN = "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
MODEL_BASE = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"

# Default HuggingFace model (fallback; usually overridden by MODEL_* per mode).
DEFAULT_MODEL = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"

# Base mode only: path/URL to reference audio and its transcript. Required for base mode unless x_vector_only.
# Examples ref_audio: "ref.wav", "https://example.com/sample.wav"
DEFAULT_REF_AUDIO = ""
DEFAULT_REF_TEXT = ""

# Device passed to CLI by default. "auto" = use PREFER_DEVICE / GPU if available.
# Examples: "auto", "cpu", "cuda:0", "cuda:1"
DEFAULT_DEVICE = "auto"

# When DEFAULT_DEVICE is "auto", this chooses the device. "cpu" often faster on AMD (avoids slow MIOpen).
# Examples: "auto", "cpu", "cuda", "cuda:0", "cuda:1"
PREFER_DEVICE = "auto"

# Default text when no text is passed on the command line.
# Examples: "I owe my soul to the company store.", "Hello, world.", "其实我真的有发现，我是一个特别善于观察别人情绪的人。"
DEFAULT_EXAMPLE_TEXT = "you come in for a 28 day trial, one day a week of workout, then you upsell a 28 day challenge/accelerator, they pay 1.99 or 2.99 for the enhanced version that has ( list out a bunch of features) and if they don't lose (the amount of fat), they get more of the free trial"

# Single JSON log file for all TTS runs (path relative to OUTPUT_DIR).
# Examples: "tts_log.json", "metadata.json", "runs.json"
TTS_LOG_JSON = "tts_log.json"


def main():
    parser = argparse.ArgumentParser(description="Qwen3-TTS: generate speech (custom_voice | voice_design | base).")
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
        help="Tone/style (CustomVoice/VoiceDesign) or leave for base. e.g. 'Very happy.'",
    )
    parser.add_argument(
        "--mode",
        default=DEFAULT_MODE,
        choices=("custom_voice", "voice_design", "base"),
        help=f"custom_voice | voice_design | base (default: {DEFAULT_MODE}).",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="HuggingFace model id. If unset, model is chosen from --mode.",
    )
    parser.add_argument(
        "--ref-audio",
        default=DEFAULT_REF_AUDIO,
        help="Base mode: path/URL to reference audio (or set DEFAULT_REF_AUDIO).",
    )
    parser.add_argument(
        "--ref-text",
        default=DEFAULT_REF_TEXT,
        help="Base mode: transcript of reference audio (or set DEFAULT_REF_TEXT).",
    )
    parser.add_argument(
        "--x-vector-only",
        action="store_true",
        help="Base mode: use only speaker embedding (ref_text not required; quality may drop).",
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
    mode = (args.mode or DEFAULT_MODE).strip().lower()
    if mode not in ("custom_voice", "voice_design", "base"):
        mode = "custom_voice"

    if mode == "base":
        ref_audio = (args.ref_audio or DEFAULT_REF_AUDIO or "").strip()
        ref_text = (args.ref_text or DEFAULT_REF_TEXT or "").strip()
        if not ref_audio:
            print("Base mode requires --ref-audio (or set DEFAULT_REF_AUDIO).", file=sys.stderr)
            sys.exit(1)
        if not args.x_vector_only and not ref_text:
            print("Base mode requires --ref-text (or set DEFAULT_REF_TEXT) unless --x-vector-only.", file=sys.stderr)
            sys.exit(1)
    else:
        ref_audio = (args.ref_audio or DEFAULT_REF_AUDIO or "").strip()
        ref_text = (args.ref_text or DEFAULT_REF_TEXT or "").strip()

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

    model_id = args.model
    if not model_id:
        model_id = {"custom_voice": MODEL_CUSTOM_VOICE, "voice_design": MODEL_VOICE_DESIGN, "base": MODEL_BASE}.get(mode, DEFAULT_MODEL)

    def load_model(dev, dt, attn_impl):
        return Qwen3TTSModel.from_pretrained(
            model_id,
            device_map=dev,
            dtype=dt,
            attn_implementation=attn_impl,
        )

    print(f"Loading model: {model_id} (mode={mode}, device={device}, attn={attn})...")
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

    lang = args.language if args.language else "Auto"
    print(f"Generating speech ({mode}): \"{text[:60]}{'...' if len(text) > 60 else ''}\"")
    if mode == "custom_voice":
        wavs, sr = model.generate_custom_voice(
            text=text,
            language=lang,
            speaker=args.speaker,
            instruct=args.instruct or "",
        )
    elif mode == "voice_design":
        wavs, sr = model.generate_voice_design(
            text=text,
            language=lang,
            instruct=args.instruct or "",
        )
    else:
        wavs, sr = model.generate_voice_clone(
            text=text,
            language=lang,
            ref_audio=ref_audio,
            ref_text=ref_text if not args.x_vector_only else None,
            x_vector_only_mode=args.x_vector_only,
        )
    out_path = args.output
    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    sf.write(out_path, wavs[0], sr)

    execution_time_seconds = time.perf_counter() - run_start_time
    output_duration_seconds = float(len(wavs[0])) / sr
    run_settings = {
        "mode": mode,
        "language": args.language or "Auto",
        "speaker": args.speaker,
        "instruct": args.instruct or "",
        "model": model_id,
        "device": device,
        "text": text,
        "sample_rate": sr,
    }
    if mode == "base":
        run_settings["ref_audio"] = ref_audio
        run_settings["ref_text"] = ref_text
        run_settings["x_vector_only"] = args.x_vector_only
    meta = {
        "output_path": out_path,
        "constants_used": {
            "OUTPUT_DIR": OUTPUT_DIR,
            "DEFAULT_OUTPUT_FILENAME": DEFAULT_OUTPUT_FILENAME,
            "DEFAULT_LANGUAGE": DEFAULT_LANGUAGE,
            "DEFAULT_SPEAKER": DEFAULT_SPEAKER,
            "DEFAULT_INSTRUCT": DEFAULT_INSTRUCT,
            "DEFAULT_MODE": DEFAULT_MODE,
            "MODEL_CUSTOM_VOICE": MODEL_CUSTOM_VOICE,
            "MODEL_VOICE_DESIGN": MODEL_VOICE_DESIGN,
            "MODEL_BASE": MODEL_BASE,
            "DEFAULT_MODEL": DEFAULT_MODEL,
            "DEFAULT_REF_AUDIO": DEFAULT_REF_AUDIO,
            "DEFAULT_REF_TEXT": DEFAULT_REF_TEXT,
            "DEFAULT_DEVICE": DEFAULT_DEVICE,
            "PREFER_DEVICE": PREFER_DEVICE,
            "DEFAULT_EXAMPLE_TEXT": DEFAULT_EXAMPLE_TEXT,
        },
        "run_settings": run_settings,
        "execution_time_seconds": round(execution_time_seconds, 3),
        "output_duration_seconds": round(output_duration_seconds, 3),
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    log_path = os.path.join(OUTPUT_DIR, TTS_LOG_JSON)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    entries = []
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                entries = json.load(f)
        except (json.JSONDecodeError, OSError):
            entries = []
    if not isinstance(entries, list):
        entries = []
    entries.append(meta)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    print(f"Saved: {out_path} (sample rate {sr}, duration {output_duration_seconds:.2f}s, ran in {execution_time_seconds:.2f}s)")


if __name__ == "__main__":
    main()
