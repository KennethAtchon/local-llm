#!/usr/bin/env bash
# Deploy the local model serving stack from this repo onto the machine.
#
# The live config lives in home directories; this repo holds the versioned copy.
# Edit here, run this, and the machine picks it up. Use ./sync.sh to pull live
# changes back into the repo.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LABEL="com.ken.llama-swap"
PLIST_DEST="$HOME/Library/LaunchAgents/$LABEL.plist"
SWAP_DEST="$HOME/.config/llama-swap/config.yaml"
PORT="${LLAMA_SWAP_PORT:-8080}"

say() { printf '\033[1m==>\033[0m %s\n' "$*"; }
die() { printf '\033[31merror:\033[0m %s\n' "$*" >&2; exit 1; }

# --- preflight ---------------------------------------------------------------
command -v llama-server >/dev/null || die "llama-server missing. Run: brew install llama.cpp"

if ! command -v llama-swap >/dev/null && [ ! -x "$HOME/.local/bin/llama-swap" ]; then
  say "llama-swap not found; installing to ~/.local/bin"
  mkdir -p "$HOME/.local/bin"
  tmp="$(mktemp -d)"
  url="$(curl -s https://api.github.com/repos/mostlygeek/llama-swap/releases/latest \
    | python3 -c 'import sys,json; print(next(a["browser_download_url"] for a in json.load(sys.stdin)["assets"] if a["name"].endswith("darwin_arm64.tar.gz")))')"
  curl -sL -o "$tmp/ls.tgz" "$url"
  tar xzf "$tmp/ls.tgz" -C "$HOME/.local/bin" llama-swap
  xattr -dr com.apple.quarantine "$HOME/.local/bin/llama-swap" 2>/dev/null || true
  rm -rf "$tmp"
fi

# Metal 4 tensor API check. This is the whole reason we left LM Studio:
# without it, prompt processing on M5 runs ~2.9x slower (386 -> 133 t/s).
say "checking Metal 4 tensor API (GPU Neural Accelerators)"
if llama-server --version >/dev/null 2>&1; then
  probe="$(mktemp)"
  llama-bench -m /dev/null 2>&1 | grep -i "has tensor" > "$probe" || true
  if grep -qi "has tensor *= *true" "$probe"; then
    say "  has tensor = true"
  else
    printf '\033[33mwarn:\033[0m could not confirm tensor API. On an M5 with macOS >= 26.2 it should be true.\n'
    printf '      Verify with:  llama-bench -m <any.gguf> -p 8 -n 0 -v 2>&1 | grep "has tensor"\n'
  fi
  rm -f "$probe"
fi

# --- install -----------------------------------------------------------------
say "installing llama-swap config -> $SWAP_DEST"
mkdir -p "$(dirname "$SWAP_DEST")"
[ -f "$SWAP_DEST" ] && cp "$SWAP_DEST" "$SWAP_DEST.bak.$(date +%s)"
cp "$REPO_DIR/llama-swap.config.yaml" "$SWAP_DEST"

say "installing launchd service -> $PLIST_DEST"
mkdir -p "$(dirname "$PLIST_DEST")"
sed "s|/Users/ken|$HOME|g" "$REPO_DIR/com.ken.llama-swap.plist" > "$PLIST_DEST"

say "restarting service"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
# bootout is asynchronous; bootstrapping too soon fails with
# "Bootstrap failed: 5: Input/output error". Wait for it to actually unregister.
for _ in $(seq 1 25); do
  launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || break
  sleep 0.4
done
launchctl bootstrap "gui/$(id -u)" "$PLIST_DEST" \
  || die "launchctl bootstrap failed. Check: launchctl print gui/$(id -u)/$LABEL"

# --- verify ------------------------------------------------------------------
say "waiting for endpoint on :$PORT"
for _ in $(seq 1 30); do
  if curl -sf -m 2 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1; then
    say "up. models:"
    curl -s "http://127.0.0.1:$PORT/v1/models" \
      | python3 -c 'import sys,json; [print("   -",m["id"]) for m in json.load(sys.stdin)["data"]]'
    cat <<EOF

opencode wiring is NOT applied automatically — it would clobber your MCP block.
Merge serving/opencode-provider.json into ~/.config/opencode/opencode.json by hand,
then quit OpenCode.app with Cmd+Q and reopen (it caches config at launch).

In the model picker choose under "Local (llama.cpp)", NOT the built-in "LMStudio"
provider — that one is hardcoded to port 1234 and will refuse to connect.
EOF
    exit 0
  fi
  sleep 2
done
die "service did not come up on :$PORT — check /tmp/llama-swap.log"
