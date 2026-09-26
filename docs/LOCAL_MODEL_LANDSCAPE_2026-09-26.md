# Local AI model landscape for the M5 Pro / 48 GB

Research cut-off: **2026-09-26**. This is a **dated, representative comparison**,
not an authoritative or automatically maintained catalogue of all models.
Follow the linked publishers' cards and benchmark run pages for current IDs,
revisions, licenses, weights and compatibility. **Nothing in this document was
installed, downloaded or benchmarked for this research.** In particular,
"fits in memory" is not the same as "works in OpenCode" or "is fastest."

## Question and recommendation

**Question:** Which types of useful local AI models can run on Ken's M5 Pro
(20 GPU cores, 48 GB unified memory), what are they good at, and how fast are
they *actually evidenced* to run? The important choice is usually the fastest
model that completes a particular job correctly, not the highest isolated
generation rate.

- **Fast, light chat/extraction:** an existing Qwen3-4B-Instruct Q4 entry, or a
  separately evaluated Qwen3.5-9B. A community M5 Pro/48 GB oMLX run for the
  former reports **101.3 generated tokens/s at 1K**; the latter reports
  **90.2 at 4K with MTP**, with different packages and conditions [B1][B2].
- **Fast local coder with a large resident model:** the **MoE** class can
  generate quickly because it activates only a fraction of its weights per
  token. Qwen3-Coder-30B-A3B previously measured **91.9 tokens/s locally**
  but **was deliberately removed at Ken's direction**; it is a comparison
  point, *not* a recommendation to restore it [L1]. A Qwen3.6-35B-A3B pack
  has a **103.9 tokens/s public M5 Pro/48 GB short run**, not yet an accepted
  local agent result [B3]. gpt-oss-20b has a **78.4 tokens/s public short
  run** [B4]. Their reasoning/tool behavior and quality still need a task test.
- **Higher-capability multimodal reasoning and the chosen daily coder:** keep
  Qwen3.8-27B as the stable default. This Mac measured **~15.5 tokens/s**
  baseline, **17.36 with the selected ngram mode**; separate oMLX public
  MTP/DFlash 20-core runs report **~31–33** for different packages/settings.
  Splash's **74 on an M5 Pro/48 GB** is a **vendor short-prompt claim**, not a
  same-job local result [L1][B5][V1]. See the [focused speed brief](QWEN38_SPEED_RESEARCH_2026-09-26.md).
- **"Muse Spark":** Meta's **Muse Spark is hosted, not a verified downloadable
  local checkpoint**. Its open-weight **Muse Glimmer-30B** descendant *does*
  fit quantized on this Mac, but the relevant public **16–17 tokens/s** runs
  are not compelling evidence that it replaces the selected Qwen for speed;
  an official speculative-decoding number is on M5 **Max**, not M5 Pro [M1][M2][B6].
- **Images, voice and search:** use specialist vision-language models for
  interpreting images, speech recognizers for audio input, TTS models for
  speech output, diffusion models for creating/editing images, and embedding
  encoders for search. Their speeds use **different units**; no defensible
  M5 Pro/48 GB timing was found for the specific speech and image-generation
  variants below [A1][I1]. Do not put them on a text-tokens/s leaderboard.

**Question reframe:** a model that emits 100 tokens/s but fails a tool call or
needs three retries can be slower than a 17-tokens/s model that solves the
task on the first try. Track *seconds to a correct completed task* as well as
prompt-processing speed, generated tokens/s, memory and failures.

## What “type of model” means

These labels describe **different axes**, not competing brands:

| Axis | Types | Why it matters on this Mac |
|---|---|---|
| Architecture | **Dense:** most weights participate per output token. **Mixture of experts (MoE):** only selected experts participate per token, but all expert weights still need to fit/reside. | MoE can decode much faster than a similarly sized dense model, while its memory footprint can remain large. Qwen3.8-27B is dense [Q1]; Qwen3.6-35B-A3B has ~35B total/~3B active [Q2]. |
| Job specialization | General instruct, code/agent, deliberate reasoning, translation, OCR/vision, embedding, speech recognition, TTS, image generation/editing. | Use a task-matched model; a chat model is not an embedding encoder or an image diffusion pipeline. |
| Input/output modality | Text→text; image+text→text (VLM); audio→text (ASR/STT); text→audio (TTS); text/image→image (diffusion). | A VLM's *text decode* tokens/s is not its image-understanding latency. |
| Packaging / runtime | GGUF + llama.cpp/Metal, MLX/oMLX, MTPLX, Splash, model-specific MLX/ONNX pipelines. Q4/4-bit reduces weight memory at a possible quality cost; KV-cache size grows with history. | The **same model name** can have different speed/quality/tool behavior depending on quantization, prompt, draft, runtime and context [L1][V1]. |

**Units:** `pp`/prefill tokens/s measures reading text input; `tg`/decode
tokens/s measures generating text. For a speech file, report **real-time
factor** (`processing seconds / audio seconds`; lower is faster) plus accuracy;
for TTS, seconds to first audio and real-time factor; for image pipelines,
**seconds per finished image** at fixed resolution and diffusion steps; for
embeddings, encoded tokens/s and retrieval quality at fixed batch and sequence
length [A3][I2]. An image of a document can add many visual tokens even if
its typed text prompt is short.

## This Mac: constraints and measured anchors

Apple's [M5 Pro specifications][H1] list 307 GB/s bandwidth. Unified memory
is shared by model weights, KV cache, vision projector/draft, system UI,
OpenCode and other apps. **48 GB is not 48 GB freely usable model VRAM.** The
versioned [serving config](../serving/llama-swap.config.yaml) is *not proof* of
what is deployed live; the currently selected Qwen stack, experimental MTPLX
lane and older observations are in the [serving runbook][L1] and
[project log][L2].

| Actually observed on this Mac | Workload and interpretation |
|---|---|
| Qwen3.8-27B Q4_K_M: **~386 pp / ~15.5 tg tokens/s**; ngram-map-k4v **15.31→17.36 tg** | Local `pp2048`/`tg128` microbench and separate deterministic speculation test. `ngram-simple` gave 23.49 but *changed output* [L1]. |
| Gemma 4 E4B Q4_K_M: **2,061 pp / 63.36 tg tokens/s** | Same-stack llama-bench comparison recorded in the project log; ~7.5B actual parameters, not "4B total" [L2]. Different model quality and workload from Qwen. |
| Qwen3-Coder-30B-A3B Q4: **1,521 pp / 91.9 tg tokens/s** | Historical local measurement; model was then **removed on request** [L1][L2]. |
| Qwen3.8-27B MLX one-shot: **464 pp / 16.8 tg tokens/s** | `mlx_lm.server` previously stalled on concurrent OpenCode streams; not a proxy for oMLX [L1]. |
| Qwen3.8-27B at 105,860 input tokens: **7m58s** to correct retrieval | Effective prefill ~225 tokens/s; a supported 262K window is **not** an interactive-speed promise [L1]. |

**Memory gate:** Q4/Q8 model file size is only a lower bound. At long context
the *same model* can approach system limits: a public Qwen3-Coder 64K run
recorded 43.96/48 GB system-used and **25.8 tg**, versus its short public
**99.7 tg** [B7][B8]. A public Qwen3.8 32K run used 41.05/48 GB and
reported **33.4 tg** with different MTP/quantization [B5]. Do not assume a
70B Q4 or a BF16 27–30B is a comfortable 48-GB daily model without proven
peak memory and context headroom.

## Representative model families and feasible configurations

This is a **sample chosen for decisions on this laptop**, not a maintained
roster of available models. Models whose exact variant has not been measured
here remain candidates only. The "fit" column refers to a specific cited
quant/pack or observed run, *not* BF16 weights or full native context.

| Class and illustrative model | Best use / trade-off | Fit evidence and text speed on M5 Pro / 48 GB |
|---|---|---|
| **Tiny general dense:** [Qwen3-4B-Instruct-2507][Q3] | Quick extraction, classification, simple coding and short assistant turns; weaker complex agent work. | Existing repo Q4 entry is configured but may download on first use [L3]. **Community oMLX** 20-GPU 4-bit/1K: **1,870 pp / 101.3 tg**, 2.9-GB peak [B1]. Not measured through this repo's live route. |
| **Small reasoning/general dense:** [Qwen3.5-9B][Q4] | More headroom than 4B for everyday chat and coding; still check tool calls and reasoning cost. | **Community oMLX** 20-GPU 48-GB, 4-bit **MTP**, 4K-labelled prompt: **1,603 pp / 90.2 tg** [B2]. Its rate includes acceleration, not an unaccelerated 9B prediction. |
| **Compact multimodal generalist:** [Gemma 4 E4B-it][Q5] | Quick screenshot/document understanding, short chat, audio input; fewer resources than a 27B. | **Locally measured** text `tg128` **63.36** [L2]. Separate **community oMLX** 20-GPU 48-GB/4-bit/32K: **3,487 pp / 38.9 tg**, 8.3-GB peak [B9]. Vision/audio latency **unknown**. |
| **Sparse agent/reasoner:** [gpt-oss-20b][Q6] | Reasoning and tool-use alternative with ~21B total/~3.6B active; official MXFP4 fit within 16 GB *for weights/runtime as described by publisher*, not a complete long-context memory promise. | **Community oMLX** 20-GPU 48-GB/4-bit/1K: **2,011 pp / 78.4 tg** [B4]; 128K run **955.5 pp / 25.8 tg**, 35.12/48 GB system-used [B10]. Quality for Ken's tasks unknown. |
| **Sparse coding agent:** [Qwen3-Coder-30B-A3B][Q7] | Non-thinking coding/tool agent; very fast output, but not the same xhigh-reasoning choice as Qwen3.8. | **Locally measured** **1,521 pp / 91.9 tg**; **removed by Ken**, not proposed for reinstall [L1][L2]. Community 20-GPU 4-bit/1K **99.7 tg** [B7], 64K **25.8 tg** with high system memory [B8]. |
| **Sparse multimodal/agent:** [Qwen3.6-35B-A3B][Q2] | ~35B total/~3B active, native 262K; candidate high-throughput reasoning, coding and visual tasks, but check real quality and tool parser. | **Community oMLX** M5 Pro 20-GPU/48-GB, 4-bit **MTPLX-branded pack**, 4K label: **2,086 pp / 103.9 tg** [B3]. Settings report `mtp_enabled: false`; **do not attribute this rate to Lightning MTP or a generic base quant**. Another *different fine-tuned MTP derivative* reports **69.7 tg** [B11]. No local acceptance run. |
| **Dense chosen model:** [Qwen3.8-27B][Q1] | Stronger broad reasoning, vision and coding for the selected local agent; decode/memory bandwidth cost versus sparse models. | **Local** Q4 baseline 15.5, selected ngram 17.36 [L1]. **Community oMLX** 20-GPU 4-bit/32K MTP **371.3 pp / 33.4 tg** [B5]; **maker Splash** 16-GPU/48-GB short-run **74 tg** [V1]. Different packages and reasoning; not apples-to-apples. |
| **Dense visual/coding agent:** [Muse Glimmer-30B][M2] | Open student of hosted Muse Spark: screenshot, tool and coding tasks; text+image input, no documented speech output. | [Official GGUF Q4 text 16.76 GB + vision projector 1.40 GB + DFlash draft 1.63 GB][M3], all distinct components. **Community oMLX** 20-GPU/48-GB/4-bit/16K with DFlash **and** SpecPrefill/KV4: **458.2 pp / 15.9 tg** [B6]. Maker's **50.2 tg M5 Max** speculative run is not an M5 Pro forecast [M2]. |
| **Older dense 24B:** [Mistral Small 3.2 24B][B12] | General/chat multimodal alternative, not a demonstrated speed leader here. | **Community oMLX** 20-GPU/48-GB/6-bit/1K: **448.3 pp / 15.1 tg**, 18.6-GB peak [B12]. |

**Licensing:** the official cards for the cited Qwen, Gemma 4, Glimmer and
gpt-oss variants say Apache-2.0 [Q1][Q2][Q5][Q6][M2]. Third-party quantized
derivatives, voice files, image-model variants and runtimes can impose
additional terms; inspect the *exact* asset and runtime before distributing a
product. Do not infer a derivative's quality from the base card.

## Speed evidence and comparability

**Evidence grades:** **L** = measured on *this* Mac (not necessarily a current
installed model), **C** = one community-submitted M5 Pro/48-GB run on a cited
page, **V** = publisher/vendor run, **U** = no comparable M5 Pro timing found.
The [oMLX run pages](https://omlx.ai/benchmarks/performance) show model,
quantization, machine, core count, context label, runtime and memory. They
are **community submissions, not an audited same-prompt cross-model league**;
"1K/4K/32K" is a labelled prompt bucket and a configured context may not
equal the exact token count processed. No ranked chart should sum or average
these rows. Specific short/long pairs illustrate how context changes results:

| Example | Short | Longer | What changes besides prompt length |
|---|---:|---:|---|
| Qwen3-Coder-30B-A3B 4-bit [B7][B8] | **99.7 tg** at 1K | **25.8 tg** at 64K | Separate submissions, settings/cache/memory; not controlled A/B. |
| gpt-oss-20b 4-bit [B4][B10] | **78.4 tg** at 1K | **25.8 tg** at 128K | Separate runs and memory conditions. |
| Gemma 4 E4B [B13][B9] | **56.3 tg** at 1K on **16-GPU** 4-bit | **38.9 tg** at 32K on **20-GPU** 4-bit | Both context *and* GPU core count differ. |
| Qwen3.8-27B [L1][B5][V1] | **15.5 local llama.cpp** at `tg128` | **33.4 community oMLX** at 32K; **74 vendor Splash** short | Different runtime, quant, draft, hardware cores and reasoning; **not** a speed-up ratio. |

Meta's Glimmer [official benchmark][M2] reports **26.6 baseline / 50.2
speculative tg** on **M5 Max**; it shows a route, not a promised Pro rate.
If a popular post says 150+ tokens/s, check whether it is **aggregate** over
multiple requests, M5 **Max**, a cached replay, or a vendor-selected prompt.
The [Qwen speed brief](QWEN38_SPEED_RESEARCH_2026-09-26.md) documents those
cases, native MTP/DFlash, and why a full OpenCode turn can differ drastically.

**Do not invent numeric speed by scaling GB/s.** Decode is often memory-bound,
but MoE routing, GPU kernels, draft acceptance, quantization, thermal behavior
and context change the result. The acceptable substitute for an unavailable
same-machine figure is **unknown** followed by a small controlled experiment.

## “Muse Spark” identity check

The names refer to different products:

```text
Meta Muse Spark (hosted proprietary parent; no verified downloadable weights)
                 │ distillation / related model family
                 ▼
Meta Muse Glimmer-30B (open-weight 29.6B dense text+image student)
                 │ GGUF quant + optional projector and DFlash draft
                 ▼
Local runtime on this Mac, if installed and validated
```

Meta's [Muse announcement][M1] calls Spark the hosted model powering Muse;
its [Muse Glimmer card][M2] describes the open model distilled from the Spark
family. No official Spark downloadable weights, published parameter count,
or local M5 Pro result were found as of the research date. Glimmer's official
[GGUF card/files][M3] supply **16.76-GB Q4 text weights**, optional
**1.40-GB vision projector**, and **1.63-GB DFlash draft**. The 131K+ context
*support* still costs cache memory. The observed [community 16K text run][B6]
does not establish Glimmer's visual-task speed or coding success.

If the intended "Spark" was **NVIDIA DGX Spark**, that is a different
computer/hardware product, not a model to download onto this Mac. Do not
quietly conflate it with Meta's model family.

## Decision map by task

| Task | Sensible local candidate(s) | Why, and what remains unproven |
|---|---|---|
| Instant short answers, tagging, simple code autocomplete | Existing Qwen3-4B-Instruct Q4 [L3][B1]; optionally Qwen3.5-9B [B2] | Small/accelerated text models can be responsive. Measure first-token time and exact-task quality, not only generation. |
| Interactive coding with tools | **Keep Qwen3.8-27B** as chosen daily model; compare MTPLX/Splash/oMLX on the *same Qwen* [L1][V1]. Qwen3.6 MoE and gpt-oss are alternatives for a separately authorized model-choice trial [B3][B4]. | Do not auto-restore the removed Qwen3-Coder. Verify tool arguments, multi-turn state, reasoning and pass/fail on actual code tasks. |
| Reading screenshots, diagrams, documents | Gemma 4 E4B for lightweight multimodal input [Q5], Qwen3.8 for hard reasoning [Q1], Glimmer as visual-agent candidate [M2] | Text generation speeds in the table are **not** image-processing speeds. Test the same image and answer rubric. |
| Audio transcription | [Parakeet TDT 0.6B v3][A4] for its documented 25 European languages and timestamps; [Whisper large-v3-turbo][A5] for broader multilingual/translation tasks | Fits via MLX packs ~2.5 GB / ~1.6 GB of weights respectively; no trustworthy M5 Pro timing found. Measure WER and RTF on Ken's recordings. |
| Speak an answer aloud | **Already local:** [Kokoro-82M][A1] → [Piper][A2] → macOS `say`, as wired in [src/speak.py](../src/speak.py) | Existing fallback chain is more useful than a hypothetical text model. Voice/engine licenses differ, and M5 Pro RTF is **unknown**. |
| Generate an image | [FLUX.2 klein 4B][I3] (~13 GB VRAM publisher fit; four-step design) or [Z-Image-Turbo][I4] (publisher says 16 GB VRAM, eight NFEs) | Quantized MLX variants exist [I5][I6]; no comparable M5 Pro seconds/image verified. Do not describe diffusion output as text tokens/s. |
| Edit an image | [Qwen-Image-Edit-2511 int4 MLX][I7] | Variant card reports ~21 GB resident / ~25.5 GB peak under its particular loader at 1024²/4 steps; fits *that workload*, not unquantized BF16 or guaranteed concurrent Qwen27. |
| Search personal notes | Existing [nomic-embed-text-v1.5][E1] GGUF Q4 embedding model, already linked to Second Brain [L1] | Embeddings map text to vectors; changing its ID/revision can invalidate the local vector index. Don't replace it merely to chase a leaderboard. |
| Multilingual retrieval and better result ordering | [Qwen3-Embedding-0.6B][E2] for 100+ languages/up to 32K; [Qwen3-Reranker-0.6B][E3] to re-score retrieved candidates | Distinct encoder and reranker jobs; ≈1.19-GB publisher weights each. New index means an explicit migration/rebuild, not a drop-in replacement for the current one. |
| Video generation or a 70B+ BF16 agent | **No default recommendation** | No directly verified comfortable 48-GB fit, quality and speed for a named variant under Ken's simultaneous workloads. A supported model card is not evidence of an interactive local workflow. |

## Model/runtime compatibility and trade-offs

- **llama.cpp + llama-swap:** the stable on-demand `:8080` lane already serves
  Qwen3.8, Gemma4, Qwen3-4B and embeddings in the **versioned** config [L3],
  but live and versioned configs differ. It requires `--jinja` for reliable
  parsed chat/tool calls; the embedding model is a Second Brain dependency [L1].
- **MLX versus oMLX:** stock `mlx_lm.server` stalled under Ken's concurrent
  agent streams even though its one-shot numbers improved [L1]. That does
  **not** prove oMLX fails: it has separate MTP/DFlash, scheduler and prefix
  cache behavior [B5]. Test exact OpenCode provider and tool schema.
- **MTPLX/Splash:** promising specialized Apple runtimes, but the fastest
  public result might require a model-specific pack and a draft head; do not
  ascribe that speed to an arbitrary GGUF [V1]. MTPLX packs are already in
  an experimental lane per August log [L2]. Consult the
  [Qwen runtime trial guide](QWEN38_SPEED_RESEARCH_2026-09-26.md), rather
  than installing another 27B copy by default.
- **Audio and images:** MLX/ONNX and diffusion pipelines have different
  sampling settings and memory patterns. A 4.6-GB quantized checkpoint is
  **not** a 4.6-GB peak memory guarantee [I3][I7]. Audio input duration,
  image resolution and diffusion step count belong beside every timing.
- **Privacy/licensing:** local processing avoids cloud inference for the
  task, but downloads, telemetry, upstream license, runtime and voice asset
  terms must be checked independently before redistribution. No user data was
  uploaded for this survey.

## Test shortlist and acceptance protocol

**A comparison plan, not permission to change the active setup:**

1. Reconfirm the actual machine/runtime/model IDs and current provider; record
   a **short**, **16–32K**, and **64K+** context case from real tasks. For coding,
   hold prompts, quant family where possible, reasoning mode, tool schemas,
   sampling, max output, cache state and concurrency fixed. Use at least three
   warm runs plus a cold run; record medians/ranges, task correctness, prefill,
   decode, first-token and total elapsed time, peak/system memory and failures.
2. Compare **the same chosen Qwen3.8** through the existing llama.cpp path and
   one isolated accelerated runtime (installed MTPLX lane first; Splash only
   after a separate package/compatibility decision). That tests a *runtime*
   choice without changing the model identity [L1][V1].
3. Only if a **new model** is desired, compare one small fast generalist
   (Qwen3-4B or 9B), one sparse reasoner (Qwen3.6-35B-A3B or gpt-oss-20b),
   and Glimmer for a genuine visual/coding agent task. Treat the removed coder
   as historical evidence, not an implicit install request. Grade the **same
   answer**, parsed tool calls and full turn, not raw model tokens/s alone.
4. Independently test a short speech file and an image job if those modalities
   matter. Report STT WER+RTF, TTS first-audio time/RTF, image seconds/image
   at fixed resolution and steps, and embedding retrieval quality/throughput.
   Do not run another large model concurrently on 48 GB to create misleading
   memory/speed measurements. Preserve `:8080` embedding availability.
5. Promote nothing unless it reliably completes the intended job faster with
   acceptable quality, tool compatibility and memory headroom. Append *local
   measurements* with exact quant/model revision/runtime/flags to the
   [serving runbook][L1] or a new dated experiment receipt.

## Owner decisions

**Default:** preserve Qwen3.8-27B as the daily coding model and its current
serving/embedding route; use this guide to choose **a task** and **a bounded
comparison**, not to download or switch every candidate. The older
Qwen3-Coder-30B-A3B was removed at Ken's direction [L2]. If future work asks
to change the default, the decision is whether a measured improvement in
*completed-task time* and fit is worth any quality/reliability regression;
until then the current default stands. No unresolved owner decision blocks
the documentation itself.

## Sources and evidence ledger

**Evidence grades and boundaries:** [L] this Mac (historical or current as
dated); [B] public community run on oMLX benchmark site (individual settings
and unknown audit); [V] publisher-run numbers; [Q/M/A/I/E/H] publisher cards,
instructions and hardware. A weight file size or supported context is not a
speed test. "Unknown" means no source-backed *same-device timing* was found,
not that the model cannot run.

**Local and machine:**

- [L1]: [serving README and measured numbers](../serving/README.md#measured-on-this-machine-m5-pro-48-gb).
- [L2]: Second Brain project log `projects/active/local-llm.md`, especially
  2026-08-19, 2026-08-20 and 2026-08-23; not a file in this repo.
- [L3]: [versioned llama-swap model config](../serving/llama-swap.config.yaml)
  (not proof of the live config).
- [H1]: [Apple M5 Pro MacBook Pro specs](https://support.apple.com/en-us/126318).

**Text models and benchmark receipts:**

- [Q1]: [Qwen3.8-27B official model card](https://huggingface.co/Qwen/Qwen3.8-27B).
- [Q2]: [Qwen3.6-35B-A3B official card](https://huggingface.co/Qwen/Qwen3.6-35B-A3B).
- [Q3]: [Qwen3-4B-Instruct-2507 official card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507).
- [Q4]: [Qwen3.5-9B official card](https://huggingface.co/Qwen/Qwen3.5-9B).
- [Q5]: [Gemma 4 E4B-it official card](https://huggingface.co/google/gemma-4-E4B-it).
- [Q6]: [gpt-oss-20b official card](https://huggingface.co/openai/gpt-oss-20b).
- [Q7]: [Qwen3-Coder-30B-A3B-Instruct official card](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct).
- [B1]: [Qwen3-4B 1K/20-core/48GB](https://omlx.ai/benchmarks/performance/duzqddpi).
- [B2]: [Qwen3.5-9B MTP 4K/20-core/48GB](https://omlx.ai/benchmarks/performance/g3d1ovyz).
- [B3]: [Qwen3.6-35B-A3B optimized pack 4K/20-core/48GB](https://omlx.ai/benchmarks/performance/3dcny7nc) — `mtp_enabled: false`, no generic-model performance claim.
- [B4]: [gpt-oss-20b 1K/20-core/48GB](https://omlx.ai/benchmarks/performance/9j4hqx9a).
- [B5]: [Qwen3.8 MTP 32K/20-core/48GB](https://omlx.ai/benchmarks/performance/28t7fhmz).
- [B6]: [Glimmer DFlash+SpecPrefill+KV4 16K/20-core/48GB](https://omlx.ai/benchmarks/performance/lxztxneg).
- [B7]: [Qwen3-Coder 1K/20-core/48GB](https://omlx.ai/benchmarks/performance/plrkwzxu).
- [B8]: [Qwen3-Coder 64K/20-core/48GB](https://omlx.ai/benchmarks/performance/y5hbzz9m).
- [B9]: [Gemma E4B 32K/20-core/48GB](https://omlx.ai/benchmarks/performance/5mgo9xh3).
- [B10]: [gpt-oss-20b 128K/20-core/48GB](https://omlx.ai/benchmarks/performance/b1yfap8t).
- [B11]: [Qwen3.6 fine-tuned Lightning-MTP derivative 4K/20-core/48GB](https://omlx.ai/benchmarks/performance/74w70dwo).
- [B12]: [Mistral Small 3.2 24B 1K/20-core/48GB](https://omlx.ai/benchmarks/performance/1a4je5wj).
- [B13]: [Gemma E4B 1K/16-core/48GB](https://omlx.ai/benchmarks/performance/hfqdl2mv).
- [V1]: [Splash benchmark methodology and 16-core M5 Pro conditions](https://github.com/incoai/splash/blob/main/docs/performance.md); [package](https://huggingface.co/incoai/Qwen3.8-27B-Splash).

**Muse and multimodal/other job cards:**

- [M1]: [Meta Muse launch, hosted Spark](https://about.fb.com/news/2026/09/introducing-muse-personal-ai-agent/).
- [M2]: [Muse Glimmer-30B model card and M4/M5 Max speculative runs](https://huggingface.co/meta-models/Muse-Glimmer-30B).
- [M3]: [Official Glimmer GGUF pack and component sizes](https://huggingface.co/meta-models/Muse-Glimmer-30B-GGUF).
- [A1]: [Kokoro-82M official card](https://huggingface.co/hexgrad/Kokoro-82M) (82M, voices/languages, Apache-2.0).
- [A2]: [Piper voice engine/voice license guidance](https://github.com/OHF-Voice/piper1-gpl); [voice assets](https://huggingface.co/rhasspy/piper-voices) (engine and each voice have separate terms).
- [A3]: [whisper.cpp benchmark protocol](https://github.com/ggml-org/whisper.cpp/tree/master/examples/bench).
- [A4]: [Parakeet TDT 0.6B v3 publisher card](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3); [MLX pack](https://huggingface.co/mlx-community/parakeet-tdt-0.6b-v3).
- [A5]: [Whisper large-v3-turbo publisher card](https://huggingface.co/openai/whisper-large-v3-turbo); [MLX pack](https://huggingface.co/mlx-community/whisper-large-v3-turbo).
- [I1]: [Apple MPS diffusion performance guidance](https://huggingface.co/docs/diffusers/en/optimization/mps).
- [I2]: [Text Embeddings Inference: token batching](https://github.com/huggingface/text-embeddings-inference).
- [I3]: [FLUX.2 klein 4B publisher card](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B).
- [I4]: [Z-Image-Turbo publisher card](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo).
- [I5]: [FLUX.2 klein 4B MLX 4-bit pack](https://huggingface.co/mlx-community/flux2-klein-4b-4bit).
- [I6]: [Z-Image-Turbo MLX 4-bit pack](https://huggingface.co/andrevp/Z-Image-Turbo-MLX-4bit).
- [I7]: [Qwen-Image-Edit-2511 publisher card](https://huggingface.co/Qwen/Qwen-Image-Edit-2511); [MLX int4 footprint/run card](https://huggingface.co/xocialize/qwen-image-edit-2511-mlx-int4).
- [E1]: [nomic-embed-text-v1.5](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5).
- [E2]: [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B).
- [E3]: [Qwen3-Reranker-0.6B](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B).

[L1]: ../serving/README.md#measured-on-this-machine-m5-pro-48-gb
[L2]: #sources-and-evidence-ledger
[L3]: ../serving/llama-swap.config.yaml
[H1]: https://support.apple.com/en-us/126318
[Q1]: https://huggingface.co/Qwen/Qwen3.8-27B
[Q2]: https://huggingface.co/Qwen/Qwen3.6-35B-A3B
[Q3]: https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507
[Q4]: https://huggingface.co/Qwen/Qwen3.5-9B
[Q5]: https://huggingface.co/google/gemma-4-E4B-it
[Q6]: https://huggingface.co/openai/gpt-oss-20b
[Q7]: https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct
[B1]: https://omlx.ai/benchmarks/performance/duzqddpi
[B2]: https://omlx.ai/benchmarks/performance/g3d1ovyz
[B3]: https://omlx.ai/benchmarks/performance/3dcny7nc
[B4]: https://omlx.ai/benchmarks/performance/9j4hqx9a
[B5]: https://omlx.ai/benchmarks/performance/28t7fhmz
[B6]: https://omlx.ai/benchmarks/performance/lxztxneg
[B7]: https://omlx.ai/benchmarks/performance/plrkwzxu
[B8]: https://omlx.ai/benchmarks/performance/y5hbzz9m
[B9]: https://omlx.ai/benchmarks/performance/5mgo9xh3
[B10]: https://omlx.ai/benchmarks/performance/b1yfap8t
[B11]: https://omlx.ai/benchmarks/performance/74w70dwo
[B12]: https://omlx.ai/benchmarks/performance/1a4je5wj
[B13]: https://omlx.ai/benchmarks/performance/hfqdl2mv
[V1]: https://github.com/incoai/splash/blob/main/docs/performance.md
[M1]: https://about.fb.com/news/2026/09/introducing-muse-personal-ai-agent/
[M2]: https://huggingface.co/meta-models/Muse-Glimmer-30B
[M3]: https://huggingface.co/meta-models/Muse-Glimmer-30B-GGUF
[A1]: https://huggingface.co/hexgrad/Kokoro-82M
[A2]: https://github.com/OHF-Voice/piper1-gpl
[A3]: https://github.com/ggml-org/whisper.cpp/tree/master/examples/bench
[A4]: https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3
[A5]: https://huggingface.co/openai/whisper-large-v3-turbo
[I1]: https://huggingface.co/docs/diffusers/en/optimization/mps
[I2]: https://github.com/huggingface/text-embeddings-inference
[I3]: https://huggingface.co/black-forest-labs/FLUX.2-klein-4B
[I4]: https://huggingface.co/Tongyi-MAI/Z-Image-Turbo
[I5]: https://huggingface.co/mlx-community/flux2-klein-4b-4bit
[I6]: https://huggingface.co/andrevp/Z-Image-Turbo-MLX-4bit
[I7]: https://huggingface.co/xocialize/qwen-image-edit-2511-mlx-int4
[E1]: https://huggingface.co/nomic-ai/nomic-embed-text-v1.5
[E2]: https://huggingface.co/Qwen/Qwen3-Embedding-0.6B
[E3]: https://huggingface.co/Qwen/Qwen3-Reranker-0.6B
