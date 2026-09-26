# Qwen3.8 Local Coder Research

Research date: 2026-08-21

**Historical snapshot.** For the September 26 speed-candidate landscape,
release versions, new X reports, and a matched-trial decision, read the
[current speed research](QWEN38_SPEED_RESEARCH_2026-09-26.md). The local
measurements and model-choice discussion below remain relevant.

## Executive Decision

This Mac can run Qwen3.8-27B as a useful daily local coding agent.

Recommended model and runtime choices:

| Use case | Model | Runtime | Decision |
|---|---|---|---|
| Stable aligned daily agent | Current `Qwen3.8-27B-Q4_K_M.gguf` | `llama.cpp` + `llama-swap` | Keep as the default |
| Speed experiment | `Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed` | MTPLX 2.8.3 | A/B test on a separate port |
| Uncensored manual model | `orcarouter/Qwen3.8-27B-Uncensored-MLX` | `mlx-vlm` | Keep isolated from autonomous tools |
| Long batch work | Current Q4 GGUF at 262K context | `llama.cpp` | Use manually, not for every interactive turn |

Do not use the 2-bit uncensored build for coding. Its own model card warns that
quality degrades severely. Do not expect the M5 Max Twitter speeds to transfer
directly to this M5 Pro.

## Model Identity

"Qwen 3.8" refers to **Qwen3.8-27B**, not Qwen3-8B.

Qwen3.8-27B is:

- A 27B dense model with a native vision encoder.
- A hybrid architecture using gated DeltaNet linear attention and periodic full attention.
- A model with native 262,144-token context, extendable to 1M with scaling methods.
- A thinking model with `low`, `medium`, and `xhigh` reasoning effort.
- A model with tool-calling support and an MTP head.
- Licensed under Apache-2.0 by the official model card.

The official model card reports these coding and agentic benchmark results:

| Benchmark | Qwen3.8-27B score |
|---|---:|
| Terminal Bench 2.1 | 73.0 |
| SWE-bench Pro | 61.7 |
| NL2Repo-Bench | 42.3 |
| DeepSWE 1.1 | 42.2 |
| QwenSWEBench | 79.0 |
| LiveCodeBench v6 | 90.3 |

These are vendor-reported benchmark results. They indicate strong capability,
not guaranteed success on a real repository.

## This Machine

Hardware discovered locally:

| Item | Value |
|---|---|
| Computer | MacBook Pro, model `Mac17,8` |
| Chip | Apple M5 Pro |
| CPU | 18 cores: 6 super cores and 12 performance cores |
| GPU | 20-core integrated Metal 4 GPU |
| Unified memory | 48 GB |
| Memory bandwidth | 307 GB/s according to Apple's technical specifications |
| Operating system | macOS 26.6.2 |
| Free storage at research time | About 651 GB |

The 48 GB figure is unified memory, not dedicated VRAM. It is shared by the
model, KV cache, macOS, OpenCode, the editor, browsers, and other services.

After loading the current Qwen3.8 model, the machine reported about 18% system-wide
free memory. This is enough for the current Q4 setup, but it is not a good reason
to run an 8-bit model while also keeping a large development environment open.

## Existing Local Stack

The current machine already has a working local serving path:

- `llama-server` is `/opt/homebrew/bin/llama-server`.
- The installed llama.cpp build is 10470.
- `llama-swap` runs as a launchd service.
- The OpenAI-compatible endpoint is `http://127.0.0.1:8080/v1`.
- The second-brain embedding model also uses this service.
- Ollama is not installed.
- LM Studio is installed, but its server is not the current coding path.
- `mlx_lm` is installed, but its server previously stalled under OpenCode concurrent streams.

The currently offered Qwen model is:

```text
qwen/qwen3.8-27b@q4_k_m
17.74 GB on disk
Vision enabled
Tool-use metadata enabled
262,144-token maximum context
```

## Local Measurements

The machine-specific serving runbook records these measurements:

| Model/runtime | Prompt processing | Generation | Notes |
|---|---:|---:|---|
| Qwen3.8-27B Q4_K_M via llama.cpp | 386 t/s | 15.5 t/s | Stable daily driver |
| Qwen3.8-27B Q4 via MLX | 464 t/s | 16.8 t/s | Faster microbenchmark, unreliable for OpenCode concurrency |
| Qwen3-Coder-30B-A3B | 1521 t/s | 91.9 t/s | Previously benchmarked, then removed at Ken's direction |

The current Qwen3.8 configuration was also exercised directly on 2026-08-21:

- `reasoning_effort=xhigh` returned `reasoning_content`.
- A tool-call probe returned parsed `tool_calls` with `finish_reason: "tool_calls"`.
- A small request generated at about 14.4 t/s.

At 262K context, the current Qwen3.8 model has been verified with a 105,860-token
needle-retrieval test. It answered correctly, but the test took 7m58s. Long context
is therefore a batch capability, not an interactive-speed promise.

## Twitter Speed Claims

The specific Twitter post investigated was:

<https://x.com/LocalAiCherry/status/2090407651762917431>

It reports `Youssofal/Qwen3.8-27B-MTPLX-Optimized-Quality` on an M5 Max with 128 GB:

| Run | Reported speed |
|---|---:|
| 1.5K context | 40.9 t/s |
| 8.2K context | 33.1 t/s |
| Auto-tuned peak | 54.8 t/s |
| Base without MTP | 17.4 t/s |

The important qualifiers are:

- The machine was an M5 Max with 128 GB, not this M5 Pro.
- The quality build was 8-bit.
- The speedup came from MTPLX using the model's native MTP head.
- The results were short-context and single-stream measurements.
- They do not prove stable long-context OpenCode performance.

Apple lists 307 GB/s for this M5 Pro and 460 or 614 GB/s for M5 Max variants.
Decode is largely memory-bandwidth-bound, so the M5 Max numbers should not be
treated as this machine's expected speed.

## MTPLX Findings

MTPLX is an Apache-2.0 Apple Silicon runtime that exposes an OpenAI-compatible
server and supports parsed tool calls. At this document's August 21 research
date, the release page reported version 2.8.3 and Qwen3.8 support; this is
**not** a current-version claim (see the September speed research above).

The recommended Qwen3.8 MTPLX speed build reports:

- 4-bit dynamic quantization.
- 20.4 GB download size.
- 23.6 GB measured peak unified memory.
- Native MTP with depth 3.
- 58.7 t/s on an M5 Max for a medium-reasoning coding task.
- 35.1 and 37.3 t/s on the M5 Max for long `xhigh` answers.

The quality build reports:

- 8-bit dynamic quantization.
- 29.4 GB download size.
- 32.7 GB measured peak unified memory.
- 48.3 t/s on an M5 Max for a medium-reasoning coding task.
- 33.1 t/s on the M5 Max for long `xhigh` answers.

MTPLX issue history matters for an agent setup:

- A long-context performance issue was closed with fixes in version 2.8.0.
- An M5 Pro paged-attention slowdown was fixed in version 2.5.4.
- An open issue reports that clients which omit hidden reasoning from history can
  trigger a full context re-prefill on every turn. The documented workaround is
  `--preserve-thinking off`.

Therefore MTPLX is worth testing, but it should be added as a separate provider
until it passes a real multi-turn repository test on this machine.

## Model Options

### Current Q4 GGUF

This is the best current default because it is already downloaded, integrated,
and tested with the local tool-calling path.

Use it when stability, privacy, and reliable agent behavior matter more than
Twitter-level decode speed.

### MTPLX Optimized Speed

This is the best candidate for a speed upgrade. It should be tested on port 8000
while the stable llama-swap service remains on port 8080.

Use `xhigh` for maximum reasoning, but use a 131K interactive context rather
than reserving the full 262K window for every turn.

### MTPLX Optimized Quality

It technically fits in 48 GB, but its memory headroom is less comfortable once
OpenCode, macOS, browsers, and other models are running. It is not the best
always-on daily profile for this machine.

### Qwen3-Coder-30B-A3B

This older MoE coder model was much faster in local benchmarks, but it does not
provide the same `xhigh` thinking workflow. It was previously removed at Ken's
direction. Do not reinstall it merely because its benchmark speed is higher.

### Qwen3-Coder-Next

Qwen3-Coder-Next has 80B total parameters and 3B active parameters, 256K context,
and non-thinking-only behavior. Its Q4 files are too large for a comfortable
48 GB setup with context and development tools. It is not the right choice here.

## Uncensored Model Findings

The investigated uncensored model is:

<https://huggingface.co/orcarouter/Qwen3.8-27B-Uncensored-MLX>

It is an abliterated derivative. Abliteration removes refusal behavior; it does
not add knowledge or improve correctness.

Reported sizes:

| Variant | Approximate size | Assessment |
|---|---:|---|
| 4-bit | 15 GB | Practical default for an uncensored test |
| 6-bit | 22 GB | Better quality choice for 48 GB |
| 8-bit | 27.5 GB | More memory pressure; card recommends 64 GB |
| 2-bit | 8.7 GB | Explicitly reported as severely degraded |

The model card reports preserved vision, tool calling, 262K context, and zero
refusals on its own probes. It does not provide an independent coding benchmark.
It should therefore be treated as a manual research model, not the default
autonomous coding agent.

Keep it bound to localhost and do not give it shell, file-write, browser, or
other high-impact tools without an explicit safety layer.

## Feasibility Verdict

### Possible

- Local code navigation and explanation.
- Repository edits and test-driven fixes.
- Multi-step debugging with tools.
- High-reasoning architecture and implementation work.
- Private inference with no cloud model request.

### Not Guaranteed

- Frontier-cloud quality on every hard repository task.
- 40 to 55 t/s on this M5 Pro.
- Interactive performance at 100K+ context.
- Correct autonomous edits without tests and approvals.
- Better coding quality merely because a model is uncensored.

The practical goal is achievable: use the stable Q4 model now, then promote MTPLX
only if an on-machine repository test proves it is faster and equally reliable.

## Sources

- Official model card: <https://huggingface.co/Qwen/Qwen3.8-27B>
- Official Qwen3.8 repository: <https://github.com/QwenLM/Qwen3.8>
- Apple M5 Pro specifications: <https://support.apple.com/en-mide/126318>
- MTPLX repository: <https://github.com/youssofal/MTPLX>
- MTPLX releases: <https://mtplx.com/releases/>
- MTPLX optimized speed model: <https://huggingface.co/Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed>
- MTPLX optimized quality model: <https://huggingface.co/Youssofal/Qwen3.8-27B-MTPLX-Optimized-Quality>
- MTPLX session-reuse issue: <https://github.com/youssofal/MTPLX/issues/291>
- Uncensored MLX model: <https://huggingface.co/orcarouter/Qwen3.8-27B-Uncensored-MLX>
- Twitter speed report: <https://x.com/LocalAiCherry/status/2090407651762917431>
- Independent local-inference coverage: <https://thenewstack.io/qwen38-27b-local-inference/>

## Local Evidence

- `serving/README.md`
- `serving/llama-swap.config.yaml`
- `~/.config/opencode/opencode.json`
- `second-brain/knowledge-base/01-ai-and-tools/local-llm-operations.md`
