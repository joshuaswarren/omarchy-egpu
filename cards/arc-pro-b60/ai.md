# local-ML on the Arc Pro B60 (Battlemage, BMG-G21, 24 GB)

What each stack can and cannot use this card for. One stack has a measured result on a 16-inch M1 Max MacBook Pro, behind unpublished local kernel patches; every number is a single-CPU lower bound.

Host prerequisites and the driver status live in [setup.md](setup.md); the
driver patches and their state in [patches.md](patches.md).

## Stack applicability

| Stack | x86 Omarchy host | Apple Silicon Omarchy host | Notes |
|---|---|---|---|
| llama.cpp (Vulkan, ANV) | Applicable, untested by us | **MEASURED on the M1 Max (10 CPUs):** pp512 1026.81 ± 3.40, tg128 20.64 ± 0.06 t/s, Qwen2.5-7B Q4_K_M; decode varies 20-25 percent run to run | [Benchmark record](../../benchmarks/2026-10-23-b60-m1max-llamacpp-vulkan.md); requires the unpublished patches and `GGML_VK_DISABLE_HOST_VISIBLE_VIDMEM=1` |
| llama.cpp (SYCL, oneAPI) | Applicable, untested by us; Intel publishes a guide for the SYCL backend on Arc | **BLOCKED**: same driver gate | Intel developer article covers the SYCL backend |
| vLLM (XPU backend) | Applicable: Arc Pro B-Series is listed as validated hardware on the XPU page | **BLOCKED**: XPU targets x86, and the driver gate is closed | [vLLM XPU docs](https://docs.vllm.ai/en/stable/models/hardware_supported_models/xpu/) |
| Ollama (Intel IPEX-LLM path) | Applicable: IPEX-LLM ships a BMG quickstart and an Ollama path | **BLOCKED**: same | [IPEX-LLM](https://github.com/intel/ipex-llm) |
| Level Zero and OpenCL compute | Applicable via `level-zero-loader` and `intel-compute-runtime` | **BLOCKED**: same | Needed for compute that is not llama.cpp |
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

## The Apple Silicon recipe does not exist yet

If, and only if, the 16K driver path lands and `vulkaninfo --summary` lists the
B60 under ANV with clean kernel logs, the first thing to test is llama.cpp's
Vulkan backend:

```bash
# conditional, never run by us
VK_DRIVER_FILES=/usr/share/vulkan/icd.d/intel_icd.json timeout 90 vulkaninfo --summary
llama-bench -m model-Q4_K_M.gguf -ngl 99 -p 512 -n 128
```

Build llama.cpp with the Vulkan backend per
[recipes/llama-cpp-vulkan.md](../../recipes/llama-cpp-vulkan.md); the packaged
binary is not assumed to carry it.

Expect obstacles before speed. The small BAR means a large part of the 24 GB is
not CPU-visible through one mapping, and device DMA is clamped to the tunnel
aperture, which is source-defined and unmeasured (see the IOVA note in
[setup.md](setup.md)). Both need measurement, not a guess about what fits.

## Honesty box

- No B60 has run on any host in this repository. Every Apple Silicon cell above
  is blocked before the first `modprobe`.
- Nothing on this page is a performance claim. Numbers published elsewhere for
  this card are somebody else's run, on their hardware and their build.
- MLX is not an eGPU path here. On the laptops, keep MLX on the M-series GPU;
  the eGPU is for the Vulkan and Level Zero stacks.