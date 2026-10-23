# Intel Arc Pro B60 (Battlemage, 24 GB)

ASRock Arc Pro B60 Creator on Omarchy. Stock `xe` driver on x86; on Apple Silicon, local 16K-page patches plus placement rules.

**Status 2026-10-23: MEASURED on the 16-inch M1 Max MacBook Pro.** With local xe patches, a Sonnet Breakaway Box, and ANV 26.2.4, llama.cpp Vulkan ran Qwen2.5-7B Q4_K_M on the card: pp512 968.87 ± 12.77, tg128 22.29 ± 0.40 t/s. Every number is a single-CPU lower bound (1 of 10 cores online; full-core rerun pending). Hot-plug is untested and the patches are not published. See the [benchmark record](../../benchmarks/2026-10-23-b60-m1max-llamacpp-vulkan.md).

Other hosts: x86 remains the stock driver path and untested by us; the other Apple Silicon hosts have no B60 run; the M6 has no transport proof.

- [setup.md](setup.md): card identity, power, the x86 recipe, the 16K page constraint, Apple Silicon blockers, failure signatures, firmware.
- [patches.md](patches.md): the four experimental 16K patches, per-file licensing, upstream status, and what is deliberately left unpatched.
- [ai.md](ai.md): what llama.cpp, vLLM, Ollama, Level Zero and MLX can and cannot use this card for.
