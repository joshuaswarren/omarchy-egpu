# Three-card same-host A/B: RTX 5060 Ti, Arc Pro B60, Apple M1 Max (2026-11-02)

Host: 16-inch M1 Max MacBook Pro (T6001), all cards in the USB4 chain,
kernel 7.1.12-2-20261029.2-lab-ARCH, llama.cpp 65840ed, llama-bench r=3,
99/99 layers on card, same boot family for every row.

| Model | Card / backend | pp512 (t/s) | tg128 (t/s) |
|---|---|---|---|
| Llama-2-7B Q4_0 | RTX 5060 Ti 16GB, CUDA (nvcc build) | 2465.97 ± 29.61 | 95.11 ± 0.09 |
| | Arc Pro B60 24GB, Vulkan (ANV, distro vulkan-intel 26.2.5) | 1116.63 ± 2.61 | 20.05 ± 0.11 |
| | Apple M1 Max, Vulkan (Honeykrisp) | 240.15 ± 0.08 | 34.33 ± 0.00 |
| Qwen3.8-27B Q4_0 (14.94 GiB) | RTX 5060 Ti, CUDA | 849.48 ± 10.19 | 23.79 ± 0.02 |
| | Arc Pro B60, Vulkan | 203.26 ± 7.36 | 3.30 ± 0.01 |
| | Apple M1 Max, Vulkan | 63.08 ± 0.04 | 9.03 ± 0.01 |

Notes:

- The B60 row with a llama-server serving fill resident (llama-2-7b loaded,
  port 8094, idle) read 1067.88 ± 69.54 / 17.98 ± 0.02: consistent with the
  exclusive run.
- The 5060 Ti leads decode on this host at 4.7x (7B) and 7.2x (27B) the B60,
  and 2.8x / 2.6x the Apple GPU. The B60 leads the Apple GPU on prefill only
  (4.65x); Apple decode beats the B60 (34.3 vs 20.1), the same tunnel-bound
  shape as the 2026-10-23 private-stack records.
- The B60's 20 t/s decode sits far below its memory bandwidth; a SYCL
  (oneAPI) backend could not be tried: the Intel SYCL GPU runtime
  (compute-runtime + level-zero GPU adapter) does not ship for aarch64, and
  Mesa Rusticl on this build exposes only the Apple GPU (clinfo), not the
  B60. A from-source aarch64 NEO build is the untested remaining path.
- gemma-4-12b Q4_0 on the B60 aborted with `vk::DeviceLostError` (stock ANV,
  this build); smaller repro pending.
- Receipts: host logs at ~/.local/state/idle-guard/20261102T{172343,172415,
  180949,181626,181749,193540,193602}Z-*.log.
