# RX 9070 on a 14-inch M2 Max MacBook Pro: llama.cpp Vulkan, 2026-10-25

MEASURED: llama.cpp inference ran on the external RX 9070 through RADV Vulkan. Qwen2.5-7B Q4_K_M reads pp512 `2426.43 ± 8.86` and tg128 `24.04 ± 0.14` t/s with the default flash-attention setting. Prompt processing is about 2.5 times faster than the RX 7600 on the same host. Decode is slower than the RX 7600 (24.0 against 28.9 to 31.9 t/s). Decode time follows the number of GPU dispatches per token, about 40 us each, and not the bytes read. The cause of that per-dispatch cost is not established.

## Results

Three repetitions, mean ± standard deviation, all model layers on the card (`-ngl 99`).

| Model | Flash attention | pp512 (t/s) | tg128 (t/s) |
|---|---|---:|---:|
| Qwen2.5-7B Q4_K_M, 4.36 GiB | build default | 2426.43 ± 8.86 | 24.04 ± 0.14 |
| Qwen2.5-7B Q4_K_M | off | 2110.59 ± 32.65 | 20.97 ± 0.04 |
| Qwen2.5-7B Q4_K_M | on | 2372.53 ± 28.62 | 23.63 ± 0.47 |
| Llama-2-7B Q4_0, 3.56 GiB | on | 2690.56 | 23.93 |

The default-setting row and the fa 0 and fa 1 rows are separate `llama-bench` invocations. The Llama-2 row has no recorded deviation. A longer decode (tg256, flash attention on) read 24.27 t/s with `power_dpm_force_performance_level` on `auto` and 24.20 t/s on `high`: no difference.

During decode: GPU busy 95 to 99 percent, sclk 3.1 GHz, mclk 1258 MHz, board power 115 to 125 W (`power1_average`). Memory use (fa 0 run): 4.44 GB VRAM, 0.47 GB GTT, 1.9 MB of the 256 MiB visible VRAM.

## RX 7600 on the same host, for comparison

The numbers come from the [RX 7600 record](2026-10-22-rx7600-m2max-llamacpp-vulkan.md), measured on earlier boots with the same llama.cpp commit and Mesa 26.2.5. They were not re-measured on the 9070's boot.

| Card | pp512 (t/s) | tg128 (t/s) |
|---|---:|---:|
| RX 9070 (this record, default flash attention) | 2426.43 ± 8.86 | 24.04 ± 0.14 |
| RX 7600 (default flash attention, 1 CPU online) | 967.77 ± 1.09 | 31.65 ± 0.03 |
| RX 7600 (fa 0, 12 CPUs) | 945.81 ± 1.99 | 28.93 ± 0.01 |

The 7600 decode rate varies from 28.9 to 31.9 t/s across boots. The CPU count of the 9070 boot is not recorded in these notes.

## Environment

| Field | Value |
|---|---|
| Host | 14-inch M2 Max MacBook Pro, Omarchy Linux, 16 KiB pages |
| Kernel | `7.1.12-2-20261013.18-egpu-ARCH` (aarch64, local build with unpublished driver and device-tree changes) |
| Card | ASRock RX 9070 Challenger 16GB, `1002:7550` (subsystem `1849:5406`), bound to amdgpu; the RX 7600 was held off with `driver_override=none` |
| Chain | Host USB4 port to an enclosure with a PCIe slot. The enclosure was a "Trebleet" according to the person who set it up; it is not in the run logs |
| GPU driver | local amdgpu module, SHA-256 `1388ccac…`, loaded with `egpu_vram_map=4` |
| Vulkan | RADV, Mesa `26.2.5-arch1.1`, staged package; RADV prints "not a conformant Vulkan implementation" |
| llama.cpp | build `65840ed53` (11449), `llama-bench` 0.6.0-dev, Vulkan backend |
| Link | sysfs `current_link_speed` 32.0 GT/s, `current_link_width` 16: what the card trained at behind the dock. The speed of the USB4 tunnel itself was not measured |
| Command | `GGML_VK_VISIBLE_DEVICES=0 llama-bench -m qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf -p 512 -n 128 -r 3 -ngl 99 -fa 0,1` |
| Environment switches | The run script sets no `RADV_PERFTEST` and no `GGML_VK_*` switch except `GGML_VK_VISIBLE_DEVICES`. The dispatch section names its own switches |
| Power | Board power from the sysfs counter above. PSU model and connectors not recorded |

## Card initialization

The kernel log of a probe boot on the same kernel and module shows amdgpu initializing the card: IP blocks `gfx_v12_0` and `sdma_v7_0`, `Detected VRAM RAM=16304M, BAR=256M`, 256-bit GDDR6, 48251M of GTT, DMUB firmware loaded through PSP (`0x0A004B00`), VCN firmware 1.12, SMU firmware 104.80.0, Display Core v3.2.378 on DCN 4.0.1, and rings `gfx_0.0.0`, four compute rings, `sdma0`, `sdma1`, `vcn_unified_0` and `jpeg_dec`. The driver's own non-posted VRAM test passed (0 of 1024 dwords and 0 of 512 qwords mismatched through MM_INDEX, 0 mismatches in the 64 KiB write and read tests). PCI enumeration shows BAR0 256 MiB, BAR2 2 MiB and BAR5 512 KiB; the 16 GiB resizable BAR is not available because the tunnel window is 8 GiB. Vulkan reports a 16.00 GiB device heap and a 47.12 GiB host heap.

## Where the decode time goes

`GGML_VK_PERF_LOGGER=1 llama-bench -p 0 -n 16 -r 1 -ngl 99 -fa 1`, one decode graph of Qwen2.5-7B Q4_K_M. Two consecutive graphs matched within 1 percent: 34266.8 us and 34392.6 us per token. The first graph:

| Op | Dispatches per token | us per dispatch | Total us |
|---|---:|---:|---:|
| ADD | 1 | 51.88 | 51.88 |
| FLASH_ATTN_EXT (128, 28 heads, k 256) | 28 | 117.778 | 3297.8 |
| GET_ROWS | 2 | 46.06 | 92.12 |
| GLU | 28 | 47.498 | 1329.96 |
| MUL_MAT_ADD MUL_MAT_VEC q4_K m=3584 k=18944 | 14 | 148.897 | 2084.56 |
| MUL_MAT_ADD MUL_MAT_VEC q4_K m=3584 k=3584 | 55 | 116.818 | 6425 |
| MUL_MAT_ADD MUL_MAT_VEC q4_K m=512 k=3584 | 42 | 21.53 | 904.28 |
| MUL_MAT_ADD MUL_MAT_VEC q6_K m=3584 k=18944 | 14 | 113.414 | 1587.8 |
| MUL_MAT_ADD MUL_MAT_VEC q6_K m=512 k=3584 | 14 | 63.24 | 885.36 |
| MUL_MAT_VEC q4_K m=18944 k=3584 | 56 | 117.005 | 6552.28 |
| MUL_MAT_VEC q4_K m=3584 k=3584 | 1 | 111.2 | 111.2 |
| MUL_MAT_VEC q6_K m=152064 k=3584 | 1 | 808.28 | 808.28 |
| RMS_NORM_MUL (3584) | 57 | 107.543 | 6129.96 |
| ROPE | 28 | 47.858 | 1340.04 |
| ROPE_VIEW_SET_ROWS ROPE | 28 | 48.607 | 1361 |
| SET_ROWS | 28 | 46.617 | 1305.28 |
| **Total** | **397** | | **34266.8** |

The rows add up to 397 dispatches and 34266.8 us. The small element-wise ops (ADD, GET_ROWS, GLU, ROPE, SET_ROWS) all sit at 46 to 52 us per dispatch, although they move very little data.

### Decode time follows the dispatch count

Same runs, `-p 0 -n 16 -fa 1`:

| Setting | Dispatches in the graph | GPU time per token | tg16 (t/s) |
|---|---:|---:|---:|
| default (fusion on) | 397 | 36371.6 us | 24.94 |
| `GGML_VK_DISABLE_FUSION=1` | 621 | 45382.5 us | 20.43 |
| `GGML_VK_DISABLE_FUSION=1` and `GGML_VK_DISABLE_MULTI_ADD=1` | 621 | 45328.8 us | 20.46 |

Turning fusion off adds 224 dispatches and 9.0 ms per token: 40 us for each extra dispatch. Two more observations point the same way. The two 7B models read the same decode rate (Qwen2.5 at 4.36 GiB: 24.04 t/s; Llama-2 at 3.56 GiB: 23.93 t/s), and the clock and power state do not matter (`auto` against `high`: 24.27 against 24.20 t/s). The Llama-2 graph's dispatch count was not recorded, so the model comparison supports the finding without proving it.

### Round-trip timing of an empty submit

A small Vulkan program (`vkrtt.c`) submits empty command buffers to the RX 9070 only:

| Measurement | Result |
|---|---|
| `vkQueueSubmit` + `vkWaitForFences`, empty, 1000 iterations | 88.7 us and 101.0 us per round trip (two runs) |
| `vkQueueSubmit` only, one wait at the end | 27.7 us and 27.9 us per submit |
| One command buffer with 1, 100, 500 or 2000 global memory barriers | 96 to 107 us in total, no growth. Not a valid barrier test: there is no dispatch between the barriers and the driver may drop them |
| The M2's own GPU, same program | 1.0 us per round trip |

These costs are of the same order as the 40 to 52 us per dispatch above. The data do not show that decode dispatches pay them.

## What is established and what is not

Established by these runs:

- Decode time per token scales with the dispatch count, at about 40 us per extra dispatch.
- It does not scale with the bytes read: the 3.56 GiB and 4.36 GiB models decode at the same rate.
- It does not depend on the DPM level, and the GPU reads 95 to 99 percent busy.
- An empty submit and wait is far slower on this card (about 89 to 101 us) than on the M2's own GPU (1.0 us).

Not established: why each dispatch costs 40 to 50 us. "A fence or barrier wait on memory behind the tunnel" is a guess, not a measurement.

Not tried on this card: a newer llama.cpp, any RADV switch, a 27B model, the 7600 on the same boot. The [RX 7600 record](2026-10-22-rx7600-m2max-llamacpp-vulkan.md) found a free decode gain from `RADV_PERFTEST=nogttspill,dmashaders` and from the graphics queue on that card. Whether either helps the 9070 is open.

## Repeatability limits

The driver build and the device-tree change are local and unpublished. Do not expect these numbers from a stock kernel or stock device tree. Hot-plug is untested: the card was present at boot. One host, three repetitions, one boot for the main table. The matched Metal baseline has not run, and no x86 reference run of this card exists here.
