#!/usr/bin/env bash
# Start a Qwen3.8 MTPLX experiment without touching llama-swap on :8080.
set -euo pipefail

MODEL="${MTPLX_MODEL:-Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed}"
HOST="${MTPLX_HOST:-127.0.0.1}"
PORT="${MTPLX_PORT:-8000}"
PROFILE="${MTPLX_PROFILE:-turbo}"
CONTEXT_WINDOW="${MTPLX_CONTEXT_WINDOW:-65536}"
DEPTH="${MTPLX_DEPTH:-3}"
GENERATION_MODE="${MTPLX_GENERATION_MODE:-mtp}"
KV_QUANTIZATION="${MTPLX_KV_QUANTIZATION:-off}"
MTP_QUANT_BITS="${MTPLX_MTP_QUANT_BITS:-}"
MTP_QUANT_GROUP_SIZE="${MTPLX_MTP_QUANT_GROUP_SIZE:-}"
MTP_QUANT_MODE="${MTPLX_MTP_QUANT_MODE:-}"
REASONING_EFFORT="${MTPLX_REASONING_EFFORT:-xhigh}"
REASONING="${MTPLX_REASONING:-auto}"
PRESERVE_THINKING="${MTPLX_PRESERVE_THINKING:-off}"
SCHEDULER_MODE="${MTPLX_SCHEDULER_MODE:-serial}"
BATCHING_PRESET="${MTPLX_BATCHING_PRESET:-solo}"
FAN_MODE="${MTPLX_FAN_MODE:-smart}"
REQUIRE_MAX_FANS="${MTPLX_REQUIRE_MAX_FANS:-0}"

say() {
  printf '\033[1m==>\033[0m %s\n' "$*"
}

die() {
  printf '\033[31merror:\033[0m %s\n' "$*" >&2
  exit 1
}

command -v mtplx >/dev/null 2>&1 || die \
  "mtplx not found. Install it with: brew install youssofal/mtplx/mtplx"

if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  existing_models="$(curl -fsS --max-time 2 "http://$HOST:$PORT/v1/models" 2>/dev/null || true)"
  if [[ "$existing_models" == *qwen3.8* || "$existing_models" == *Qwen3.8* || "$existing_models" == *mtplx* ]]; then
    say "MTPLX is already running at http://$HOST:$PORT"
    exit 0
  fi
  die "port $PORT is already in use; set MTPLX_PORT to another port"
fi

server_cmd=(
  mtplx serve
  --host "$HOST"
  --port "$PORT"
  --model "$MODEL"
  --profile "$PROFILE"
  --context-window "$CONTEXT_WINDOW"
  --depth "$DEPTH"
  --generation-mode "$GENERATION_MODE"
  --paged-kv-quantization "$KV_QUANTIZATION"
  --reasoning "$REASONING"
  --reasoning-effort "$REASONING_EFFORT"
  --preserve-thinking "$PRESERVE_THINKING"
  --scheduler-mode "$SCHEDULER_MODE"
  --batching-preset "$BATCHING_PRESET"
  --fan-mode "$FAN_MODE"
)

if [[ -n "$MTP_QUANT_BITS" ]]; then
  server_cmd+=(--mtp-quant-bits "$MTP_QUANT_BITS")
fi

if [[ -n "$MTP_QUANT_GROUP_SIZE" ]]; then
  server_cmd+=(--mtp-quant-group-size "$MTP_QUANT_GROUP_SIZE")
fi

if [[ -n "$MTP_QUANT_MODE" ]]; then
  server_cmd+=(--mtp-quant-mode "$MTP_QUANT_MODE")
fi

if [[ "$REQUIRE_MAX_FANS" == "1" ]]; then
  server_cmd+=(--require-max-fans)
fi

say "starting $MODEL"
say "endpoint: http://$HOST:$PORT/v1"
say "profile: $PROFILE, context: $CONTEXT_WINDOW, depth: $DEPTH, mode: $GENERATION_MODE"
say "kv: $KV_QUANTIZATION, reasoning: $REASONING/$REASONING_EFFORT, fans: $FAN_MODE"

"${server_cmd[@]}" &
server_pid=$!

cleanup() {
  if kill -0 "$server_pid" 2>/dev/null; then
    kill "$server_pid" 2>/dev/null || true
    wait "$server_pid" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

for _ in $(seq 1 60); do
  if ! kill -0 "$server_pid" 2>/dev/null; then
    wait "$server_pid" || true
    die "mtplx exited before becoming ready"
  fi

  if curl -fsS --max-time 2 "http://$HOST:$PORT/v1/models" >/dev/null 2>&1; then
    say "ready: http://$HOST:$PORT/v1"
    wait "$server_pid"
    exit $?
  fi

  sleep 1
done

die "mtplx did not become ready after 60 seconds"
