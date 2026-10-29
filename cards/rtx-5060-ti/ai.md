# local-ML on the RTX 5060 Ti (Blackwell, GB206, 16 GB)

What each stack can and cannot use this card for. Anything marked untested has
no run on our hardware: no number on this page is a measurement, and no
performance or model-size claim is made here.

Driver status is in [setup.md](setup.md); the patch and upstream position in
[patches.md](patches.md).

## Stack applicability

| Stack | x86 Omarchy host | Apple Silicon Omarchy host | Notes |
|---|---|---|---|
| llama.cpp (CUDA) | Applicable, untested by us | **Not available**: no CUDA userspace exists for this card on the laptops | Needs a working NVIDIA open-module install; see [setup.md](setup.md) |
| llama.cpp (Vulkan, NVK) | Applicable, untested by us | Applicable in principle, **NOT MEASURED**: no driver run exists | Needs the nouveau route and a working firmware set |
| vLLM (CUDA backend) | Applicable, untested by us | **Not available**: no CUDA userspace on aarch64 | The standard path for this card |
| Ollama (CUDA) | Applicable, untested by us | **Not available**: same reason | Detects the driver at start; without CUDA it will not use the card |
| Ollama (Vulkan backend) | Available as an additional backend | Untested on aarch64 | Vulkan is enabled when the backend is installed; `OLLAMA_VULKAN=0` disables it |
| CUDA itself | Available with the open modules route | **Not available** | No version-matched aarch64 driver installer could be found |
| MLX and the local-ML stack | Not applicable | No verified MLX backend for this eGPU | MLX targets the integrated Apple GPU, and that support does not transfer to an eGPU |

## The x86 recipe (conditional on a driver run)

Stock NVIDIA stack. Blackwell needs the open kernel modules plus the closed
user-space stack:

```bash
pacman -S --needed nvidia-open-dkms nvidia-utils
nvidia-smi
nvidia-smi -q | grep -i "GSP Firmware"    # expect the installed release version
```

Then the usual CUDA tooling; nothing about this card needs special handling
once the driver is up (llama.cpp here means the CUDA build; the Vulkan build is
a separate recipe, [recipes/llama-cpp-vulkan.md](../../recipes/llama-cpp-vulkan.md)):

```bash
llama-bench -m model-Q4_K_M.gguf -ngl 99 -p 512 -n 128     # llama.cpp with CUDA
# or, for a served endpoint:
llama-server -m model-Q4_K_M.gguf -ngl 99 --host 127.0.0.1 --port 8080
```

## The Apple Silicon recipe does not exist yet

CUDA is unavailable there (see [setup.md](setup.md)). The only candidate is
llama.cpp's Vulkan backend on NVK, and it has never run in this configuration:

```bash
# conditional, never run by us
sudo modprobe nouveau
VK_DRIVER_FILES=/usr/share/vulkan/icd.d/nouveau_icd.json timeout 90 vulkaninfo --summary
llama-bench -m model-Q4_K_M.gguf -ngl 99 -p 512 -n 128
```

Build llama.cpp with the Vulkan backend per
[recipes/llama-cpp-vulkan.md](../../recipes/llama-cpp-vulkan.md); the packaged
binary is not assumed to carry it.

Expect obstacles before speed. The 2 GiB or 8 GiB prefetch window behind the
tunnel is source-defined and unmeasured, and nothing here establishes what a
given allocation can map. Measure before quoting a number or a ceiling.

## Honesty box

- No RTX 5060 Ti has run on any host in this repository. The Apple Silicon
  cells are blocked before the first `modprobe`.
- Nothing on this page is a performance claim. Numbers published elsewhere for
  this card are somebody else's run, on their hardware and their driver.
- MLX is not an eGPU path here. On the laptops, keep MLX on the M-series GPU;
  the eGPU is for the CUDA or Vulkan stacks.