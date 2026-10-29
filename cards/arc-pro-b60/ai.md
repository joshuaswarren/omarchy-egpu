# local-ML on the Arc Pro B60 (Battlemage, BMG-G21, 24 GB)

What each stack can and cannot use this card for. One stack has a measured result on a 16-inch M1 Max MacBook Pro, behind unpublished local kernel patches; the fastest numbers also need private Intel driver patches that are not upstream.

Host prerequisites and the driver status live in [setup.md](setup.md); the
driver patches and their state in [patches.md](patches.md).

## Stack applicability

| Stack | x86 Omarchy host | Apple Silicon Omarchy host | Notes |
|---|---|---|---|
| llama.cpp (Vulkan, ANV) | Applicable, untested by us | **MEASURED on the M1 Max (10 CPUs):** pp512 1026.81 ± 3.40, tg128 20.64 ± 0.06 t/s, Qwen2.5-7B Q4_K_M; decode varies 20-25 percent run to run. With private ANV and xe buffer-placement patches, Llama-2-7B Q4_0 decode is 63.80 (fa0) and 65.96 (fa1) t/s. Qwen3.8-27B Q4_0 (unsloth), all 66 layers on the card (fa1): pp512 428.04, tg128 17.28 t/s; the UD-Q4_K_M file: pp512 442.61, tg128 13.12 t/s (its quantization mix, not the link, sets that rate) | [Benchmark record](../../benchmarks/2026-10-23-b60-m1max-llamacpp-vulkan.md); requires the unpublished patches and `GGML_VK_DISABLE_HOST_VISIBLE_VIDMEM=1` |
| llama.cpp (SYCL, oneAPI) | Applicable, untested by us; Intel publishes a guide for the SYCL backend on Arc | **Untested**: the xe driver now runs Vulkan on the M1 Max; this stack has not been tried | Intel developer article covers the SYCL backend |
| vLLM (XPU backend) | Applicable: Arc Pro B-Series is listed as validated hardware on the XPU page | **NOT MEASURED**: XPU targets x86 | [vLLM XPU docs](https://docs.vllm.ai/en/stable/models/hardware_supported_models/xpu/) |
| Ollama (Intel IPEX-LLM path) | Applicable: IPEX-LLM ships a BMG quickstart and an Ollama path | **Untested**: IPEX-LLM targets x86; not tried here | [IPEX-LLM](https://github.com/intel/ipex-llm) |
| Level Zero and OpenCL compute | Applicable via `level-zero-loader` and `intel-compute-runtime` | **Untested**: the xe driver loads on the M1 Max; Level Zero compute has not been tried | Needed for compute that is not llama.cpp |
| MLX and the local-ML stack | Not applicable | No verified MLX backend for this eGPU | MLX targets the integrated Apple GPU, and that support does not transfer to an eGPU |

## The x86 recipe (conditional on a driver run)

Stock Intel stack; the card is not new to it.

```bash
pacman -S vulkan-intel vulkan-tools level-zero-loader intel-compute-runtime
vulkaninfo --summary      # the Arc Pro B60 must appear under ANV
# then build llama.cpp with GGML_VULKAN=ON per recipes/llama-cpp-vulkan.md
llama-bench -m model-Q4_K_M.gguf -ngl 99 -p 512 -n 128
```

For a served endpoint, once `llama-bench` has produced real numbers:

```bash
llama-server -m model-Q4_K_M.gguf -ngl 99 --host 127.0.0.1 --port 8080
```

## The Apple Silicon recipe

The measured run on the 16-inch M1 Max used the 16K xe path with local patches, ANV built from the Mesa 26.2.4 release tarball, and this command:

```bash
GGML_VK_VISIBLE_DEVICES=0 GGML_VK_DISABLE_HOST_VISIBLE_VIDMEM=1 llama-bench -m model-Q4_K_M.gguf -p 512 -n 128 -r 3 -ngl 99
```

The required workarounds and the result are in the [benchmark record](../../benchmarks/2026-10-23-b60-m1max-llamacpp-vulkan.md). No stock-system recipe exists: the patches are local and not upstream.

Build llama.cpp with the Vulkan backend per
[recipes/llama-cpp-vulkan.md](../../recipes/llama-cpp-vulkan.md); the packaged
binary is not assumed to carry it.

### Same-boot dual-card (both eGPUs on one tunnel)

With an RTX 5060 Ti dock chained on the Sonnet's downstream port, the same
boot measured (Llama-2-7B Q4_0, flash attention on): this card on Vulkan
pp512 1482.52 ± 2.26, tg128 66.60 ± 0.01; split across both cards,
Qwen3.8-27B Q4_0 ran pp512 453.46 ± 5.21, tg128 15.67 ± 2.17. The
dual-card topology needs the kernel command line to carry
`hpmmioprefsize=256M` (with `hpmemsize=64M`) or the second card's BARs fail
alignment assignment. Full record: [dual-card
record](../../benchmarks/2026-10-24-dualcard-b60-5060ti-m1max.md).

Expect obstacles before speed. The measured run mapped a 256 MiB BAR for 24 GiB of VRAM, because the 32 GiB resize cannot fit the tunnel window. Weights stayed in VRAM only when the kernel reported that real 256 MiB window; the stock write-combined mapping and CPU-written buffers needed local patches (see the benchmark record). The device DMA clamp to the tunnel aperture is still source-defined and unmeasured (see the IOVA note in [setup.md](setup.md)).

## Honesty box

- One stack (llama.cpp Vulkan) has measured results on one host, the 16-inch M1 Max, with local kernel patches. No other host, stack or card combination is proven.
- The numbers on this page link to a record that states their conditions. The fastest ones need private driver patches that are not upstream.
- Numbers published elsewhere for this card are somebody else's run, on their hardware and their build.
- MLX is not an eGPU path here. On the laptops, keep MLX on the M-series GPU;
  the eGPU is for the Vulkan and Level Zero stacks.