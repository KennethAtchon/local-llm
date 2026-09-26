# Qwen3.8 Local Coder Setup

This is the machine-specific setup runbook for the M5 Pro 48 GB system.
Run the relative `./serving/...` commands below from the repository root.
For the newer candidates, provenance and go/no-go trial protocol, see
[Qwen3.8 speed research (2026-09-26)](QWEN38_SPEED_RESEARCH_2026-09-26.md).
This runbook's MTPLX installation instructions were written before MTPLX
2.12.0 and Splash; check actual installed versions and supported flags before
following them. No newer candidate has passed the local acceptance gate.

## Recommended Architecture

Keep two independent profiles:

```text
OpenCode
   |
   +--> Stable aligned Qwen3.8 Q4 via llama-swap :8080
   |
   +--> MTPLX Qwen3.8 speed test :8000
   |
   +--> Optional uncensored MLX profile :8002
```

The stable server remains the default until a candidate passes both the
acceptance tests in this document and the matched coding-task comparison in
the September speed research.

## Profile A: Current Stable Server

The current live server is `llama-swap` at:

```text
http://127.0.0.1:8080/v1
```

The current Qwen model is:

```text
/Users/ken/.lmstudio/models/lmstudio-community/Qwen3.8-27B-GGUF/Qwen3.8-27B-Q4_K_M.gguf
```

The tested generation settings are:

```text
/opt/homebrew/bin/llama-server
  --host 127.0.0.1
  --port ${PORT}
  --jinja
  -fa on
  -ngl 99
  --no-webui
  -ctk q8_0
  -ctv q8_0
  -np 1
  --spec-type ngram-map-k4v
  -m Qwen3.8-27B-Q4_K_M.gguf
  -c 262144
  --chat-template-kwargs '{"reasoning_effort":"xhigh"}'
```

Do not remove these important settings:

- `--jinja` applies the Qwen chat template and enables parsed tool calls.
- `-ngl 99` offloads the model to Metal.
- `-fa on` enables flash attention.
- `-ctk q8_0 -ctv q8_0` reduces KV memory without the mixed-cache speed penalty.
- `-np 1` reserves one full context slot for a single user.
- `--spec-type ngram-map-k4v` gives a measured lossless speedup on this model.
- `reasoning_effort=xhigh` enables the highest supported Qwen3.8 reasoning level.

### Context Recommendation

The model supports 262,144 tokens, but that does not mean every turn should use
the full window.

Use:

| Workload | Context |
|---|---:|
| Interactive coding | 65,536 or 131,072 |
| Large repository investigation | 131,072 |
| Batch retrieval or long-context experiment | 262,144 |

If the server context changes, update the OpenCode model limit in the same change.
The server's `-c` value and OpenCode's `limit.context` must match.

The current OpenCode model block uses:

```json
{
  "context": 262144,
  "output": 32768
}
```

For a lower-latency interactive profile, use `131072` for context and `16384`
or `32768` for output. Keep the larger settings for batch work.

### Stable Server Operations

```bash
curl -s http://127.0.0.1:8080/v1/models
curl -s http://127.0.0.1:8080/running
open http://127.0.0.1:8080/ui
```

The service is managed by launchd. There is normally no manual start step.

```bash
launchctl kickstart -k gui/$(id -u)/com.ken.llama-swap
```

Do not stop this service casually. The second-brain semantic embedding model
also depends on it and will otherwise fall back to keyword-only retrieval.

## Profile B: MTPLX Speed A/B Test

MTPLX uses Qwen3.8's native MTP head and exposes an OpenAI-compatible server.
Both native-MTP variants were already installed and smoke-tested on this Mac
on August 23 (then MTPLX 2.9.1). **Do not re-pull them merely to perform the
first comparison.** The commands below document setup for a missing lane;
check the actual installed version and current upstream release before any
upgrade, and benchmark versions separately rather than silently replacing one.

```bash
brew install youssofal/mtplx/mtplx

mtplx doctor
mtplx inspect Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed
mtplx pull Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed
mtplx tune --model Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed --retune
```

This workspace now keeps both native-MTP variants locally. Run the repository
preflight before an experiment; it checks the installed runtime, both model
contracts, variation flags, port isolation, and host capacity:

```bash
./serving/mtplx_preflight.sh
```

The second model is the quality-first 8-bit build:

```bash
mtplx pull Youssofal/Qwen3.8-27B-MTPLX-Optimized-Quality
```

The model card reports a 20.4 GB download and a 23.6 GB measured peak for the
optimized speed build. It should fit this Mac more comfortably than the 8-bit
quality build.

After the model is pulled, the repo launcher starts the same profile and waits
until its API is ready:

```bash
./serving/start_mtplx_speed.sh
```

Override defaults without editing the script:

```bash
MTPLX_CONTEXT_WINDOW=32768 MTPLX_PROFILE=turbo ./serving/start_mtplx_speed.sh
```

Start it separately from llama-swap:

```bash
mtplx serve \
  --host 127.0.0.1 \
  --port 8000 \
  --model Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed \
  --profile sustained \
  --context-window 131072 \
  --reasoning-effort xhigh \
  --preserve-thinking off \
  --scheduler-mode serial \
  --batching-preset solo
```

Why these settings:

- `127.0.0.1` keeps the endpoint local.
- Port `8000` avoids the existing llama-swap service on port `8080`.
- `sustained` is more appropriate for a coding agent than a short benchmark lane.
- `131072` leaves more memory and latency headroom than 262K.
- `xhigh` selects the highest Qwen3.8 reasoning effort.
- `preserve-thinking off` avoids repeated full re-prefill for OpenCode clients that
  do not send hidden reasoning back in conversation history.
- `serial` and `solo` match a single-user workstation.

Check the served model identifier before adding the provider:

```bash
curl -s http://127.0.0.1:8000/v1/models
```

Add a separate OpenAI-compatible provider in OpenCode using the returned model ID:

```json
{
  "mtplx": {
    "npm": "@ai-sdk/openai-compatible",
    "name": "MTPLX Qwen3.8",
    "options": {
      "baseURL": "http://127.0.0.1:8000/v1"
    },
    "models": {
      "MODEL_ID_FROM_V1_MODELS": {
        "name": "Qwen3.8 MTPLX Optimized Speed",
        "tool_call": true,
        "limit": {
          "context": 131072,
          "output": 16384
        }
      }
    }
  }
}
```

Do not overwrite the whole OpenCode configuration. It also contains MCP
configuration and API-key interpolation.

## MTPLX Acceptance Test

Promote MTPLX only if all of these pass:

1. `GET /v1/models` returns the expected model.
2. A normal request returns HTTP 200.
3. A safe function schema produces parsed `tool_calls`, not raw `<tool_call>` text.
4. A ten-turn repository task completes without disconnects or malformed arguments.
5. `curl http://127.0.0.1:8000/health` remains healthy during the task.
6. `memory_pressure -Q` does not show sustained system pressure.
7. The end-to-end result is faster than the stable 14 to 17 t/s path.
8. Performance remains usable after the session grows beyond 32K context.

If any of these fail, keep the stable llama.cpp profile as the daily default.

## Profile C: Uncensored MLX Model

The uncensored model is an abliterated derivative. It removes refusal behavior;
it does not make the model more accurate or more capable at coding.

Use 4-bit for the practical default or 6-bit for better quality on this 48 GB Mac.
Do not use the 2-bit build for real work.

Create an isolated Python 3.11 environment. The system `python3` is 3.9.6, but
`/opt/homebrew/bin/python3.11` is available.

```bash
/opt/homebrew/bin/python3.11 -m venv ~/.venvs/qwen38-uncensored
source ~/.venvs/qwen38-uncensored/bin/activate
python -m pip install -U "mlx-vlm>=0.6.13" "mlx>=0.32" huggingface_hub
```

Download the 6-bit variant:

```bash
hf download orcarouter/Qwen3.8-27B-Uncensored-MLX \
  --include "6-bit/*" \
  --local-dir ~/models/qwen38-uncensored
```

Serve it on a separate local port:

```bash
python -m mlx_vlm server \
  --model ~/models/qwen38-uncensored/6-bit \
  --port 8002
```

Verify the listener before sending it any requests:

```bash
lsof -nP -iTCP:8002 -sTCP:LISTEN
```

Continue only if the listener is bound to `127.0.0.1:8002`, not `0.0.0.0:8002`.
If the installed MLX runtime exposes a host option, pass `--host 127.0.0.1`.

Security rules for this profile:

- Bind it to localhost only.
- Do not expose it to the LAN or the public internet.
- Do not give it shell execution, file-write, browser, or deployment tools by default.
- Use it as a manual research/chat profile unless a separate safety layer exists.
- Treat generated code and commands as untrusted until reviewed and tested.

## Tool Surface

Keep local tool schemas lean. The current serving tests found that very large
combined MCP schemas can exceed llama.cpp grammar limits and make every tool-call
request fail.

The local agent should start with:

- Repository file reading.
- Repository file editing.
- Directory listing.
- Test and formatter execution with approval.
- Git diff and status inspection.

Avoid loading every web, browser, and second-brain tool into the same local agent
request. Use a separate research-capable provider when those schemas are needed.

## Troubleshooting

### Raw Tool Markup

Check that `--jinja` is enabled. Without it, the model can emit raw markup instead
of parsed OpenAI tool calls.

### Wrong Provider

Use the configured `Local (llama.cpp)` provider. Do not use OpenCode's built-in
LM Studio provider, which is hardcoded to port `1234`.

### Memory Pressure

Lower context before lowering model quality:

1. Reduce context from 262K to 131K.
2. Reduce output from 32K to 16K.
3. Close unused model servers and browsers.
4. Keep the Q4 model as the daily default.

### MTPLX Repeated Prefill

Use `--preserve-thinking off` for clients that omit hidden reasoning from history.
This is a known OpenCode-style session-cache issue in MTPLX.

### Second-Brain Degradation

Keep the llama-swap service running with the `second-brain-embed` model available.
Stopping it degrades semantic retrieval to keyword-only behavior.

## Final Recommendation

Use the current Q4 GGUF through llama-swap for the daily aligned coder today.

Run MTPLX Optimized Speed as a separate A/B profile. If it passes the real
repository acceptance test, use it for fast interactive work and keep llama.cpp
for long-context or reliability-sensitive work.

Keep the uncensored MLX model separate and manual. It is an option for local
research, not a reason to remove the safety and tooling boundaries around the
daily coding agent.

## Sources

- Official model card: <https://huggingface.co/Qwen/Qwen3.8-27B>
- Official Qwen3.8 repository: <https://github.com/QwenLM/Qwen3.8>
- MTPLX repository: <https://github.com/youssofal/MTPLX>
- MTPLX optimized speed model: <https://huggingface.co/Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed>
- MTPLX session-reuse issue: <https://github.com/youssofal/MTPLX/issues/291>
- Uncensored MLX model: <https://huggingface.co/orcarouter/Qwen3.8-27B-Uncensored-MLX>
- Apple M5 Pro specifications: <https://support.apple.com/en-mide/126318>
