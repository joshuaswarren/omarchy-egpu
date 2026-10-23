# RX 7600 on a 14-inch M2 Max MacBook Pro: llama.cpp Vulkan, 2026-10-22

MEASURED: llama.cpp inference ran on the external card through RADV Vulkan. The kernel log after the run shows no amdgpu error, fault, or alignment line. The first captures (below) ran with 1 of 12 CPUs online; the 12-CPU rerun of 2026-10-23 is the current reference: Qwen2.5-7B Q4_K_M at pp512 `945.81 ± 1.99` / tg128 `28.93 ± 0.01` with flash attention off, and `967.59 ± 9.65` / `28.90 ± 0.04` with it on. The 7B decode rate varies 28.9-31.9 t/s across boots and is GPU- or driver-side, not CPU-limited (thread and core test below).

| Test | Tokens per second |
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

**Correction and resolution, 2026-10-23.** The first eGPU boots ran with only 1 of 12 CPUs online: the replacement device tree carried stale spin-table release addresses, which change every boot, so the secondary cores failed to start (`CPU1..CPU11: failed to come online`, `Brought up 1 node, 1 CPU`). A 12-CPU rerun with the identity-range fix in the boot chain's own device trees then measured every model again. Two results stand. First, the 7B Q4 decode rate is not CPU-limited and is not stable across boots: it reads 28.9 to 31.9 t/s (fa0 around 29.5; fa1 31.4 to 31.9). The earlier single-CPU 31.65 was the high end of that range, not a better configuration. Second, a direct test on the 12-CPU boot held decode flat at 29.4 to 29.6 t/s across 1, 2, 4, 8, and 12 llama-bench threads, P-core pinning, and E-core pinning, at load below 0.4. The extra cores lifted the smaller models (the 3B gained 24 percent decode). The 1-CPU rows remain on this page as historical values.

## Later clean-module run

With the patch series cleaned for [PR #184](https://github.com/omacom/linux-aurora/pull/184), the same host and model measured pp512 `967.77 ± 1.09` and tg128 `31.65 ± 0.03` (3 repetitions, 1 CPU online; the high end of the 28.9-31.9 boot range). The kernel log stayed clean. A variant sweep moved decode barely: default DPM 31.70 ± 0.02, forced high 31.17 ± 0.06, `RADV_PERFTEST=nogttspill` 31.48 ± 0.37. During runs the GPU sat at ~98% busy with the CPU blocked in `drmSyncobjWait` in 33 of 34 stack samples: the workload is GPU-bound, and clock or RADV-spill settings are not the decode limiter.

## 12-CPU rerun, 2026-10-23

Boot chain carrying the PR's device-tree change: `nproc` 12, `Brought up 1 node, 12 CPUs`, identity tunnel ranges confirmed in the live tree, 0 amdgpu errors in dmesg, load under 0.4. Same command shape, n=3, all layers on the card, Qwen2.5-7B Q4_K_M: pp512 `945.81 ± 1.99` / tg128 `28.93 ± 0.01` (fa0; repeats 29.57, 29.49) and `967.59 ± 9.65` / `28.90 ± 0.04` (fa1; repeats 31.86, 31.39). The thread and core test in the same window read 29.43 to 29.62 t/s across every thread count and core pinning. Q6_K was skipped in this window; its 1-CPU rows stand as single-CPU results.

Context, not our measurement: community data for an RX 7600 on a native PCIe host ([llama.cpp discussion 10879](https://github.com/ggml-org/llama.cpp/discussions/10879)) reports tg128 58.03 t/s on Llama-2-7B Q4_0; scaled by model size (3.56/4.36 GiB) that is roughly 47 t/s on this workload class, and an RX 7600M XT eGPU entry reads 45.28. Our 28.9-31.9 sits below that band. What closes the gap is **not established**. One hypothesis, RADV upload/descriptor/indirect-buffer memory landing in GTT behind the tunnel, is contradicted in part by our own data: `test-backend-ops` runs the same RADV with the same buffer placement and completes small operations in 4.2 us, which that placement alone could not explain. The CPU theory was also tested and refuted (thread and core test above). The measured link facts stand: big decode kernels stream 226-250 GB/s against a 288 GB/s peak, weights sit in VRAM, and small operations took 20-70 us in the timestamp logs. The next probe counts per-token dispatches and what each touches.

## Not measured

The matched macOS Metal baseline from the [method](method.md#matched-linux-vulkan-and-macos-metal-runs) (same revision, same model, same settings on the same Mac's integrated GPU) has not run yet. Compare it against the 12-CPU rows.
