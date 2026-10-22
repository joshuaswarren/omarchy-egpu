# Intel Arc Pro B60 (Battlemage, 24 GB)

ASRock Arc Pro B60 Creator on Omarchy. Stock `xe` driver, Intel firmware
package, Vulkan through ANV.

**Status 2026-10-22:** no host cell is proven. x86 is the stock driver path and
untested by us; every Apple Silicon host is blocked on a 16K xe kernel that has
not been built or shipped. The four-patch 16K series compiles through `xe.o`;
no card has ever been attached on any host.

- [setup.md](setup.md): card identity, power, the x86 recipe, the 16K page
  constraint, Apple Silicon blockers, failure signatures, firmware.
- [patches.md](patches.md): the four experimental 16K patches, per-file
  licensing, upstream status, and what is deliberately left unpatched.
- [ai.md](ai.md): what llama.cpp, vLLM, Ollama, Level Zero and MLX can and
  cannot use this card for.