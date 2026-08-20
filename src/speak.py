#!/usr/bin/env python3
"""Local text-to-speech with a Kokoro -> Piper -> macOS `say` fallback chain.

COPIED FROM THE SECOND BRAIN. Source of truth remains
`second-brain/brain-tooling/scripts/brainctl.py` (functions `speak_with_kokoro`,
`speak_with_piper`, `speak_with_say`, `speak_text`). This file exists so the
local-llm workspace has TTS parity standalone. If you change speech behaviour,
change it in the second brain first, then re-copy here.

Model/voice assets are NOT duplicated: by default this reuses the runtime the
second brain already installed (`.brain-runtime/tts-venv`, `.brain-runtime/tts-models`).
Override with the SECOND_BRAIN_* environment variables below.

Backends, in order:
  1. kokoro - MLX-Audio (mlx-community/Kokoro-82M-bf16), best quality, Apple Silicon
  2. piper  - Piper neural voice (en_US-lessac-high.onnx)
  3. say    - macOS built-in, always available

Env overrides:
  SECOND_BRAIN_ROOT               vault root (default ~/Documents/ObsidianNotes/second-brain)
  SECOND_BRAIN_MLX_AUDIO_PYTHON   python with mlx_audio installed
  SECOND_BRAIN_KOKORO_MODEL       default mlx-community/Kokoro-82M-bf16
  SECOND_BRAIN_KOKORO_VOICE       default af_heart
  SECOND_BRAIN_PIPER_BIN          piper binary
  SECOND_BRAIN_PIPER_MODEL        piper .onnx voice model

Usage:
  ./src/speak.py --text "hello world"
  ./src/speak.py --file notes.md --output out.m4a
  ./src/speak.py --text "hi" --tts say --macos-voice Samantha --rate 200
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_SECOND_BRAIN_ROOT = Path.home() / "Documents" / "ObsidianNotes" / "second-brain"
SECOND_BRAIN_ROOT = Path(
    os.environ.get("SECOND_BRAIN_ROOT", DEFAULT_SECOND_BRAIN_ROOT)
).expanduser()

# Scratch space for this repo, so we never write into the vault.
RUNTIME_DIR = Path(__file__).resolve().parent.parent / ".tts-runtime"


def piper_paths() -> tuple[str | None, Path]:
    configured_binary = os.environ.get("SECOND_BRAIN_PIPER_BIN")
    candidates = [
        configured_binary,
        shutil.which("piper"),
        str(SECOND_BRAIN_ROOT / ".brain-runtime" / "tts-venv" / "bin" / "piper"),
    ]
    binary = next((item for item in candidates if item and Path(item).exists()), None)
    configured_model = os.environ.get("SECOND_BRAIN_PIPER_MODEL")
    model = (
        Path(configured_model).expanduser()
        if configured_model
        else SECOND_BRAIN_ROOT / ".brain-runtime" / "tts-models" / "en_US-lessac-high.onnx"
    )
    return binary, model


def mlx_audio_python() -> str | None:
    configured = os.environ.get("SECOND_BRAIN_MLX_AUDIO_PYTHON")
    candidates = [
        configured,
        str(SECOND_BRAIN_ROOT / ".brain-runtime" / "tts-venv" / "bin" / "python"),
        shutil.which("python3"),
    ]
    return next((item for item in candidates if item and Path(item).exists()), None)


def convert_audio_file(source: Path, destination: Path) -> None:
    output_format = {".mp4": "mp4f", ".m4a": "m4af"}.get(destination.suffix.lower())
    if output_format is None:
        raise ValueError("Audio conversion supports .mp4 and .m4a output paths.")
    converter = shutil.which("afconvert")
    if converter is None:
        raise FileNotFoundError("macOS afconvert is required for .mp4 and .m4a output.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.unlink(missing_ok=True)
    try:
        subprocess.run(
            [converter, "-f", output_format, "-d", "aac", str(source), "-o", str(destination)],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(details or f"afconvert failed for {destination}") from exc


def speak_with_kokoro(text: str, voice: str | None, output_path: Path | None = None) -> None:
    python = mlx_audio_python()
    afplay = shutil.which("afplay")
    if python is None or (output_path is None and afplay is None):
        raise FileNotFoundError("MLX-Audio, its Python runtime, or macOS afplay is not available.")
    model = os.environ.get("SECOND_BRAIN_KOKORO_MODEL", "mlx-community/Kokoro-82M-bf16")
    selected_voice = voice or os.environ.get("SECOND_BRAIN_KOKORO_VOICE", "af_heart")
    model_cache = SECOND_BRAIN_ROOT / ".brain-runtime" / "huggingface"
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=RUNTIME_DIR, prefix="kokoro-") as output_directory:
        command = [
            python, "-m", "mlx_audio.tts.generate",
            "--model", model,
            "--text", text,
            "--voice", selected_voice,
            "--lang_code", "a",
            "--output_path", output_directory,
            "--file_prefix", "speech",
            "--join_audio",
        ]
        environment = os.environ.copy()
        environment.setdefault("HF_HOME", str(model_cache))
        try:
            subprocess.run(command, check=True, capture_output=True, text=True, env=environment)
        except subprocess.CalledProcessError as exc:
            details = (exc.stderr or exc.stdout or "").strip()
            raise RuntimeError(details or "MLX-Audio failed to generate speech.") from exc
        audio_files = sorted(Path(output_directory).glob("*.wav"))
        if not audio_files:
            raise RuntimeError("MLX-Audio completed without producing a WAV file.")
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(audio_files[0], output_path)
        else:
            subprocess.run([afplay, str(audio_files[0])], check=True)


def speak_with_piper(text: str, output_path: Path | None = None) -> None:
    piper, model = piper_paths()
    afplay = shutil.which("afplay")
    if piper is None or not model.exists() or (output_path is None and afplay is None):
        raise FileNotFoundError("Piper, its voice model, or macOS afplay is not available.")
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        destination = output_path
        if destination is None:
            with tempfile.NamedTemporaryFile(dir=RUNTIME_DIR, suffix=".wav", delete=False) as output:
                temporary_name = output.name
            destination = Path(temporary_name)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [piper, "--model", str(model), "--output_file", str(destination)],
            input=f"{text}\n",
            text=True,
            check=True,
        )
        if output_path is None:
            subprocess.run([afplay, str(destination)], check=True)
    finally:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)


def speak_with_say(
    text: str, voice: str | None, rate: int | None, output_path: Path | None = None
) -> None:
    say = shutil.which("say")
    if say is None:
        raise SystemExit(
            "No local speech engine is available. Install Piper or use macOS with the 'say' command."
        )
    command = [say]
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        command.extend(["-o", str(output_path)])
    if voice:
        command.extend(["-v", voice])
    if rate:
        command.extend(["-r", str(rate)])
    subprocess.run([*command, text], check=True)


def speak_text(text: str, args: argparse.Namespace) -> str:
    requested_output = Path(args.output).expanduser() if getattr(args, "output", None) else None
    staging_path: Path | None = None
    output_path = requested_output
    if requested_output is not None and requested_output.suffix.lower() in {".mp4", ".m4a"}:
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=RUNTIME_DIR, suffix=".aiff", delete=False) as staging:
            staging_path = Path(staging.name)
        output_path = staging_path

    try:
        backend: str | None = None
        if args.tts in {"auto", "kokoro"}:
            try:
                speak_with_kokoro(text, args.voice, output_path)
                backend = "kokoro"
            except (FileNotFoundError, OSError, RuntimeError, subprocess.CalledProcessError) as exc:
                if args.tts == "kokoro":
                    raise SystemExit(f"Kokoro speech failed: {exc}") from exc
                print(f"Warning: Kokoro voice unavailable; trying Piper ({exc})", file=sys.stderr)
        if backend is None and args.tts in {"auto", "piper"}:
            try:
                speak_with_piper(text, output_path)
                backend = "piper"
            except (FileNotFoundError, OSError, subprocess.CalledProcessError) as exc:
                if args.tts == "piper":
                    raise SystemExit(f"Piper speech failed: {exc}") from exc
                print(
                    f"Warning: neural Piper voice unavailable; falling back to macOS say ({exc})",
                    file=sys.stderr,
                )
        if backend is None:
            speak_with_say(text, getattr(args, "macos_voice", None), args.rate, output_path)
            backend = "say"
        if staging_path is not None and requested_output is not None:
            try:
                convert_audio_file(staging_path, requested_output)
            except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
                raise SystemExit(f"Audio conversion failed: {exc}") from exc
        return backend
    finally:
        if staging_path is not None:
            staging_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read text aloud with a local TTS engine.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", help="Text to speak")
    source.add_argument("--file", help="Path to a text/Markdown file to read aloud")
    parser.add_argument(
        "--tts", choices=["auto", "kokoro", "piper", "say"], default="auto",
        help="Force a backend; default auto tries kokoro then piper then say",
    )
    parser.add_argument("--voice", help="Kokoro voice (default af_heart)")
    parser.add_argument("--macos-voice", help="macOS `say` voice, e.g. Samantha")
    parser.add_argument("--rate", type=int, help="macOS `say` words per minute")
    parser.add_argument("--output", help="Write audio to a file (.wav/.aiff/.m4a/.mp4) instead of playing")
    args = parser.parse_args()

    if args.text is not None:
        paragraph = " ".join(args.text.split())
    else:
        target = Path(args.file).expanduser()
        if not target.is_file():
            raise SystemExit(f"File does not exist: {target}")
        paragraph = " ".join(target.read_text(encoding="utf-8").split())
    if not paragraph:
        raise SystemExit("Text to speak must not be empty.")

    backend = speak_text(paragraph, args)
    print(f"spoken via: {backend}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
