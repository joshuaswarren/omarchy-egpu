# Inference on the RX 7600 (Navi 33, `gfx1102`, 8 GB)

What each stack can and cannot use this card for. One stack now has a measured
result on this card on a 14-inch M2 Max MacBook Pro, behind unpublished local
kernel and device-tree changes. Reproduction on a stock system is not
available yet.

## Stack applicability

| Stack | x86 Omarchy host | Apple Silicon Omarchy host | Notes |
|---|---|---|---|
| llama.cpp (Vulkan, RADV) | Applicable; untested on this card by us | **MEASURED on the M2 Max:** pp512 945.81-967.59, tg128 28.90-28.93 (12-CPU rerun; 28.9-31.9 across boots), Qwen2.5-7B Q4_K_M; with `RADV_PERFTEST=nogttspill,dmashaders` Llama-2-7B Q4_0 decode is 26 to 30 percent higher (fa0) | [Benchmark record](../../benchmarks/2026-10-22-rx7600-m2max-llamacpp-vulkan.md); requires the unpublished driver and device-tree fix |
| Ollama (ROCm) | Supported upstream: RX 7600 is in the official Linux ROCm list (ROCm v7 driver) | **Blocked**: ROCm is not packaged for aarch64 Linux | [Ollama GPU docs](https://docs.ollama.com/gpu) |
| Ollama (Vulkan backend) | Available as an additional backend | Untested on aarch64 | Vulkan is enabled by default when the backend is installed; `OLLAMA_VULKAN=0` disables |
| vLLM | ROCm builds target x86_64 servers; consumer RDNA3 is not the supported vLLM target | **Blocked** (aarch64 + ROCm) | Use llama.cpp or Ollama on this card |
| ROCm | `gfx1102` is Release Ready in current ROCm (x86_64 Linux) | **Blocked**; no aarch64 ROCm packages | Officially: [ROCm system requirements](https://rocm.docs.amd.com/projects/install-on-linux/en/develop/reference/system-requirements.html) |
| MLX / the local-ML stack | No verified backend for this card here | No verified backend for this card here | Integrated Apple GPU support does not establish external AMD GPU support |

## The measured command

The record's exact run, from the benchmark environment:

```bash
GGML_VK_VISIBLE_DEVICES=0 llama-bench -m qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf \
  -p 512 -n 128 -r 3 -ngl 99
```

On Apple Silicon eGPU hosts, exporting `RADV_PERFTEST=nogttspill,dmashaders` first raises decode (see the [setup note](setup.md#decode-environment-setting-apple-silicon-egpu-hosts)).
This command works only with the patched driver loaded and the device-tree
window fixed. Until those changes ship in a package, treat it as the
measurement procedure, not a setup path. The [shared Vulkan
recipe](../../recipes/llama-cpp-vulkan.md) builds the backend and selects the
external card on a stock system once the driver prerequisites exist.

The card has 8 GB VRAM. This model, at 4.36 GiB with all layers offloaded,
fits comfortably; larger models need CPU offload and become link-bound. The
measured decode rate already reflects the USB4/PCIe tunnel.

## Honesty box

- One stack (llama.cpp Vulkan) has measured results for several models on one host. No other combination is proven.
- No ROCm, Ollama, vLLM or tinygrad run exists on this card.
- The matched macOS Metal baseline from the [method](../../benchmarks/method.md) has not run; no cross-machine ratio is claimed.
- The working run required unpublished changes. Reproduction on a stock system is not yet possible.
