#!/usr/bin/env bash
# Verify the local MTPLX experiment lane without starting a model server.
set -euo pipefail

HOST="${MTPLX_HOST:-127.0.0.1}"
PORT="${MTPLX_PORT:-8000}"
MODELS_CSV="${MTPLX_MODELS:-Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed,Youssofal/Qwen3.8-27B-MTPLX-Optimized-Quality}"

say() {
  printf '\033[1m==>\033[0m %s\n' "$*"
}

die() {
  printf '\033[31merror:\033[0m %s\n' "$*" >&2
  exit 1
}

command -v mtplx >/dev/null 2>&1 || die "mtplx is not installed"
command -v curl >/dev/null 2>&1 || die "curl is required"
command -v lsof >/dev/null 2>&1 || die "lsof is required"

say "runtime"
mtplx --version
mtplx doctor

serve_help="$(mtplx serve --help)"
for flag in \
  '--profile {stable,performance-cold,sustained,turbo,exact,max-diagnostic}' \
  '--depth DEPTH' \
  '--generation-mode {mtp,ar,auto}' \
  '--context-window CONTEXT_WINDOW' \
  '--paged-kv-quantization, --paged-kv-quant, --kv-quant {off,q8,q4}' \
  '--mtp-quant-bits MTP_QUANT_BITS' \
  '--reasoning {auto,on,off}' \
  '--reasoning-effort {auto,low,medium,high,xhigh}' \
  '--preserve-thinking {auto,on,off,scoped}' \
  '--scheduler-mode {serial,cooperative,ar_batch,mtp_batch,mtp_cohort_experimental}' \
  '--batching-preset {solo,latency,agent,throughput}' \
  '--fan-mode {default,smart,max}'; do
  [[ "$serve_help" == *"$flag"* ]] || die "installed MTPLX is missing serve flag: $flag"
done
say "variation flags: profile, context, depth, generation mode, paged KV, and MTP quantization are available"

say "models"
IFS=',' read -r -a models <<< "$MODELS_CSV"
for model in "${models[@]}"; do
  [[ -n "$model" ]] || die "MTPLX_MODELS contains an empty model name"
  say "checking $model"
  mtplx inspect "$model" --require-mtp --json >/dev/null
done

if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  if curl -fsS --max-time 2 "http://$HOST:$PORT/v1/models" >/dev/null 2>&1; then
    say "port $PORT already serves a responsive MTPLX endpoint"
  else
    die "port $PORT is occupied by a non-MTPLX process; set MTPLX_PORT"
  fi
else
  say "port $PORT is available"
fi

say "host capacity"
if command -v memory_pressure >/dev/null 2>&1; then
  memory_pressure -Q || true
fi
df -h "$HOME"

say "ready: run one model at a time; the existing llama-swap service remains on 127.0.0.1:8080"
say "contexts: 32768 65536 131072 262144"
say "depths: AR (MTPLX_GENERATION_MODE=ar), D1, D2, D3"
say "paged KV: off, q8, q4"
