# Qwen3.8-27B on the M5 Pro: speed research and decision

Research cut-off: **2026-09-26**. This is a decision brief, **not** a report of
new benchmarks on this Mac. The August [model research](QWEN38_LOCAL_CODER_RESEARCH.md)
explains model choice and quality; the [setup runbook](QWEN38_LOCAL_CODER_SETUP.md)
and [serving README](../serving/README.md) describe the existing stack. This brief
supersedes their dated *speed-candidate and release-status recommendations*, not
the measured local results or the decision to keep Qwen3.8-27B.

## Decision in one minute

1. **Keep llama.cpp + llama-swap on `127.0.0.1:8080` as the daily default.**
   Its Qwen3.8-27B Q4_K_M path and parsed tool calls have actually worked here.
   The locally measured `ngram-map-k4v` mode raised generation from 15.31 to
   17.36 tokens/s on its test without changing its deterministic output [L1].
2. **Compare the already installed MTPLX Optimized Speed profile first** on its
   separate `:8000` lane. Both MTPLX packs were downloaded and smoke-tested on
   2026-08-23, but no matched, multi-turn OpenCode speed/quality comparison is
   recorded. The installed version then was 2.9.1 [L2]. Check the installed
   version before relying on any later release's behavior; 2.12.0 was published
   September 24 [P3].
3. **Trial Splash separately next**, if maximizing speed still matters after the
   matched MTPLX comparison. Its maker reports 74 generation tokens/s on an M5
   Pro/48 GB, but under a specific short, medium-reasoning workload on a
   **16-GPU-core** machine. It is neither an independent replication nor a forecast for
   this **20-GPU-core** Mac running a long xhigh OpenCode session [P5][P6]. Its
   ~17.4-GB package/runtime [P5] require a separate download and compatibility
   check.
4. **Do not promote from a headline tokens/s result alone.** Compare time to
   complete a real coding task, cold and reused prompt processing, quality,
   memory pressure, streaming stability, and parsed tool calls. Keep the
   existing model and embedding service available throughout.

No runtime was started, installed, upgraded, benchmarked, or reconfigured for
this September research. A candidate is not an accepted new default.

## The actual bottleneck

**Prefill** is reading the input prompt; **decode** is generating output tokens.
**KV cache** stores attention state for the active context. **Speculative
decoding** has a cheaper draft mechanism suggest tokens and the target model
verify them; MTP (multi-token prediction) uses a head trained with the target,
while DFlash2 uses a separate diffusion-style draft. Reported decode throughput
does not include all the prefill, reasoning, tool, and application time in an
agent turn.

| Fact measured on this Mac | Result | Implication |
|---|---:|---|
| M5 Pro / 20 GPU cores / 48 GB unified memory | 307 GB/s memory bandwidth [L3][P1] | M5 Max numbers do not transfer directly. |
| Qwen3.8-27B Q4_K_M via llama.cpp, short `pp2048` / `tg128` | ~386 prompt / ~15.5 generation tokens/s [L1] | Controlled local base, not an agent-turn measurement. |
| Same target, `ngram-map-k4v` | 15.31 → 17.36 generation tokens/s [L1] | Already enabled; output matched baseline at temperature 0/seed 42 in that local test, not a universal quality proof. |
| `ngram-simple` | 23.49 tokens/s [L1] | Output **changed** in the local test; do not treat as a free lossless gain. |
| MLX one-shot on this Mac | 464 prompt / 16.8 generation tokens/s [L1] | `mlx_lm.server` previously stalled under OpenCode's concurrent streams (14m25s versus 23s). Do not generalize that failure to oMLX. |
| 105,860-token needle retrieval | Correct answer in 7m58s, ~225 effective prompt tokens/s [L1] | A 262K *configured maximum* is not a fast 262K interaction. |

This Mac's selected Qwen model and the previous decision to remove
Qwen3-Coder-30B-A3B are recorded in [L2]. Although that smaller-active-parameter
coder had a faster local microbenchmark, reintroducing it is **not** part of
this speed investigation. A smaller requested/contextual prompt and fewer tool
schemas may save more wall-clock time than a better decode microbenchmark:
the local prompt inventory grew from 10,892 base tokens to 23,610 when the
Playwright MCP tools were included [L3]. Keep the actual job fixed when
comparing engines; separately measure the effect of trimming prompts.

## Current runtime landscape: evidence, not a leaderboard

| Candidate | Evidence and date | Condition / transfer limit | Agent-readiness question |
|---|---|---|---|
| **Splash + `incoai/Qwen3.8-27B-Splash`** | Maker reports **74 decode tokens/s** on an M5 Pro **16 GPU/48 GB** for short coding prompts; **54 at 32K**, **363 prefill tokens/s at 32K**, and **170 aggregate tokens/s over four short concurrent requests** [P5][P6]. Launched September 17 [P7]. | Selected prompts, medium reasoning, 1,024-output-token cap, its own 4-bit package. Aggregate concurrency is **not** single-stream speed. An exact cached replay is not a cold prefill. No independent same-workload 74 tokens/s replication was identified. | Apache-2.0 engine and pack, `splash serve`/`splash opencode`, OpenAI-compatible streaming and parsed tool calls are documented [P5][P8]. Verify in our actual OpenCode agent. Pack is Splash-specific; check memory and long-context quality before promotion. |
| **oMLX native MTP** | Public [M5 Pro 20 GPU/48 GB run](https://omlx.ai/benchmarks/performance/urpn5mqe) reports **465.8 prompt / 30.9 decode tokens/s at 1K** and **484.8 / 32.5 at 4K**, oMLX 0.6.1, 4-bit Q4-gs128, MTP on [P9]. Another [recipe](https://omlx.ai/benchmarks/performance/xtagrlp4) reports ~32.7 at 1K [P10]. | Short measured prompts; a configured 131K context is not a measured 131K prompt. Different package and settings from the local llama.cpp baseline or Splash. | oMLX documents OpenAI-compatible serving, tool parsing and OpenCode integration [P11]. Benchmark its agent behavior, not `mlx_lm.server`'s old failure. |
| **MTPLX Optimized Speed** | Its pack reports dynamic 4-bit and native MTP, ~20.4 GB download and **58.7 tokens/s on M5 Max** for a medium-reasoning coding task [P2]. MTPLX **2.12.0** released September 24 [P3]; the repo's experiment lane was installed at **2.9.1** August 23 [L2]. | The M5 Max rate is not an M5 Pro prediction. 2.12.0's 48-GB default context-planner figure of 204,800 is below the model's 262,144-token native maximum [P3][P4]; these are *configured windows*, not measured long-prompt speeds. Memory-saving q8/q4 paged KV can cost decode speed [P12]. | Already isolated on `:8000`; launcher defaults to turbo, D3, 65,536 context, xhigh, serial/solo and preserve-thinking off [L4]. Confirm actual installed version and a complete agent task. |
| **DFlash2 drafts in Ollama / llama.cpp / oMLX** | A developer [posted](https://x.com/jianchen1799/status/2089998615146348759) **up to 44 tokens/s on his M5 Pro** using an Ollama port [X1]. Another X post cites a separate llama.cpp M5 Pro comparison of **10.42 → 18.4–19.3** [X2]. llama.cpp documents `draft-dflash` [P13]; oMLX has DFlash-specific recipes [P14]. | Different authors, engines, quants, prompts and dates. Draft memory and accept rate matter. The DFlash2 model card's large **H200/CUDA** rates [P15] are not Metal results. A flag or pull request does not prove a released Apple-speed path. | Check current integration status and matching draft/model before considering a new runtime. The local no-draft `ngram-map-k4v` is the established fallback. |
| **Stock `mlx-lm` native MTP** | A proposed implementation reported **15.7 → 24.6 tokens/s** on a *different* Qwen3.6-27B / M4 Pro setup [P16]. | Its PR was not merged at the research cut-off. Do not claim these flags or rates for the stock release or for Qwen3.8. | Not the immediate agent candidate. |

**Why the tables disagree:** hardware bandwidth and GPU cores, quantization,
sampling, reasoning effort, prefix-cache hits, input length, generated-token
count, fan/thermal state and concurrent request count differ. MTP/draft
acceptance also depends on the prompt. MTPLX's [independent issue #286][C1]
shows a retest reversing the impression left by its first benchmark: after
tuning and controlling thermals, decode ranged from **51.2 tokens/s at 1K to
20.3 at 32K** on an **M3 Max**, not on this Mac. Its later estimated MTPLX
end-to-end figure should not be compared with an oMLX time that includes
measured prefill. Independent [concurrency report #265][C2] saw aggregate
throughput *fall* at two simultaneous requests on an M3 Max.

A community [multi-engine coding comparison][C3] on **M2 Max/96 GB at 128K**
reports MTPLX ~20–24 decode tokens/s and llama.cpp+MTP ~17–20 in its
multi-phase task; its environment, subjective score and hardware differ.
These independent reports constrain expectations but do not replace a
same-machine trial. A [Qwen model discussion][C4] reports 4,792 generated
tokens/77s at medium versus 36,188/869s at xhigh in one M5 Max coding
scenario. It illustrates why a shorter answer can be faster **without** a
faster model engine; its judged quality is not a controlled conclusion.

## What X did and did not establish

The shared Playwright browser MCP opened the following **public post pages**
and read their post text and dates on September 26:

- [Jian Chen, August 19][X1]: an author/developer claim of Ollama DFlash2
  reaching *up to* 44 tokens/s on his M5 Pro; links [Ollama PR 17865][P17].
  No matched OpenCode result for this machine.
- [Wei, August 19][X2]: describes someone else's llama.cpp Q4_K_M comparison
  from 10.42 to 18.4–19.3 tokens/s and notes draft memory costs; **not** an
  independent measurement by Wei on this Mac.
- [Inco AI, September 18][X3]: vendor claim of 144 tokens/s for Splash on an
  **M5 Max** and up-to multipliers versus other engines. Not the 48-GB M5 Pro
  result and not an independent comparison.

The browser's **X keyword search redirected to sign-in**; direct public post
pages were accessible. Agent Reach's X CLI had no complete explicit
credentials. Reddit's logged-in CLI was also unavailable, so the community
comparison [C3] was read via public search/mirror, not authenticated Reddit.
This is a targeted public-post and public-web survey, **not an exhaustive
search of X or Reddit**. Dates, authors and whether a number is vendor,
developer, independent or local are part of the claim.

## Reproducible comparison before changing the default

This is a **research protocol**, not a request to run tests during documentation.
Start with the already installed MTPLX lane, then trial Splash separately if
the expected gain is worth another runtime and model package; oMLX is the
independent Apple-MTP comparator if the first two disappoint. Read live
`/v1/models` and the installed runtime/version rather than assuming the
August snapshots are still deployed. The repo's [launcher][L4] and
[preflight][L5] are the existing MTPLX surfaces; do not silently replace the
`llama-swap` service, which also serves second-brain embeddings [L1].

1. **Freeze the job.** Same coding prompts, tool schemas, source revision,
   sampling, reasoning effort, max output, concurrency=1 and cache condition.
   Choose a short edit, a 16–32K-history debug task, and a 64K+-history task;
   include a parsed tool-call exercise and an answer-quality check. Compare
   medium-to-medium and xhigh-to-xhigh. Report the exact quantized checkpoint:
   candidate packs are *not* equal-weight byte copies of Q4_K_M.
2. **Record both rates and experience.** Cold first token, prefill tokens/s,
   decode tokens/s, generated thinking and answer tokens, end-to-end turn
   seconds, time for a multi-turn coding job, peak/steady memory and pressure,
   cache hits, disconnects and correctness. At least three warm repetitions
   per case plus a cold run; record median and range. Do not infer 262K
   usability from `--context-window 262144` or a 1K benchmark.
3. **Isolate memory and ports.** Never load the two 27B weights concurrently
   for comparative numbers on 48 GB. Keep `:8080` reachable for the embedding
   service; unload its generation model before a candidate run rather than
   killing the whole service. Note background applications and thermal state.
   Restore the stable OpenCode provider after each candidate trial.
4. **Acceptance gate.** Promote only when complete agent tasks are materially
   faster, output/tool correctness is no worse on the chosen tasks, streaming
   stays stable for ten turns and at 32K+, the model does not cause sustained
   memory pressure, and the existing `:8080`/embedding path still works.
   Record an actual measured result here before claiming a winner.

| Trial | Status as of this research | Evidence needed next |
|---|---|---|
| llama.cpp Q4_K_M `ngram-map-k4v` | **Measured local baseline; daily default** [L1] | Same-job total latency and quality receipt. |
| MTPLX Speed, current installed 2.9.1 at Aug 23 | **Installed and smoke-tested, not promoted** [L2] | Installed-version check, then matched OpenCode and memory measurements. Decide whether to assess newer 2.12.0 in a *separate* trial. |
| Splash | **Public vendor claim only; not installed or tested here** [P5][P6] | Separate package/runtime, parsed-tool and full-turn comparison. |
| oMLX MTP / DFlash | **Public benchmarks, no local acceptance result** [P9][P14] | Only if needed after higher-value trials; match quant/context. |

## Owner decisions

No new decision is needed to **document** this research. For a later build,
the default is to keep the current Qwen3.8-27B and stable provider until a
same-machine comparison passes the acceptance gate. Installing Splash,
upgrading MTPLX, or changing OpenCode's default is a separate implementation
choice, not something the cited speed claims already authorize. The prior
choice to remove Qwen3-Coder-30B-A3B remains in force [L2].

## Evidence ledger

**Local / repo evidence** (measured or recorded on Ken's machine):

- [L1]: [serving/README.md](../serving/README.md#measured-on-this-machine-m5-pro-48-gb), including the speculation, agent, memory and embedding sections.
- [L2]: Second Brain project log, `projects/active/local-llm.md`, entries
  2026-08-19 and 2026-08-23. This lives in the vault, not this repo.
- [L3]: Second Brain `knowledge-base/01-ai-and-tools/local-llm-operations.md`,
  sections "Measured facts worth not re-deriving" and "Prompt overhead".
- [L4]: [serving/start_mtplx_speed.sh](../serving/start_mtplx_speed.sh) (versioned
  launcher; **not** proof of the current live process).
- [L5]: [serving/mtplx_preflight.sh](../serving/mtplx_preflight.sh).

**Primary upstream / maker documentation** (a maker's benchmark is still a
maker's benchmark):

- [P1]: [Apple M5 Pro specifications](https://support.apple.com/en-us/126318).
- [P2]: [MTPLX Optimized Speed card](https://huggingface.co/Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed).
- [P3]: [MTPLX v2.12.0 release](https://github.com/youssofal/MTPLX/releases/tag/v2.12.0).
- [P4]: [Qwen3.8-27B model card](https://huggingface.co/Qwen/Qwen3.8-27B).
- [P5]: [Splash package card](https://huggingface.co/incoai/Qwen3.8-27B-Splash).
- [P6]: [Splash benchmark methodology](https://github.com/incoai/splash/blob/main/docs/performance.md).
- [P7]: [Splash launch post](https://inco.ai/blog/splash/).
- [P8]: [Splash repository/API](https://github.com/incoai/splash).
- [P9]: [oMLX M5 Pro 48-GB result](https://omlx.ai/benchmarks/performance/urpn5mqe).
- [P10]: [Second oMLX M5 Pro recipe](https://omlx.ai/benchmarks/performance/xtagrlp4).
- [P11]: [oMLX repository](https://github.com/jundot/omlx).
- [P12]: [MTPLX v2.10.0 release and KV context trade-off](https://github.com/youssofal/MTPLX/releases/tag/v2.10.0). Its "48GB seat" result is an M5 Max memory-limited simulation, **not** a physical M5 Pro test.
- [P13]: [llama.cpp speculative-decoding documentation](https://github.com/ggml-org/llama.cpp/blob/master/docs/speculative.md).
- [P14]: [oMLX DFlash recipe on M5 Pro/64 GB](https://omlx.ai/benchmarks/performance/y4qrq1sx).
- [P15]: [Qwen3.8-27B DFlash2 model card](https://huggingface.co/incoai/Qwen3.8-27B-DFlash2).
- [P16]: [Open MLX-LM native-MTP pull request](https://github.com/ml-explore/mlx-lm/pull/990).
- [P17]: [Ollama DFlash2 pull request](https://github.com/ollama/ollama/pull/17865).

**Independent/community and X posts** (identify test conditions before reuse):

- [C1]: [MTPLX issue #286: independent test and later retest](https://github.com/youssofal/MTPLX/issues/286).
- [C2]: [MTPLX issue #265: two-request concurrency](https://github.com/youssofal/MTPLX/issues/265).
- [C3]: [M2 Max multi-engine Reddit discussion](https://www.reddit.com/r/LocalLLaMA/comments/1vwbyzr/benchmark_results_what_is_the_best_and_fastest/) and [public mirror](https://bittide.aicompass.dev/article/4869f5a1-8569-4294-9b45-0dfe35e428bc).
- [C4]: [Qwen model discussion #194: reasoning-token example](https://huggingface.co/Qwen/Qwen3.8-27B/discussions/194).
- [X1]: [Jian Chen, August 19, direct browser read](https://x.com/jianchen1799/status/2089998615146348759).
- [X2]: [Wei, August 19, direct browser read](https://x.com/wei_wang/status/2089902169843540452).
- [X3]: [Inco AI, September 18, direct browser read](https://x.com/inco_ai/status/2101100749623341513).

[L1]: ../serving/README.md#measured-on-this-machine-m5-pro-48-gb
[L2]: #evidence-ledger
[L3]: #evidence-ledger
[L4]: ../serving/start_mtplx_speed.sh
[L5]: ../serving/mtplx_preflight.sh
[P1]: https://support.apple.com/en-us/126318
[P2]: https://huggingface.co/Youssofal/Qwen3.8-27B-MTPLX-Optimized-Speed
[P3]: https://github.com/youssofal/MTPLX/releases/tag/v2.12.0
[P4]: https://huggingface.co/Qwen/Qwen3.8-27B
[P5]: https://huggingface.co/incoai/Qwen3.8-27B-Splash
[P6]: https://github.com/incoai/splash/blob/main/docs/performance.md
[P7]: https://inco.ai/blog/splash/
[P8]: https://github.com/incoai/splash
[P9]: https://omlx.ai/benchmarks/performance/urpn5mqe
[P10]: https://omlx.ai/benchmarks/performance/xtagrlp4
[P11]: https://github.com/jundot/omlx
[P12]: https://github.com/youssofal/MTPLX/releases/tag/v2.10.0
[P13]: https://github.com/ggml-org/llama.cpp/blob/master/docs/speculative.md
[P14]: https://omlx.ai/benchmarks/performance/y4qrq1sx
[P15]: https://huggingface.co/incoai/Qwen3.8-27B-DFlash2
[P16]: https://github.com/ml-explore/mlx-lm/pull/990
[P17]: https://github.com/ollama/ollama/pull/17865
[C1]: https://github.com/youssofal/MTPLX/issues/286
[C2]: https://github.com/youssofal/MTPLX/issues/265
[C3]: https://www.reddit.com/r/LocalLLaMA/comments/1vwbyzr/benchmark_results_what_is_the_best_and_fastest/
[C4]: https://huggingface.co/Qwen/Qwen3.8-27B/discussions/194
[X1]: https://x.com/jianchen1799/status/2089998615146348759
[X2]: https://x.com/wei_wang/status/2089902169843540452
[X3]: https://x.com/inco_ai/status/2101100749623341513
