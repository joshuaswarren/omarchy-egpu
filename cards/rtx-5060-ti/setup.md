# RTX 5060 Ti setup

PNY GeForce RTX 5060 Ti 16GB (Blackwell, GB206), `10de:2d04`, in a USB4 dock (ADT-Link UT4G, ASMedia ASM2464PD switch) plugged into the right port of the 16-inch M1 Max MacBook Pro. The PCIe link measured Gen4 x4 (the card's slot is Gen5 x8). During all NVIDIA runs the Sonnet box with the Intel card was unplugged: with both attached, the first card's SR-IOV VF BARs (7 x 8 GiB) consume the tunnel window and the second card gets no BARs, so the NVIDIA card ran alone on the tunnel.

## Status (2026-10-23)

| Stage | State | Evidence |
|---|---|---|
| Card enumerates over USB4 | MEASURED (bus `0001:03:00.0`; BAR0 64 MiB, BAR1 256 MiB prefetchable, BAR3 32 MiB; VRAM 16311 MiB per `nvidia-smi`; no resizable BAR in use) | boot `986bd5b5` capture |
| NVIDIA open modules load | MEASURED after the 16K-page fix below | module 595.112.07 loads and initializes |
| CUDA | MEASURED: `nvidia-smi` reports CUDA 13.2; `cuInit`, `cuCtxCreate` and a 1 GiB `cuMemAlloc` succeed (sm_120, compute capability 12.0); llama.cpp CUDA smoke ran (see numbers) | driver + smoke receipts |
| Vulkan | MEASURED: llama.cpp lists `Vulkan0 : NVIDIA GeForce RTX 5060 Ti (16311 MiB)`; requires the EGL files below | server log |
| Inference | MEASURED, n=5: see the numbers table and the [benchmark record](../../benchmarks/2026-10-23-5060ti-m1max-nvidia.md) | Gemma + CUDA smoke receipts |

## What the host needs (same as the other cards on this Mac)

- Kernel: the lab's patched 7.1.12 16K-page eGPU kernel with the tunnel window working (root-port prefetchable-window enable + identity bus addresses; see the [B60 record](../../benchmarks/2026-10-23-b60-m1max-llamacpp-vulkan.md) for the measured procedure on this host).
- Module options, in `/etc/modprobe.d/`: `options nvidia NVreg_RegistryDwords="RmForceDisableIomapWC=1"`. Note the key is a driver registry key inside `NVreg_RegistryDwords`, not a module parameter; a bare `NVreg_RmForceDisableIomapWC` is ignored by the kernel. Measured: the first `nvidia-smi` without the key hard-reset the Mac; with the key applied, no crash and no Xid across several runs. The mechanism (write-combined BAR mappings faulting through this host's PCIe tunnel) is inferred from this lab's earlier driver findings on the same host, not measured for NVIDIA specifically. Side effect per the driver source: this key removes NVIDIA's unaligned BAR access support on arm64.

## Vulkan enumeration: the measured cause

The NVIDIA Vulkan ICD's one-time initialization opens the distribution glvnd `libEGL.so.1`, requires `EGL_EXT_platform_base` and `EGL_EXT_platform_device`, enumerates EGL devices, and needs one advertising `EGL_NV_device_cuda`; only `libEGL_nvidia.so.0` does. Without it, every ICD entry point returns `VK_ERROR_INITIALIZATION_FAILED` and `vulkaninfo`/llama.cpp report no drivers. Two files from the driver package make it work:

- `libEGL_nvidia.so.0` on the library path
- the glvnd EGL vendor manifest `/usr/share/glvnd/egl_vendor.d/10_nvidia.json` (its `library_path` points at `libEGL_nvidia.so.0`; the Vulkan ICD manifest is a separate `nvidia_icd.json`)

The NVIDIA ICD deliberately routes through the distribution's glvnd `libEGL`; the NVIDIA EGL library is the device-enumeration backend it needs.

## Numbers

All n=5, llama.cpp build `65840ed53c8653bfbf3e9014d9cbf71ac8c08725`, all 49/49 layers on the card (weights 6637 MiB, KV 608 MiB, compute 129 MiB of 16311 MiB), temperature-0 answer correct, zero Xid lines in the kernel log.

| Test | pp512 | tg128 |
|---|---:|---:|
| Vulkan, Gemma-4-12B QAT Q4_0, flash attention on | 1538.69 ± 6.15 | 44.88 ± 0.02 |
| Vulkan, Gemma-4-12B QAT Q4_0, flash attention off | 1377.52 ± 0.39 | 43.64 ± 0.01 |
| CUDA, Qwen2.5-7B Q4_K_M (smoke, n=3, CUDA 13.4.92 build) | 2919.15 ± 37.74 | 81.46 ± 0.04 |
| Vulkan, Qwen3.8-27B | pending | pending |

Details and environment: [benchmark record](../../benchmarks/2026-10-23-5060ti-m1max-nvidia.md).
