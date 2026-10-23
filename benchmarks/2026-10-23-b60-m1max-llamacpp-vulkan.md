# Arc Pro B60 on a 16-inch M1 Max MacBook Pro: llama.cpp Vulkan, 2026-10-23

MEASURED: llama.cpp inference ran on the external card through Intel's ANV Vulkan driver. The kernel log from driver load to the end of the runs shows no error, fault, SError, DART, or timeout line. **All numbers on this page are single-CPU lower bounds:** this boot ran with 1 of the host's 10 CPUs online (stale spin-table addresses in the replacement device tree; see the limits section). A full-core rerun is pending.

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

The correctness check at temperature 0 answered "The capital of France is Paris." at 91.7 t/s prompt and 10.1 t/s generation. `vulkaninfo --summary` reports `Intel(R) Arc(tm) Pro B60 Graphics (BMG G21)`, discrete, conformance 1.4.0.0, with 23.66 GiB device-local, 46.78 GiB system, and 256 MiB host-visible device-local heaps. `vkcube` did not run; no display was attached.

## Required workarounds, measured

- `GGML_VK_DISABLE_HOST_VISIBLE_VIDMEM=1` is required. Without it, llama.cpp's host-visible device-local buffers land in system memory here and a small-model run fell from pp128 573.41 / tg32 16.50 to pp128 6.8 / tg32 1.9 t/s.
- The card's 32 GiB resizable-BAR request cannot fit the tunnel window, so the run loads with `xe.vram_bar_size=-1` (no resize attempt). BAR0 16 MiB and BAR2 256 MiB assign on a normal boot with no rescan.
- On this host, every CPU read through the Apple root port's prefetchable window returned all-ones regardless of the device-tree mapping; only the root port's non-prefetchable window forwards. A runtime `setpci` bisect proved the window routing; the current run uses that workaround after each boot. A one-line kernel fix (extending the prefetchable-window enable condition to `tunnel_cold_init` ports) is inferred from the source but not yet booted.
- Buffer placement rules this card needs behind the tunnel: VRAM BAR mappings must be non-posted; the GuC SLPC shared-data buffer must stay in VRAM; page tables and the migration VM must stay in VRAM (`xe.np_keep_vram_mask=0x7`); other pinned kernel buffers moved to write-combined system memory; user-space mapped buffers must not live in the BAR. The kernel must report the real 256 MiB host-visible VRAM or ANV ignores VRAM entirely and puts weights in system memory.

## Limits

One CPU online, shared with other work, so every number is a lower bound. Hot-plug is untested. The 32 GiB BAR resize is impossible on this tunnel. The patches are local; kernel pull-request cleanup is next. After a card hang the device wedges and needs a reboot.

## Not measured

The matched macOS Metal baseline from the [method](method.md#matched-linux-vulkan-and-macos-metal-runs) has not run. Comparisons to the RX 7600 record are not valid until both cards have full-core reruns on the same conditions; on the same single-CPU conditions the RX 7600 read pp512 964.58 / tg128 31.07, so prompt processing matches and decode differs.
