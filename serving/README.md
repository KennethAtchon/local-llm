# Serving stack

The local model server: `llama.cpp` + `llama-swap` on `127.0.0.1:8080`. Replaced
LM Studio on 2026-08-19.

Live config lives in home directories. This folder is the versioned copy.

```
./install.sh    repo    -> machine  (deploy + restart + verify)
./sync.sh       machine -> repo     (capture live changes)
```

| File | Deploys to |
|---|---|
| `llama-swap.config.yaml` | `~/.config/llama-swap/config.yaml` |
| `com.ken.llama-swap.plist` | `~/Library/LaunchAgents/com.ken.llama-swap.plist` |
| `opencode-provider.json` | merge by hand into `~/.config/opencode/opencode.json` |

`opencode-provider.json` is not installed automatically — the real file also holds
the MCP block with API-key interpolation, and overwriting it would destroy that.

## Operating it

There is no "start the server" step. `llama-swap` is a launchd service: it starts
at login and holds port 8080 permanently. Models load on first request naming
them and unload after their TTL.

```bash
launchctl bootout   gui/$(id -u)/com.ken.llama-swap                                  # stop
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.ken.llama-swap.plist     # start
launchctl kickstart -k gui/$(id -u)/com.ken.llama-swap                               # restart

curl -s localhost:8080/v1/models    # offered
curl -s localhost:8080/running      # loaded in RAM right now
open http://127.0.0.1:8080/ui       # web UI
```

Full runbook, including removal: `second-brain/knowledge-base/01-ai-and-tools/local-llm-operations.md`.

## Measured on this machine (M5 Pro, 48 GB)

| Model | pp2048 | tg128 |
|---|---|---|
| Qwen3.8-27B Q4_K_M (dense) | 386 t/s | 15.5 t/s |
| Qwen3.8-27B via MLX | 464 t/s | 16.8 t/s |

Qwen3.8-27B is the daily driver, chosen by Ken on quality grounds.

Qwen3-Coder-30B-A3B was benchmarked here (1521 t/s prefill, 91.9 t/s generation —
about 4x/6x the dense 27B) and then **removed at Ken's direction**; it was added
without being asked for. Do not reinstall it as a "faster option". The speed gap
is real and known; the model choice is settled.

MLX wins the microbenchmark but `mlx_lm.server` stalls under opencode's concurrent
streams — 14m25s agent turns vs 23s. It stays in the roster for one-shot use only.

Qwen3.8-27B runs at **262144** context (the model's trained max), 24.2 GB RSS, cold
start 2-3s. Verified at 105,860 tokens: correct needle retrieval, 7m58s. Prefill
degrades to ~225 t/s at that length, so full-context turns are batch work, not
interactive.

**Speculative decoding is on:** `--spec-type ngram-map-k4v`, no draft model needed,
+13% tok/s on the 27B (15.31 -> 17.36) and verified **lossless** — byte-identical
output vs baseline at temp 0. `ngram-simple` is faster still (23.49 t/s, +53%) but
was measured to CHANGE OUTPUT, so it is deliberately not used. `ngram-cache` is
slower than no speculation at all (14.72).

## Non-obvious things that will bite you

**`--jinja` is mandatory.** Without it the chat template is not applied, tool calls
come back as raw text instead of parsed `tool_calls`, and agent loops silently do
nothing.

**Metal 4 tensor API.** LM Studio's bundled llama.cpp fork failed the tensor-API
check on M5, so the GPU Neural Accelerators went unused — 386 vs 133 t/s prefill,
2.9x. Generation is unaffected (15.47 vs 15.46) because decode is memory-bandwidth
bound, which is exactly why the loss was invisible in chat. Confirm with
`has tensor = true`; A/B it with `GGML_METAL_TENSOR_DISABLE=1`.

**Do not raise ubatch.** Higher is slower here: 376 / 350 / 305 t/s at 512 / 1024 /
2048. Default 512 wins. This applies to generation models only — the embedding
model needs `-b 8192 -ub 8192` or it returns HTTP 500 on long chunks.

**KV cache `q8_0` on both K and V.** Same speed as f16, half the memory. Never mix
f16 and q8_0 — that collapses prefill to 121 t/s.

**`-np 1`.** llama-server reserves 4 slots by default; a single user wants one slot
holding the whole window.

**firecrawl's MCP breaks local tool calling.** Its tool schemas exceed llama.cpp's
`MAX_REPETITION_THRESHOLD` (2000) in the combined GBNF grammar, so every
tool-calling request 400s with `failed to parse grammar`. All tool schemas compile
into one grammar, so one bad server breaks all of them.

**opencode's built-in "LMStudio" provider** is hardcoded to `127.0.0.1:1234`
regardless of config. Picking a model under that heading gives
`ECONNREFUSED 127.0.0.1:1234`. Always pick under **Local (llama.cpp)**.

**The second brain depends on this server.** `second-brain-embed` serves the
semantic index. Stop the service and `brain_search` silently degrades to
keyword-only. Do not rename that model or its revision — vectors are stored keyed
by `<model>@<revision>`.

## Untested speedups

llama.cpp build 10470 `--spec-type` accepts `draft-dflash`, `draft-mtp`,
`draft-eagle3`, and `draft-simple` alongside the ngram modes. So DFlash
([arXiv 2602.06036](https://arxiv.org/abs/2602.06036)) **is** supported here —
earlier notes claiming otherwise were based on a stale GitHub issue.

What is missing is a draft checkpoint matching Qwen3.8-27B's tokenizer. Draft-model
speculation is where the 2-3x wins are; the ngram modes are the cheap fraction of
that. `empero-ai/Qwen3.8-2B-Distill-GGUF` is an untested candidate for
`draft-simple`. Circulating ~111 tok/s DFlash benchmarks are 4090 numbers and do
not transfer to Apple Silicon.
