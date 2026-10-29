# NVIDIA RTX 5060 Ti (Blackwell, 16 GB)

PNY GeForce RTX 5060 Ti 16GB on Omarchy. Primary route on the laptops: nouveau
with NVK. Reference route on x86: NVIDIA open kernel modules plus CUDA.

**Status 2026-10-22:** no host cell is proven. Both routes are stock
distribution paths and neither has been run on our own x86 hardware with this
card. On the laptops the nouveau modules are NOT MEASURED (they compile for
the 16K kernel with no source patches, no run recorded), the NVIDIA-open route is NOT MEASURED at
userspace because no matching aarch64 driver installer exists, and no card has
ever been attached on any host.

- [setup.md](setup.md): card identity, both driver routes, firmware sets,
  Apple Silicon aperture and coherency constraints, failure signatures.
- [NVK-BUILD.md](NVK-BUILD.md): building and verifying the Mesa NVK userspace
  from source on a 16 KiB-page aarch64 Omarchy host (no GPU required).
- [patches.md](patches.md): why no patch is carried, per-route build status,
  licensing, upstream status and the open upstream DMA defect we do not patch.
- [ai.md](ai.md): what llama.cpp, vLLM, Ollama, CUDA and MLX can and cannot use
  this card for.