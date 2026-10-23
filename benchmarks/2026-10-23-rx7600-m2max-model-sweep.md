# RX 7600 model sweep and dispatch-latency probe, 2026-10-23

MEASURED on the same 14-inch M2 Max MacBook Pro and RX 7600 chain as the [headline record](2026-10-22-rx7600-m2max-llamacpp-vulkan.md), on the cleaned module (`r0100-clean`). **All throughput numbers below are single-CPU lower bounds:** every eGPU boot in this sweep ran with 1 of the host's 12 CPUs online because the replacement device tree carried stale spin-table addresses; see the correction in the headline record. The GPU-side latency probe is unaffected. Conditions also differ from the headline record: other tickets were running on the host (load average 2.3 to 4.2). Every run used the same command shape (n=3, all 99 layers on the card, flash-attention off and on), returned rc=0, and left the last 200 kernel-log lines free of errors. Each model was deleted after its run.

| Model | Size | pp512 fa=0 | tg128 fa=0 | pp512 fa=1 | tg128 fa=1 |
|---|---|---:|---:|---:|---:|
| Qwen2.5-3B Q4_K_M | 1.95 GiB | 1747.31 ± 17.83 | 28.54 ± 0.18 | 1893.86 ± 33.82 | 32.41 ± 2.24 |
| Qwen2.5-7B Q4_K_M (earlier clean run, idle host) | 4.36 GiB | 967.77 ± 1.09 | 31.65 ± 0.03 | not run | not run |
| Qwen2.5-7B Q6_K | 5.82 GiB | 956.33 ± 8.13 | 24.04 ± 0.08 | 961.03 ± 65.70 | 26.55 ± 0.06 |
| Llama-3.1-8B Q4_K_M | 4.58 GiB | 862.11 ± 4.86 | 23.04 ± 0.12 | 911.00 ± 4.05 | 25.95 ± 0.30 |
| Qwen3-8B Q4_K_M | 4.68 GiB | 824.70 ± 1.38 | 19.49 ± 0.02 | 883.43 ± 3.79 | 21.59 ± 0.67 |

Command shape: `GGML_VK_VISIBLE_DEVICES=0 llama-bench -m <model>.gguf -p 512 -n 128 -r 3 -ngl 99 -fa <0|1> -o md`.

Two observations the table supports: flash attention raises decode 10 to 14 percent on these models, and the 3B Q4 decodes slower than the 7B Q4 despite half the bytes. Decode time follows layer count and per-dispatch latency, not weight bytes: the card is dispatch-latency-bound in decode, not bandwidth-bound.

## Dispatch latency, measured directly

A Vulkan compute probe (`vkchase`) on the same host measured the two memory paths behind the tunnel:

| Probe | VRAM | System memory (GTT behind the tunnel) |
|---|---:|---:|
| Dependent load over a 64 MiB table | 142.9 ns/load | 2632.6 ns/load (18x) |
| Dependent tiny dispatch, barrier between (64 threads) | 3.08 us/dispatch | 6.02 us/dispatch |

Every buffer a GPU dispatch touches in GTT instead of VRAM costs about 3 us on this chain, and llama.cpp decode issues several hundred dependent dispatches per token, so GTT placement of RADV's upload/descriptor/indirect buffers was a candidate explanation for the roughly 20 us per small operation in the timestamp logs and the decode gap to native PCIe. It is **not established**: `test-backend-ops` runs the same RADV with the same buffer placement and completes small operations in 4.2 us, which that placement alone could not explain, and every eGPU run so far shared one online CPU with other jobs. Treat the mechanism as a hypothesis, contradicted in part, awaiting the 12-CPU rerun. The link-latency numbers above are measurements either way.
