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

## Same-command native comparison and a free gain, 2026-10-23

Running the exact command and model from [llama.cpp discussion 10879](https://github.com/ggml-org/llama.cpp/discussions/10879) (Llama-2-7B Q4_0, `-ngl 100`, `RADV_PERFTEST=nogttspill`, n=3, same llama.cpp build): over the USB4 tunnel this card reads pp512 `1005.43 ± 1.80` / tg128 `29.26 ± 0.03` with flash attention off, and `1226.01 ± 0.38` / `32.88 ± 0.01` with it on. The thread's native RX 7600 (older llama.cpp commit `91f8c9c`, fa0) read pp512 `1167.20 ± 20.39` / tg128 `58.03 ± 0.08`. Over the tunnel the card keeps about 86 percent of native prompt processing and 50 percent of native decode. Two caveats: the native entry predates llama.cpp's MMVQ path, so the native number with current code is unknown; and the Q4_K_M twin on the tunnel read fa0 `834.65 / 26.68`, fa1 `991.79 / 30.50`, showing the workload choice moves the absolute numbers.

One environment switch gains decode for free on this setup: `GGML_VK_DISABLE_MMVQ=1` takes Llama-2-7B Q4_0 decode from 29.86 to 32.24 t/s (+8 percent) and Qwen2.5-7B Q4_K_M from 29.21 to 31.35 (+7 percent). Other switches on top of it changed nothing beyond ±1 t/s in the sweep. Not tested on a native card; treat it as an eGPU-side observation.

## Decode gap: what is refuted so far

The exact same-command comparison above puts the tunnel at 50 percent of native decode. These candidate causes are now measured and refuted:

- CPU count, threads, and core type: 12 CPUs; 1, 2, 4, 8, 12 threads; P-core and E-core pinning all read 29.4-29.6 t/s.
- Clocks and power: forced high DPM, the sam profile, and `RADV_PERFTEST=nogttspill` changed nothing.
- Cold descriptor-set fetches: a probe cycling 1, 16, 128, 600, 2000, and 5000 distinct descriptor sets reads the same ~6.5 us per dispatch at every count - no cold-set penalty.
- Tensor placement behind the tunnel: a buffer audit shows weights, KV cache, and compute buffers all in device VRAM; the only system-memory buffers are llama.cpp's own host staging (426 MiB upload, 22 MiB host). Nothing the shaders read per token sits behind the tunnel.


## Round trips, barriers, and power states: refuted, 2026-10-23

Three more candidate causes were measured and eliminated (GPU otherwise idle):

- Queue round trips: decode issues 20.2 submissions and 21.4 interrupts per token. Forcing the submit node limit to 25 raises this to 34.3 submissions and drops decode from 29.80 to 29.23 t/s: 14 extra round trips cost 0.65 ms, about 46 us each, so the baseline 20 round trips cost under 3 percent of the 33.5 ms token. Limits of 100/400/1000/100000 all stay at 20.2 per token and 29.76-29.84 t/s (llama.cpp has another submit trigger). Doorbell writes on the non-posted BAR and MSI delivery over USB4 are not the bottleneck.
- Barrier and descriptor cost: a dependent dispatch costs 2.97 us with a global memory barrier, 2.98 us with buffer barriers matching the application's sync function, 2.97 us with ALL_COMMANDS, 0.29 us execution-only, 0.09 us with none; adding a timestamp query costs +1.6 us. Descriptor sets are flat at 3.0 us from 1 to 5000 distinct sets (idle-GPU figures; the earlier 6.5 us readings were taken with concurrent jobs). The 22 us per small op in the perf log is not barrier or descriptor cost.
- GFXOFF: disabled 29.88 vs enabled 28.72/28.10 t/s, inside the ±0.8-1.5 run noise. Not the cause.

What is left, honestly: the GPU is busy 100 percent but memory-busy 3 percent during decode; big matvecs reach 170-208 GB/s; the small ops (RMS_NORM 75 us x 65 per token, ROPE/SET_ROWS/GLU about 22 us x 32 each) add about 9 ms; a bare dependent dispatch costs 3 us. A 75 us RMS_NORM is 15-25x a dependent dispatch plus its tiny work, so something inside those shaders is slow here. One odd observation: the sampled memory clock read 96 MHz during decode in the default power mode and 1124 MHz forced high, with identical tg128. The next probe times a standalone RMS-norm-like shader against a memory-clock-pinned GPU; comparison against a native card is still missing. Nothing measured points at the kernel or the link, and no further kernel work is recommended by any measurement so far.
