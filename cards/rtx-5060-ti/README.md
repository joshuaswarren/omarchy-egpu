# NVIDIA RTX 5060 Ti (Blackwell, 16 GB)

PNY GeForce RTX 5060 Ti 16GB on Omarchy. Primary route on the laptops: nouveau
with NVK. Reference route on x86: NVIDIA open kernel modules plus CUDA.

**Status:** measured on the 16-inch M1 Max MacBook Pro through the NVIDIA-open
route (595.112.07, 16K fix): CUDA and Vulkan run on the card
([record 2026-10-23](../../benchmarks/2026-10-23-5060ti-m1max-nvidia.md)). On x86 neither route has been run on
our own hardware with this card. On the other laptops the nouveau modules are
NOT MEASURED (they compile for the 16K kernel with no source patches, no run
recorded) and the NVIDIA-open route on them is NOT MEASURED at userspace (the 10-23
aarch64 module build has not been repeated on those hosts).

- [setup.md](setup.md): card identity, both driver routes, firmware sets,
  Apple Silicon aperture and coherency constraints, failure signatures.
- [NVK-BUILD.md](NVK-BUILD.md): building and verifying the Mesa NVK userspace
  from source on a 16 KiB-page aarch64 Omarchy host (no GPU required).
- [patches.md](patches.md): why no patch is carried, per-route build status,
  licensing, upstream status and the open upstream DMA defect we do not patch.
- [ai.md](ai.md): what llama.cpp, vLLM, Ollama, CUDA and MLX can and cannot use
  this card for.