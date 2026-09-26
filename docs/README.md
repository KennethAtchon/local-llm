# Local model documentation

This folder contains machine-specific research for the M5 Pro/48 GB Mac.
Read in this order:

1. [Local AI model landscape](LOCAL_MODEL_LANDSCAPE_2026-09-26.md) — model
   types, use cases, Muse Spark versus Glimmer, fit and qualified speed
   evidence across text, vision, voice, images and retrieval.
2. [Qwen3.8 speed decision and evidence](QWEN38_SPEED_RESEARCH_2026-09-26.md)
   — current candidate comparison, X/community provenance, measured-versus-
   claimed speeds, and the matched-trial acceptance gate.
3. [August local coder research](QWEN38_LOCAL_CODER_RESEARCH.md) — model choice,
   hardware fit, original measurements, alternatives, and historical sources.
4. [Local coder setup](QWEN38_LOCAL_CODER_SETUP.md) — the existing serving and
   MTPLX experimental profiles; follow release/version caveats in the newer
   decision brief.

The live-versus-versioned serving details and local benchmarks remain in
[serving/README.md](../serving/README.md). Commands written as `./serving/...`
in these documents are run from the **repository root**, not `docs/`.
