#!/usr/bin/env python3
"""Compare local models on real tasks from an Azelify runbook.

The premise being tested is how these models are actually used here: no agent
implements from scratch, there is always a runbook, and the model's job is to
follow it faithfully against real repo context.

Tasks live in evals/tasks/*.json. Each names a runbook excerpt, optional repo
files for context, and an optional reference implementation for scoring.

  ./evals/run.py                       # all tasks, all models
  ./evals/run.py --task 01-text-gates  # one task
  ./evals/run.py --models qwen3.8-27b,qwen3-4b

Outputs land in evals/results/<task>/<model>.md and are meant to be read, not
scored automatically — where a reference exists the harness prints a diff to
make reading fast.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TASKS_DIR = ROOT / "tasks"
RESULTS_DIR = ROOT / "results"
ENDPOINT = "http://127.0.0.1:8080/v1/chat/completions"

SYSTEM = (
    "You are implementing a work package from an existing engineering runbook. "
    "The runbook is authoritative: follow its file paths, names, and constraints "
    "exactly. Do not redesign, do not add compatibility shims or deprecated "
    "aliases, and do not invent files it does not name. Output only the code it "
    "asks for, in a single fenced block per file, preceded by the file path as a "
    "comment. No commentary before or after."
)


def read_repo_file(repo: Path, rel: str, limit: int | None = None) -> str:
    path = repo / rel
    if not path.is_file():
        return f"[missing: {rel}]"
    text = path.read_text(encoding="utf-8", errors="replace")
    if limit and len(text) > limit:
        text = text[:limit] + f"\n... [truncated at {limit} chars]"
    return text


def build_prompt(task: dict, repo: Path) -> str:
    parts: list[str] = []
    runbook = task.get("runbook")
    if runbook:
        excerpt = read_repo_file(repo, runbook["file"])
        lines = excerpt.splitlines()
        lo, hi = runbook.get("lines", [1, len(lines)])
        parts.append(
            f"## Runbook excerpt — {runbook['file']} lines {lo}-{hi}\n\n"
            + "\n".join(lines[lo - 1 : hi])
        )
    for rel in task.get("context_files", []):
        parts.append(f"## Existing file — {rel}\n\n```ts\n{read_repo_file(repo, rel, 8000)}\n```")
    parts.append(f"## Your task\n\n{task['instruction']}")
    return "\n\n---\n\n".join(parts)


def call(model: str, prompt: str, max_tokens: int, timeout: int) -> tuple[str, dict]:
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.2,
            "seed": 7,
        }
    ).encode()
    req = urllib.request.Request(
        ENDPOINT, data=body, headers={"Content-Type": "application/json"}
    )
    t0 = time.time()
    data = json.load(urllib.request.urlopen(req, timeout=timeout))
    elapsed = time.time() - t0
    msg = data["choices"][0]["message"]
    usage = data.get("usage", {})
    stats = {
        "elapsed_s": round(elapsed, 1),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "tok_per_s": round((usage.get("completion_tokens") or 0) / elapsed, 1) if elapsed else 0,
        "finish": data["choices"][0].get("finish_reason"),
        "reasoning_chars": len(msg.get("reasoning_content") or ""),
    }
    return (msg.get("content") or ""), stats


def extract_code(text: str) -> str:
    blocks = re.findall(r"```(?:[a-zA-Z]*)\n(.*?)```", text, re.S)
    return "\n".join(b.strip() for b in blocks) if blocks else text.strip()


def normalize(code: str) -> list[str]:
    """Strip comments and blank lines so scoring compares behaviour, not prose."""
    out = []
    for line in code.splitlines():
        s = line.strip()
        if not s or s.startswith("//") or s.startswith("*") or s.startswith("/*"):
            continue
        out.append(s)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="qwen3.8-27b")
    ap.add_argument("--task", help="run a single task by stem")
    ap.add_argument("--repo", default="/Users/ken/Documents/workspace/Azelify")
    ap.add_argument("--max-tokens", type=int, default=2000)
    ap.add_argument("--timeout", type=int, default=1800)
    args = ap.parse_args()

    repo = Path(args.repo)
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    task_files = sorted(TASKS_DIR.glob("*.json"))
    if args.task:
        task_files = [p for p in task_files if p.stem == args.task]
    if not task_files:
        print("no tasks matched")
        return 1

    for tf in task_files:
        task = json.loads(tf.read_text())
        prompt = build_prompt(task, repo)
        out_dir = RESULTS_DIR / tf.stem
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "_prompt.md").write_text(prompt)
        print(f"\n=== {tf.stem} — {task['title']}")
        print(f"    prompt ~{len(prompt)//4} tok")

        reference = None
        if task.get("reference_file"):
            reference = read_repo_file(repo, task["reference_file"])

        for model in models:
            try:
                content, stats = call(model, prompt, args.max_tokens, args.timeout)
            except Exception as exc:  # noqa: BLE001
                print(f"    {model:20} FAILED: {exc}")
                continue
            code = extract_code(content)
            line = (
                f"    {model:20} {stats['elapsed_s']:6.1f}s  "
                f"{stats['tok_per_s']:5.1f} tok/s  "
                f"out={stats['completion_tokens']}  think={stats['reasoning_chars']}c"
            )
            if reference:
                ratio = difflib.SequenceMatcher(
                    None, normalize(reference), normalize(code)
                ).ratio()
                line += f"  match={ratio:.0%}"
            print(line)
            (out_dir / f"{model}.md").write_text(
                f"# {model} — {task['title']}\n\n"
                f"```json\n{json.dumps(stats, indent=2)}\n```\n\n{content}\n"
            )
    print(f"\nresults in {RESULTS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
