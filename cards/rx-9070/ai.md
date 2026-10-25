# Local AI on the RX 9070 (Navi 48, `gfx1201`, 16 GB)

No run of any kind exists on this card here. Everything below is
applicability per upstream documentation, not measurement.


## Stack applicability

| Stack | x86 Omarchy host | Apple Silicon Omarchy host | Notes |
|---|---|---|---|
| llama.cpp (Vulkan, RADV) | Applicable; untested on this card by us | Applicable; untested; RADV supports `gfx1201` in Mesa 25+ | Reference cross-vendor path |
| Ollama (ROCm) | Supported upstream: RX 9070 is in the official Linux ROCm list (ROCm v7 driver required) | **Blocked**: ROCm is not packaged for aarch64 Linux | [Ollama GPU docs](https://docs.ollama.com/gpu) |
| Ollama (Vulkan backend) | Available as an additional backend | Untested on aarch64 | `OLLAMA_VULKAN=0` disables; `GGML_VK_VISIBLE_DEVICES` selects a device |
| vLLM | ROCm builds target x86_64 servers; RDNA4 is not a supported vLLM target (community work exists on gfx1201) | **Blocked** (aarch64 + ROCm) | [AMD's ROCm-on-Radeon vLLM page](https://rocm.docs.amd.com/projects/radeon-ryzen/en/docs-7.1/docs/advanced/advancedrad/linux/vllm/vllm.html) documents the supported Radeon path |
| ROCm | `gfx1201` Release Ready in current ROCm; x86_64 Linux only | **Blocked**; no aarch64 ROCm packages | [ROCm system requirements](https://rocm.docs.amd.com/projects/install-on-linux/en/develop/reference/system-requirements.html) |
| MLX / the local-ML stack | No verified backend for this card here | No verified backend for this card here | Integrated Apple GPU support does not establish external AMD GPU support |

## llama.cpp Vulkan recipe

Use the [shared Vulkan build and device-selection recipe](../../recipes/llama-cpp-vulkan.md) after the driver and BAR checks pass. It builds Vulkan support explicitly, selects the external GPU, and records at least three repetitions.

The RX 9070 has 16 GB VRAM. The model, context, KV cache and runtime buffers must fit the chosen workload. No fit or speed measurement exists here yet.

## Honesty box

- We have not run compute workloads on this card.