# Inference on the RX 7600 (Navi 33, `gfx1102`, 8 GB)

What each stack can and cannot use this card for. Anything marked **untested**
has no run on our hardware yet; no number on this page is a measurement.

## Stack applicability

| Stack | x86 Omarchy host | Apple Silicon Omarchy host | Notes |
|---|---|---|---|
| llama.cpp (Vulkan, RADV) | Applicable; untested on this card by us | **BLOCKED:** GFX initialization fails before RADV can run | RADV ships for aarch64; the current driver probe does not complete |
| Ollama (ROCm) | Supported upstream: RX 7600 is in the official Linux ROCm list (ROCm v7 driver) | **Blocked**: ROCm is not packaged for aarch64 Linux | [Ollama GPU docs](https://docs.ollama.com/gpu) |
| Ollama (Vulkan backend) | Available as an additional backend | Untested on aarch64 | Vulkan is enabled by default when the backend is installed; `OLLAMA_VULKAN=0` disables |
| vLLM | ROCm builds target x86_64 servers; consumer RDNA3 is not the supported vLLM target | **Blocked** (aarch64 + ROCm) | Use llama.cpp or Ollama on this card |
| ROCm | `gfx1102` is Release Ready in current ROCm (x86_64 Linux) | **Blocked**; no aarch64 ROCm packages | Officially: [ROCm system requirements](https://rocm.docs.amd.com/projects/install-on-linux/en/develop/reference/system-requirements.html) |
| MLX / the local-ML stack | No verified backend for this card here | No verified backend for this card here | Integrated Apple GPU support does not establish external AMD GPU support |

## llama.cpp Vulkan recipe

Use the [shared Vulkan build and device-selection recipe](../../recipes/llama-cpp-vulkan.md) only after GPU initialization completes and a hardware Vulkan probe succeeds. It builds Vulkan support explicitly, selects the external GPU, and records at least three repetitions. Those prerequisites have not passed on the M2 Max.

The RX 7600 has 8 GB VRAM. The model, context, KV cache and runtime buffers must fit the chosen workload. No fit or speed measurement exists here yet.

## Honesty box

- No Vulkan, ROCm, Ollama, vLLM or tinygrad run exists on this card in our lab.
- The current measurements cover normal-boot BAR assignment, VRAM access diagnostics and partial driver initialization. See the [M2 Max result](../../hosts/m2-max/README.md); no prefill or decode rate is claimed.
