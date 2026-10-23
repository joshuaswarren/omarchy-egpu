# RX 7600 model sweep and dispatch-latency probe, 2026-10-23

MEASURED on the same 14-inch M2 Max MacBook Pro and RX 7600 chain as the [headline record](2026-10-22-rx7600-m2max-llamacpp-vulkan.md), on the cleaned module (`r0100-clean`). The first sweep ran with 1 of 12 CPUs online (stale spin-table addresses in the replacement device tree); the 12-CPU rerun later the same day re-measured the models with all cores online and load under 0.4. Both are in the table. The GPU-side latency probe is unaffected by CPU count. Every run used the same command shape (n=3, all 99 layers on the card, flash-attention off and on), returned rc=0, and left the last 200 kernel-log lines free of errors. Each model was deleted after its run.

| Model | Size | pp512 fa0 (1 CPU) | tg128 fa0 (1 CPU) | pp512 fa1 (1 CPU) | tg128 fa1 (1 CPU) | pp512 fa0 (12 CPU) | tg128 fa0 (12 CPU) | pp512 fa1 (12 CPU) | tg128 fa1 (12 CPU) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen2.5-3B Q4_K_M | 1.95 GiB | 1747.31 ± 17.83 | 28.54 ± 0.18 | 1893.86 ± 33.82 | 32.41 ± 2.24 | 1880.40 ± 2.40 | 35.34 ± 0.01 | 1995.66 ± 1.10 | 39.76 ± 0.00 |
| Qwen2.5-7B Q4_K_M | 4.36 GiB | 967.77 ± 1.09 | 31.65 ± 0.03 | not run | not run | 945.81 ± 1.99 | 28.93 ± 0.01 | 967.59 ± 9.65 | 28.90 ± 0.04 |
| Qwen2.5-7B Q6_K | 5.82 GiB | 956.33 ± 8.13 | 24.04 ± 0.08 | 961.03 ± 65.70 | 26.55 ± 0.06 | skipped | skipped | skipped | skipped |
| Llama-3.1-8B Q4_K_M | 4.58 GiB | 862.11 ± 4.86 | 23.04 ± 0.12 | 911.00 ± 4.05 | 25.95 ± 0.30 | 878.54 ± 0.30 | 25.79 ± 0.36 | 944.85 ± 0.18 | 28.42 ± 0.03 |
| Qwen3-8B Q4_K_M | 4.68 GiB | 824.70 ± 1.38 | 19.49 ± 0.02 | 883.43 ± 3.79 | 21.59 ± 0.67 | 855.58 ± 0.32 | 22.88 ± 0.01 | 907.38 ± 7.17 | 23.82 ± 0.01 |

Command shape: `GGML_VK_VISIBLE_DEVICES=0 llama-bench -m <model>.gguf -p 512 -n 128 -r 3 -ngl 99 -fa <0|1> -o md`.

Three observations the table supports: flash attention raises decode 10 to 14 percent on these models; the 3B Q4 decodes slower than the 7B Q4 despite half the bytes, so decode follows layer count and per-dispatch latency rather than weight bytes; and the 7B decode barely moves between 1 and 12 CPUs (31.65 high-end boot vs 28.93) while the 3B gains 24 percent, so per-token host work matters only for the small models. The 7B decode varies 28.9 to 31.9 t/s across boots and a thread/core test held it flat at 29.4 to 29.6 across 1 to 12 threads and core pinning: it is GPU- or driver-side. Full detail in the [headline record](2026-10-22-rx7600-m2max-llamacpp-vulkan.md).

## Dispatch latency, measured directly

A Vulkan compute probe (`vkchase`) on the same host measured the two memory paths behind the tunnel:

| Probe | VRAM | System memory (GTT behind the tunnel) |
|---|---:|---:|
| Dependent load over a 64 MiB table | 142.9 ns/load | 2632.6 ns/load (18x) |
| Dependent tiny dispatch, barrier between (64 threads) | 3.08 us/dispatch | 6.02 us/dispatch |

Every buffer a GPU dispatch touches in GTT instead of VRAM costs about 3 us on this chain, and llama.cpp decode issues several hundred dependent dispatches per token, so GTT placement of RADV's upload/descriptor/indirect buffers was a candidate explanation for the decode gap to native PCIe. It is **refuted as a cold-fetch mechanism**: a descriptor-set sweep (1 to 5000 distinct sets) reads the same ~6.5 us per dispatch at every count, and a buffer audit shows weights, KV, and compute buffers all in VRAM with nothing per-token behind the tunnel. The CPU theory is also refuted (thread and core test above). The open question is why small operations run 5x slower here than in `test-backend-ops`; see the headline record's refuted-causes list. The link-latency numbers above remain measurements.

## Cross-vendor small-op cost, 2026-10-23

The same small-operation cost appears on both cards this repo has measured, across two vendors, two Mac kernels, and two Vulkan drivers. MEASURED on both sides:

| Card and model | Driver, host | Small op | Decode (tg128 fa0) | Prompt processing |
|---|---|---:|---|---|
| RX 7600 (Navi 33), Llama-2-7B Q4_0 | RADV, 14-inch M2 Max, 12 CPUs | ~22 us per op in the perf log | 29.26 t/s, about 1/2 of the thread's native 58.03 | 1005.43, 86 percent of native 1167.20 |
| Arc Pro B60 (BMG G21), Llama-2-7B Q4_0 | ANV, 16-inch M1 Max, 10 CPUs | ~23 us per dispatch | 14.39 t/s, about 1/4 of that same native reference | 974.84, at the tunnel RX 7600's level |

The B60 row uses the thread's native RX 7600 as its only available native reference; no native Arc Pro B60 entry exists in that thread.

Prompt processing hides per-operation latency because its operations are large; decode does not. So the per-operation cost is not specific to RADV (the earlier RADV prototype idea stays dropped), not in one card's firmware, and not explained by the refuted causes above (descriptor cold fetch, tensor placement, CPU count, clocks) or by the later refutations (queue round trips under 3 percent of the token, barrier flavours flat at ~3 us, GFXOFF inside noise - see the headline record). What remains is inside the small shaders themselves; the discriminating probe times a standalone RMS-norm-like shader against a memory-clock-pinned GPU. The link-latency numbers above remain measurements.
