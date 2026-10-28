# 0004 GPU only through shared services

**Context.** The Jetson's GPU and its 30 GB of unified memory are shared with Immich, Jellyfin and Ollama. Portfolio data is a few thousand rows; RAPIDS does not support JetPack 5, and L4T images cannot run on GitHub's arm64 runners.

**Decision.** No GPU in the API, worker or database images. GPU work, when a feature needs it, goes through the shared `ollama` server (statement parsing, categorisation, summaries) behind an interface with a non-LLM fallback, or an opt-in `gpu` compose profile worker with a NumPy fallback, adopted only after a benchmark shows at least 5× on the Xavier.

**Consequences.** The image that CI tests is the image that ships. No GPU feature exists yet.
