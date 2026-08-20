#!/usr/bin/env bash
# Pull the live machine config back into this repo, so the repo stays the
# versioned record of what is actually running.
#
# Direction is the opposite of install.sh:
#   install.sh  repo  -> machine
#   sync.sh     machine -> repo
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cp "$HOME/.config/llama-swap/config.yaml" "$REPO_DIR/llama-swap.config.yaml"
cp "$HOME/Library/LaunchAgents/com.ken.llama-swap.plist" "$REPO_DIR/com.ken.llama-swap.plist"

# Provider + agent only. The MCP block is excluded on purpose: it contains
# {env:...} API-key interpolation that has no business in a public repo.
python3 - "$REPO_DIR" <<'PY'
import collections, json, sys
from pathlib import Path

repo = Path(sys.argv[1])
src = json.loads(Path.home().joinpath(".config/opencode/opencode.json").read_text(),
                 object_pairs_hook=collections.OrderedDict)
out = collections.OrderedDict()
out["provider"] = {"local": src["provider"]["local"]}
if "local" in src.get("agent", {}):
    out["agent"] = {"local": src["agent"]["local"]}
target = repo / "opencode-provider.json"
target.write_text(json.dumps(out, indent=2) + "\n")
print("synced provider with models:", ", ".join(out["provider"]["local"]["models"]))
PY

echo "done. review with: git -C '$REPO_DIR/..' diff serving/"
