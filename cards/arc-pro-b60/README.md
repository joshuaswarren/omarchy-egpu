# Intel Arc Pro B60 (Battlemage, 24 GB)

ASRock Arc Pro B60 Creator on Omarchy. Stock `xe` driver on x86; on Apple Silicon, local 16K-page patches plus placement rules.

**Status 2026-10-23: MEASURED on the 16-inch M1 Max MacBook Pro.** With private ANV and xe buffer-placement patches (not upstream), Llama-2-7B Q4_0 decodes at 63.80 (fa0) and 65.96 (fa1) t/s, up from 14.96 and 18.89, about 93 to 94 percent of the public thread's native B60 at matched flash attention. Qwen3.8-27B UD-Q4_K_M (15.32 GiB, 66 of 66 layers) runs fully on the card at pp512 442.61 and tg128 13.12 t/s (fa1, n=5); no native reference exists for it; see the [benchmark record](../../benchmarks/2026-10-23-b60-m1max-llamacpp-vulkan.md#intel-driver-buffers-in-vram-2026-10-23). With local xe patches, a Sonnet Breakaway Box, and ANV 26.2.4, llama.cpp Vulkan ran on the card on a 10-CPU boot: Qwen2.5-7B Q4_K_M at pp512 1026.81 ± 3.40 / tg128 20.64 ± 0.06 (fa0) and 1057.67 ± 73.17 / 24.45 ± 0.13 (fa1); decode varies 20-25 percent run to run and is GPU- or driver-side. 14B models fit and run entirely in the 24 GiB VRAM. Hot-plug is untested and the patches are not published. See the [benchmark record](../../benchmarks/2026-10-23-b60-m1max-llamacpp-vulkan.md).
Other hosts: x86 remains the stock driver path and untested by us; the other Apple Silicon hosts have no B60 run; the M6 has no transport proof.

- [setup.md](setup.md): card identity, power, the x86 recipe, the 16K page constraint, Apple Silicon blockers, failure signatures, firmware.
- [patches.md](patches.md): the four experimental 16K patches, per-file licensing, upstream status, and what is deliberately left unpatched.
- [ai.md](ai.md): what llama.cpp, vLLM, Ollama, Level Zero and MLX can and cannot use this card for.
