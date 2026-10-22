# RX 7600 on a 14-inch M2 Max MacBook Pro: llama.cpp Vulkan, 2026-10-22

MEASURED: llama.cpp inference ran on the external card through RADV Vulkan. The kernel log after the run shows no amdgpu error, fault, or alignment line.

| Test | Tokens per second |
|---|---:|
| pp512 (prompt processing) | 964.58 ± 0.29 |
| tg128 (decode) | 31.07 ± 0.01 |

Three repetitions, mean ± standard deviation, all model layers on the card.

## Environment

| Field | Value |
|---|---|
| Host | 14-inch M2 Max MacBook Pro, Omarchy Linux, 16 KiB pages |
| Kernel | `7.1.12-2-20261013.18-egpu-ARCH` (aarch64, local build with unpublished driver and device-tree changes) |
| Card | ASRock Radeon RX 7600 Challenger OC, `1002:7480`, bound to amdgpu |
| Chain | Host USB4 port, OwlTree dock, Rosewill ASM2464PD enclosure; cable and PSU not recorded |
| GPU driver | amdgpu loaded from `/lib/modules/.../updates/amdgpu.ko`, SHA-256 `1388ccac…`; amdgpu 3.64.0 initialized |
| Vulkan | RADV, Mesa `26.2.5-arch1.1`, conformance 1.4.5.3, discrete GPU, `AMD Radeon RX 7600 (RADV NAVI33)` |
| Model | Qwen2.5-7B-Instruct Q4_K_M, 4.36 GiB, 7.62 B parameters |
| llama.cpp | build `65840ed53` (11449), Vulkan backend |
| Command | `GGML_VK_VISIBLE_DEVICES=0 llama-bench -m qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf -p 512 -n 128 -r 3 -ngl 99` |
| Power | Not recorded. Link under load: not recorded |
| Conditions | Run inside a scheduled probe window; one short correctness check before the timed runs |

A short generation check ran at temperature 0: the prompt "The capital of France is" produced "The capital of France is Paris." at 128.3 t/s prompt and 28.2 t/s generation, confirming the timed numbers did not come from a broken context. `vkcube` did not run; no display was attached.

## Repeatability limits

The driver build and the device-tree change are local and unpublished. Do not expect these numbers from a stock kernel or stock device tree. Hot-plug is untested: the card was present at boot, so these results cover the attached-at-boot path only. The 8 GiB BAR resize still fails and BAR0 falls back to 256 MiB; the driver continues. Decode through the USB4/PCIe tunnel is expected to sit below a native PCIe x16 result; the workload's memory placement was not profiled. Both points are inference, not measurements.

## Not measured

The matched macOS Metal baseline from the [method](method.md#matched-linux-vulkan-and-macos-metal-runs) (same revision, same model, same settings on the same Mac's integrated GPU) has not run yet. Comparisons between this record and other machines are not valid until that baseline exists.
