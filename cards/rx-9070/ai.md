# Local AI on the RX 9070 (Navi 48, `gfx1201`, 16 GB)

One stack, llama.cpp on Vulkan, has a measured result on this card: a 14-inch M2 Max MacBook Pro, behind unpublished local kernel and device-tree changes (see the [benchmark record](../../benchmarks/2026-10-25-rx9070-m2max-llamacpp-vulkan.md)). Everything else below is applicability per upstream documentation, not measurement.


## Stack applicability

| Stack | x86 Omarchy host | Apple Silicon Omarchy host | Notes |
|---|---|---|---|
| llama.cpp (Vulkan, RADV) | Applicable; untested on this card by us | **MEASURED on the M2 Max:** Qwen2.5-7B Q4_K_M pp512 2426.43 ± 8.86, tg128 24.04 ± 0.14 t/s (flash attention at the build default); needs the local driver and device-tree changes | Reference cross-vendor path; [record](../../benchmarks/2026-10-25-rx9070-m2max-llamacpp-vulkan.md) |
| Ollama (ROCm) | Supported upstream: RX 9070 is in the official Linux ROCm list (ROCm v7 driver required) | **Blocked**: ROCm is not packaged for aarch64 Linux | [Ollama GPU docs](https://docs.ollama.com/gpu) |
| Ollama (Vulkan backend) | Available as an additional backend | Untested on aarch64 | `OLLAMA_VULKAN=0` disables; `GGML_VK_VISIBLE_DEVICES` selects a device |
| vLLM | ROCm builds target x86_64 servers; RDNA4 is not a supported vLLM target (community work exists on gfx1201) | **Blocked** (aarch64 + ROCm) | [AMD's ROCm-on-Radeon vLLM page](https://rocm.docs.amd.com/projects/radeon-ryzen/en/docs-7.1/docs/advanced/advancedrad/linux/vllm/vllm.html) documents the supported Radeon path |
| ROCm | `gfx1201` Release Ready in current ROCm; x86_64 Linux only | **Blocked**; no aarch64 ROCm packages | [ROCm system requirements](https://rocm.docs.amd.com/projects/install-on-linux/en/develop/reference/system-requirements.html) |
| MLX / the local-ML stack | No verified backend for this card here | No verified backend for this card here | Integrated Apple GPU support does not establish external AMD GPU support |

## llama.cpp Vulkan recipe

Use the [shared Vulkan build and device-selection recipe](../../recipes/llama-cpp-vulkan.md) after the driver and BAR checks pass. It builds Vulkan support explicitly, selects the external GPU, and records at least three repetitions.

The RX 9070 has 16 GB VRAM. The model, context, KV cache and runtime buffers must fit the chosen workload. The measured 7B Q4 model (4.36 GiB) used 4.44 GB of VRAM during decode. No larger model has run on this card.

The measured command, from the record:

```bash
GGML_VK_VISIBLE_DEVICES=0 llama-bench -m qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf \
  -p 512 -n 128 -r 3 -ngl 99 -fa 0,1
```

Decode is limited by the number of GPU dispatches per token, not by the model size: see [why](README.md#why-decode-is-dispatch-bound-on-this-setup). `RADV_PERFTEST=dmashaders` raised decode by about 27 to 33 percent on this card on three boots (llama.cpp Vulkan, Qwen2.5-7B Q4_K_M); how to set it, and what the measurement does not show, are in the [setup note](setup.md#decode-environment-setting-apple-silicon-egpu-hosts) and the [benchmark record](../../benchmarks/2026-10-26-rx9070-m2max-radv-perftest.md).

## Honesty box

- One stack (llama.cpp Vulkan) and one model family have measured results, on one host. No other combination is proven.
- No ROCm, Ollama, vLLM or tinygrad run exists on this card.
- The matched macOS Metal baseline has not run; no cross-machine ratio is claimed.
- The working run required unpublished changes. Reproduction on a stock system is not yet possible.
