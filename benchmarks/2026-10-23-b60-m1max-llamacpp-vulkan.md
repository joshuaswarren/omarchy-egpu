# Arc Pro B60 on a 16-inch M1 Max MacBook Pro: llama.cpp Vulkan, 2026-10-23

MEASURED: llama.cpp inference ran on the external card through Intel's ANV Vulkan driver. The kernel log from driver load to the end of the runs shows no error, fault, SError, DART, or timeout line. A follow-up run with all 10 CPUs online (stock device tree) is the current reference on Qwen2.5-7B Q4_K_M: pp512 1026.81 ± 3.40 / tg128 20.64 ± 0.06 with flash attention off, and 1057.67 ± 73.17 / 24.45 ± 0.13 with it on. Decode varies 20 to 25 percent run to run on this setup (other lanes' jobs co-ran), so the single-core 22.29 below sits inside that spread; the 10-core boot did not change decode beyond it. Prompt processing rose to 1026.81-1097.61.

| Test | Tokens per second |
|---|---:|
| pp512 (prompt processing) | 968.87 ± 12.77 |
| tg128 (decode) | 22.29 ± 0.40 |

Three repetitions, mean ± standard deviation, all model layers on the card.

## Environment

| Field | Value |
|---|---|
| Host | 16-inch M1 Max MacBook Pro, Omarchy Linux, 16 KiB pages, 1 CPU online |
| Kernel | `7.1.12` local build with unpublished xe patches |
| Card | ASRock Intel Arc Pro B60 (Battlemage G21, 24 GiB), `8086:e211`, bound to xe 1.1.0 |
| Chain | Host port, USB4/Thunderbolt cable, Sonnet Breakaway Box 850 T5 with its own 850 W supply |
| GPU driver | xe with local patches (not published); GuC 70.72.1, HuC 8.2.10, DMC 2.6 loaded |
| Vulkan | ANV built from the Mesa 26.2.4 release tarball (`-Dvulkan-drivers=intel`); the aarch64 distribution package ships no Intel Vulkan driver |
| Model | Qwen2.5-7B-Instruct Q4_K_M, 4.36 GiB |
| llama.cpp | build `65840ed53`, Vulkan backend |
| Command | `GGML_VK_VISIBLE_DEVICES=0 GGML_VK_DISABLE_HOST_VISIBLE_VIDMEM=1 llama-bench -m qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf -p 512 -n 128 -r 3 -ngl 99` |
| Power | Not recorded. Link under load: not recorded |
| Conditions | Scheduled probe window; one short correctness check before the timed runs |


## 10-CPU rerun, 2026-10-23

Boot with the stock device tree: all 10 cores online. On this machine the 64-bit prefetchable window needed two runtime steps for the test, both applied from the hub's own bridges: a write of 1 to the tunnel root port's prefetchable-window enable register (`PORT_PREFMEM_ENABLE`, which read 0), and bridge/BAR bus addresses equal to CPU addresses (the stock tree maps PCI `0x8_00000000` to CPU `0x10_00000000`). Same command shape as below. Qwen2.5-7B Q4_K_M, other lanes' background jobs co-running:

| Run | pp512 | tg128 |
|---|---:|---:|
| flash-attention off (headline) | 1026.81 ± 3.40 | 20.64 ± 0.06 |
| flash-attention on (headline) | 1057.67 ± 73.17 | 24.45 ± 0.13 |
| flash-attention off (second run) | 1097.61 ± 6.19 | 25.42 ± 0.46 |
| flash-attention on (second run) | 985.72 ± 5.22 | 23.95 ± 0.03 |

Larger models on the 24 GiB card (second run): Qwen2.5-14B Q4_K_M pp512 567.29 / tg128 14.80 (fa off; 566.53 / 14.51 on), and Qwen3-14B Q4_K_M 537.73 / 9.10 (535.37 / 9.12 on). Both fit entirely in VRAM. Qwen3-14B decodes slower than the same-size Qwen2.5; the cause is not isolated. A settings sweep on the single-core boot found the defaults and `-fa 1` best on this setup; disabling coopmat cost 32 percent of prompt processing and disabling f16 cost 57 percent.

The 10-core boot did not lift decode beyond the 20-25 percent run-to-run spread, so as with the RX 7600, decode here is GPU- or driver-side, not CPU-limited; the extra cores lifted prompt processing.
The correctness check at temperature 0 answered "The capital of France is Paris." at 91.7 t/s prompt and 10.1 t/s generation. `vulkaninfo --summary` reports `Intel(R) Arc(tm) Pro B60 Graphics (BMG G21)`, discrete, conformance 1.4.0.0, with 23.66 GiB device-local, 46.78 GiB system, and 256 MiB host-visible device-local heaps. `vkcube` did not run; no display was attached.

## Required workarounds, measured

- `GGML_VK_DISABLE_HOST_VISIBLE_VIDMEM=1` is required. Without it, llama.cpp's host-visible device-local buffers land in system memory here and a small-model run fell from pp128 573.41 / tg32 16.50 to pp128 6.8 / tg32 1.9 t/s.
- The card's 32 GiB resizable-BAR request cannot fit the tunnel window, so the run loads with `xe.vram_bar_size=-1` (no resize attempt). BAR0 16 MiB and BAR2 256 MiB assign on a normal boot with no rescan.
- On this host, every CPU read through the Apple root port's prefetchable window returned all-ones regardless of the device-tree mapping; only the root port's non-prefetchable window forwards. A runtime `setpci` bisect proved the window routing; the current run uses that workaround after each boot. A one-line kernel fix (extending the prefetchable-window enable condition to `tunnel_cold_init` ports) is inferred from the source but not yet booted.
- Buffer placement rules this card needs behind the tunnel: VRAM BAR mappings must be non-posted; the GuC SLPC shared-data buffer must stay in VRAM; page tables and the migration VM must stay in VRAM (`xe.np_keep_vram_mask=0x7`); other pinned kernel buffers moved to write-combined system memory; user-space mapped buffers must not live in the BAR. The kernel must report the real 256 MiB host-visible VRAM or ANV ignores VRAM entirely and puts weights in system memory.

## Limits

The first run used one CPU; the 10-CPU rerun above is the current reference, and decode did not move beyond its 20-25 percent run-to-run spread, so no number here is CPU-starved in a way that hides capacity - but that spread itself is unexplained. Hot-plug is untested. The 32 GiB BAR resize is impossible on this tunnel. The patches are local; kernel pull-request cleanup is next. After a card hang the device wedges and needs a reboot. The window workaround is re-applied after each boot until the kernel change lands.

## Not measured

The matched macOS Metal baseline from the [method](method.md#matched-linux-vulkan-and-macos-metal-runs) has not run. Cross-card comparison is still premature: decode on both the RX 7600 and this card is GPU- or driver-side and varies run to run, and the two records were taken under different co-load. On full-core boots the RX 7600 reads pp512 945.8-1097.6 and tg128 28.9-31.9; this card reads pp512 985.7-1097.6 and tg128 20.6-25.4.
