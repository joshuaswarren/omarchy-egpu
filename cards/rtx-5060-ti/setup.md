# RTX 5060 Ti setup

PNY GeForce RTX 5060 Ti 16GB (Blackwell, GB206), `10de:2d04`, in a USB4 dock on the 16-inch M1 Max MacBook Pro, bus `0001:03:00.0` (per `nvidia-smi`). Dock identity, port, BAR sizes, link width, and the both-cards constraint are recorded (boltctl, the PCI tree, and kernel-log captures from 2026-10-23); the link speed varies with load and idles at 2.5 GT/s, so the safe statement is PCIe x4 through the USB4 tunnel (card capable of x8). During all NVIDIA runs the Intel card's enclosure was unplugged: with both attached, the Intel card's SR-IOV VF BARs (7 x 8 GiB, 56 GiB total) consume the tunnel window and the second card gets no address space, so the NVIDIA card ran alone (kernel-log capture of the both-cards boot).

## Status (2026-10-23)

| Stage | State | Evidence |
|---|---|---|
| Card enumerates over USB4 | MEASURED (bus `0001:03:00.0`; VRAM 16311 MiB; BAR0 64 MiB non-prefetchable, BAR1 256 MiB prefetchable, BAR3 32 MiB; resizable-BAR capability present, BAR1 left at 256 MiB; PCIe x4 through the tunnel, card x8-capable) | `nvidia-smi` + PCI captures, 2026-10-23 |
| NVIDIA open modules load | MEASURED after the 16K-page fix below | module 595.112.07 loads and initializes |
| CUDA | MEASURED: driver ceiling 13.2 per `nvidia-smi`; toolkit 13.4.92 (nvcc); cuInit 0, cuCtxCreate 0, 1 GiB cuMemAlloc 0 (compute capability 12.0, 15849 MiB); llama.cpp CUDA benchmarks ran (see numbers) | driver-API + nvcc + benchmark records |
| Vulkan | MEASURED: llama.cpp lists `Vulkan0 : NVIDIA GeForce RTX 5060 Ti (16311 MiB)`; requires the EGL files below | server log |
| Inference | MEASURED, n=5 (Vulkan) and n=5 (CUDA): see the numbers table and the [benchmark record](../../benchmarks/2026-10-23-5060ti-m1max-nvidia.md) | Gemma and CUDA benchmark records |

## What the host needs (same as the other cards on this Mac)

- Kernel: the patched 7.1.12 16K-page eGPU kernel with the tunnel window working (root-port prefetchable-window enable + identity bus addresses; see the [B60 record](../../benchmarks/2026-10-23-b60-m1max-llamacpp-vulkan.md) for the measured procedure on this host).
- Module options, in `/etc/modprobe.d/`: `options nvidia NVreg_RegistryDwords="RmForceDisableIomapWC=1"`. Note the key is a driver registry key inside `NVreg_RegistryDwords`, not a module parameter; a bare `NVreg_RmForceDisableIomapWC` is ignored by the kernel. Measured: the first `nvidia-smi` without the key hard-reset the Mac (netconsole shows the driver load at 20:22:45Z, Chipset-not-recognized at 20:24:04Z, then fresh boot messages at 20:25:01Z, no oops text; the boot id change is independently logged). With the key applied, no crash and no Xid across several runs. The mechanism (write-combined BAR mappings faulting through this host's PCIe tunnel) is inferred from our earlier driver findings on the same host, not measured for NVIDIA specifically. Side effect per the driver source: this key removes NVIDIA's unaligned BAR access support on arm64.

## Vulkan enumeration: the measured cause

The NVIDIA Vulkan ICD's one-time initialization opens the distribution glvnd `libEGL.so.1`, requires `EGL_EXT_platform_base` and `EGL_EXT_platform_device`, enumerates EGL devices, and needs one advertising `EGL_NV_device_cuda`; only `libEGL_nvidia.so.0` does. Without it, every ICD entry point returns `VK_ERROR_INITIALIZATION_FAILED` and `vulkaninfo`/llama.cpp report no drivers. Two files from the driver package make it work:

- `libEGL_nvidia.so.0` on the library path
- the glvnd EGL vendor manifest `/usr/share/glvnd/egl_vendor.d/10_nvidia.json` (its `library_path` points at `libEGL_nvidia.so.0`; the Vulkan ICD manifest is a separate `nvidia_icd.json`)

The NVIDIA ICD deliberately routes through the distribution's glvnd `libEGL`; the NVIDIA EGL library is the device-enumeration backend it needs.

## Numbers

All rows n=5, llama.cpp build `65840ed53c8653bfbf3e9014d9cbf71ac8c08725`, all 49/49 layers on the card (weights 6637 MiB, KV 608 MiB, compute 129 MiB of 16311 MiB), temperature-0 answer correct, zero Xid lines in the kernel log.

| Test | pp512 | tg128 |
|---|---:|---:|
| Vulkan, Gemma-4-12B QAT Q4_0, flash attention on | 1538.69 ± 6.15 | 44.88 ± 0.02 |
| Vulkan, Gemma-4-12B QAT Q4_0, flash attention off | 1377.52 ± 0.39 | 43.64 ± 0.01 |
| CUDA, Gemma-4-12B QAT Q4_0, flash attention on (toolkit 13.4.92, sm_120) | 2123.08 ± 24.18 | 49.83 ± 0.03 |
| CUDA, Gemma-4-12B QAT Q4_0, flash attention off | 1732.39 ± 3.80 | 48.08 ± 0.05 |
| CUDA, Qwen2.5-7B Q4_K_M (first smoke, n=3) | 2919.15 ± 37.74 | 81.46 ± 0.04 |
| Vulkan, Qwen3.8-27B Q4_0, flash attention on (n=3) | 673.27 ± 0.55 | 22.52 ± 0.06 |
| CUDA, Qwen3.8-27B Q4_0, flash attention on (n=3) | 943.70 ± 10.33 | 24.63 ± 0.01 |

Details and environment: [benchmark record](../../benchmarks/2026-10-23-5060ti-m1max-nvidia.md).

A lever A/B on this card and model (CUDA graphs, KV cache type) says: keep
the defaults (CUDA graphs on, f16 KV); q8_0 KV only for VRAM headroom, at a
speed cost (about 10 percent decode on Gemma-4-12B).

### Same-boot dual-card (both eGPUs on one tunnel)

With the Arc Pro B60 in a Sonnet Breakaway enclosure and this card's dock
chained on its downstream port, the same boot measured (Llama-2-7B Q4_0,
flash attention on): CUDA pp512 3132.07 ± 33.51, tg128 97.78 ± 0.05;
Vulkan pp512 2478.46 ± 1.49, tg128 84.92 ± 0.07. Split across both cards,
Qwen3.8-27B Q4_0 ran pp512 453.46 ± 5.21, tg128 15.67 ± 2.17. The
dual-card topology needs one more kernel command-line knob
(`hpmmioprefsize=256M`) or this card's prefetchable BARs fail alignment
assignment. Full record: [dual-card record](../../benchmarks/2026-10-24-dualcard-b60-5060ti-m1max.md).

## The nouveau route (not part of these runs)

An earlier shared-kernel route compiled nouveau (plus NVK for Vulkan) and the NVIDIA-open modules against a common kernel target; that established compilation only, and no nouveau runtime run exists on this hardware. Every measurement on this page is the NVIDIA-open route. Nouveau plus its GSP firmware and Mesa NVK are built (the 16K GSP page-table fix is built, untested on hardware); not exercised in these runs. Build notes: [NVK-BUILD.md](NVK-BUILD.md).
