# Arc Pro B60 on a 16-inch M1 Max MacBook Pro: llama.cpp Vulkan, 2026-10-23

MEASURED: llama.cpp inference ran on the external card through Intel's ANV Vulkan driver. The kernel log from driver load to the end of the runs shows no error, fault, SError, DART, or timeout line. A follow-up run with all 10 CPUs online (stock device tree) is the reference for the stock buffer placement on Qwen2.5-7B Q4_K_M: pp512 1026.81 ± 3.40 / tg128 20.64 ± 0.06 with flash attention off, and 1057.67 ± 73.17 / 24.45 ± 0.13 with it on. Decode varies 20 to 25 percent run to run on this setup (other jobs co-ran), so the single-core 22.29 below sits inside that spread; the 10-core boot did not change decode beyond it. Prompt processing rose to 1026.81-1097.61. Later the same day, moving the Intel driver's CPU-written buffers into VRAM lifted Llama-2-7B Q4_0 decode on this card from 18.89 to 65.96 t/s (fa1); see [the section below](#intel-driver-buffers-in-vram-2026-10-23). Those results need private driver patches that are not upstream.

| Test | Tokens per second |
|---|---:|
| pp512 (prompt processing) | 968.87 ± 12.77 |
| tg128 (decode) | 22.29 ± 0.40 |

Three repetitions, mean ± standard deviation, all model layers on the card.

## Environment

| Field | Value |
|---|---|
| Host | 16-inch M1 Max MacBook Pro, Omarchy Linux, 16 KiB pages, 1 CPU online (this first run; the later runs below used 10 CPUs) |
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


## 10-CPU rerun, 2026-10-23

Boot with the stock device tree: all 10 cores online. On this machine the 64-bit prefetchable window needed two runtime steps for the test, both applied from the hub's own bridges: a write of 1 to the tunnel root port's prefetchable-window enable register (`PORT_PREFMEM_ENABLE`, which read 0), and bridge/BAR bus addresses equal to CPU addresses (the stock tree maps PCI `0x8_00000000` to CPU `0x10_00000000`). Same command shape as below. Qwen2.5-7B Q4_K_M, other background jobs co-running:

| Run | pp512 | tg128 |
|---|---:|---:|
| flash-attention off (headline) | 1026.81 ± 3.40 | 20.64 ± 0.06 |
| flash-attention on (headline) | 1057.67 ± 73.17 | 24.45 ± 0.13 |
| flash-attention off (second run) | 1097.61 ± 6.19 | 25.42 ± 0.46 |
| flash-attention on (second run) | 985.72 ± 5.22 | 23.95 ± 0.03 |

Larger models on the 24 GiB card (second run): Qwen2.5-14B Q4_K_M pp512 567.29 / tg128 14.80 (fa off; 566.53 / 14.51 on), and Qwen3-14B Q4_K_M 537.73 / 9.10 (535.37 / 9.12 on). Both fit entirely in VRAM. Qwen3-14B decodes slower than the same-size Qwen2.5; the cause is not isolated. A settings sweep on the single-core boot found the defaults and `-fa 1` best on this setup; disabling coopmat cost 32 percent of prompt processing and disabling f16 cost 57 percent.

The 10-core boot did not lift decode beyond the 20-25 percent run-to-run spread, so as with the RX 7600, decode here is GPU- or driver-side, not CPU-limited; the extra cores lifted prompt processing.

## Cross-vendor small-op cost

The same-command Llama-2-7B Q4_0 run on this card (10 CPUs) read pp512 974.84 / tg128 14.39 (fa0) and 1001.76 / 17.63 (fa1), with a measured ~23 us per tiny dispatch. The RX 7600 on its tunnel reads ~22 us per small op. Two vendors, two drivers, two hosts: the shared per-operation cost is measured on both sides. Driver buffers that the CPU writes sit in system memory behind the tunnel on both cards, and moving them to VRAM removes much of the cost (the next section and the [RX 7600 window l section](2026-10-22-rx7600-m2max-llamacpp-vulkan.md#window-l-shader-placement-measured-abab-and-a-proposed-fix-2026-10-23)). The barrier explanation was a hypothesis; barrier flavours measured flat at about 3 us on the RX 7600. See the [cross-vendor section](2026-10-23-rx7600-m2max-model-sweep.md#cross-vendor-small-op-cost-2026-10-23) of the RX 7600 sweep.
## Intel driver buffers in VRAM, 2026-10-23

MEASURED on the same 16-inch M1 Max chain with all 10 CPUs online, kernel `7.1.12-2-20261013.18-egpu-ARCH` with local xe patches 0005 to 0014 and the local Apple PCIe change, and ANV from Mesa 26.2.4 with a private build patch. llama.cpp `65840ed53c8653bfbf3e9014d9cbf71ac8c08725`, Vulkan, Llama-2-7B Q4_0 (the model of the [llama.cpp Vulkan discussion](https://github.com/ggml-org/llama.cpp/discussions/10879)), `-ngl 100 -r 3`, `GGML_VK_DISABLE_HOST_VISIBLE_VIDMEM=1`, same boot for every row.

The cause, and how each step was found. Our kernel patches place every user buffer the CPU maps in system memory, because CPU stores into the non-posted BAR fault. ANV keeps its shader code and several state pools in such buffers, so the GPU can only read them across the USB4 link. That placement is MEASURED by the speed change below; that instruction and state fetches over the link are the cost is INFERRED, and consistent with the [RX 7600 result](2026-10-22-rx7600-m2max-llamacpp-vulkan.md#window-l-shader-placement-measured-abab-and-a-proposed-fix-2026-10-23). A private ANV patch and an opt-in xe buffer property (patch 0014) let selected buffer classes stay in VRAM, written with aligned 64-bit and byte stores only.

| Variant | fa1 pp512 | fa1 tg128 | fa0 pp512 | fa0 tg128 |
|---|---:|---:|---:|---:|
| xe 0013, no buffer change | 1031.13 ± 0.99 | 17.96 ± 0.06 | 1014.50 ± 4.70 | 14.74 ± 0.28 |
| xe 0014, setting off | 1101.27 ± 1.12 | 18.89 ± 0.07 | 1036.42 ± 9.79 | 14.96 ± 0.04 |
| shader code in VRAM (`ANV_SHADER_HEAP_VRAM=1`) | 1413.82 ± 2.98 | 45.80 ± 0.29 | 1347.79 ± 1.76 | 43.14 ± 0.29 |
| shader code and five more buffer classes in VRAM | 1418.34 ± 8.55 | **65.96 ± 0.13** | 1330.26 ± 9.43 | **63.80 ± 0.03** |

Decode rises 3.5 times at fa1 (18.89 to 65.96) and 4.3 times at fa0 (14.96 to 63.80). Shader code alone gives 2.4 times (fa1). Prompt processing rises 29 percent at fa1 and 28 percent at fa0 against the setting-off row.

One buffer class at a time on top of the shader code (Llama-2-7B Q4_0, fa1, decode only, `-n 128`, n=2):

| Extra buffer class in VRAM | tg128 |
|---|---:|
| none (shader code only) | 45.82 ± 0.11 |
| binding tables | 47.50 ± 0.06 |
| bindless surface states | 46.11 ± 0.07 |
| general state | 48.91 ± 0.09 |
| indirect push descriptors | 46.16 ± 0.12 |
| **descriptor sets** | **56.12 ± 0.03** |
| internal surface states | bus error (INFERRED: its CPU writes are not alignment-safe) |
| dynamic state | bus error (same) |

The five non-crashing classes together, with the shader code, are the last row of the first table. They are selected with `ANV_SHADER_HEAP_VRAM=1` and `ANV_NP_VRAM_POOLS="descriptor-bo;general pool;binding table pool;bindless surface state pool;indirect push descriptor pool"`. llama.cpp still needs `GGML_VK_DISABLE_HOST_VISIBLE_VIDMEM=1`.

Other models with the same buffer set (`-ngl 99`, `-p 512 -n 128 -r 3`, 10 CPUs):

| Model | fa1 pp512 | fa1 tg128 | fa0 pp512 | fa0 tg128 |
|---|---:|---:|---:|---:|
| Qwen3-1.7B Q4_K_M | 3121.85 ± 49.22 | 99.75 ± 0.41 | 3031.92 ± 110.45 | 100.62 ± 0.50 |
| Qwen2.5-7B-Instruct Q4_K_M | 1439.92 ± 9.53 | 55.88 ± 0.08 | 1429.87 ± 19.51 | 55.78 ± 0.01 |
| Qwen3-8B Q4_K_M | 1191.06 ± 4.79 | 46.90 ± 0.02 | 1210.15 ± 4.66 | 46.89 ± 0.04 |
| Qwen2.5-14B-Instruct Q4_K_M | 716.65 ± 133.13 (one noisy repetition) | 31.47 ± 0.02 | 817.65 ± 4.34 | 31.48 ± 0.05 |
| Qwen2.5-32B-Instruct Q4_K_M (18.5 GiB) | 423.19 ± 0.35 | 15.81 ± 0.01 | 434.29 ± 0.77 | 15.79 ± 0.01 |

The temperature-0 check on Qwen2.5-7B answered "The capital of France is Paris." No kernel error, fault or timeout line appeared in any run.

### Against the native-PCIe B60 in the public thread

The thread has a native Arc Pro B60 Vulkan entry: [a comment from 2026-01-17](https://github.com/ggml-org/llama.cpp/discussions/10879#discussioncomment-15523099), the B60 as the second GPU in an x86 PC beside an RTX 4070 Ti, Mesa 25.1.5, llama.cpp build `516a4ca`, Llama-2-7B Q4_0, `-ngl 100`. It reads pp512 522.36 ± 3.60 / tg128 68.55 ± 0.01 with flash attention off and pp512 274.76 ± 0.27 / tg128 70.54 ± 0.03 with it on.

Matched on flash attention, decode here is 63.80 / 68.55 = 93 percent (fa0) and 65.96 / 70.54 = 94 percent (fa1) of that native entry. Prompt processing here is 2.5 times (fa0) and 5.2 times (fa1) the thread's values. The comparison is indicative, not like for like: a different llama.cpp commit, Mesa version, host CPU and driver stack, and the thread's run had a second GPU in the machine.

Before this change the same card decoded this model at 14.96 (fa0) and 18.89 t/s (fa1), 22 percent and 27 percent of the thread's native values at matched flash attention.

### Not done and not upstream

The remaining driver buffers (internal surface states, dynamic state, batch buffers) are still in system memory; the two crashing classes need alignment-safe CPU writes. Hot-plug is untested. The xe patches 0005 to 0014 and the ANV change are private patches, not yet upstream, and no merge request or pull request for them exists. The xe 0014 patch SHA-256 is `967e91a9c2ee9b47a40b95e50b156865093b148780335db8ae3fc0ca1d7f3384`; the ANV patch is `d15848dd88753c1e8e39ca6806486b2fb8e5da7262fa333ff65806d115845572`.

## Qwen3.8-27B fully on the card, 2026-10-23

MEASURED. Qwen3.8-27B (unsloth `Qwen3.8-27B-UD-Q4_K_M.gguf`, base model Qwen/Qwen3.8-27B, Apache-2.0) runs with all 66 layers on the B60. The file is 16,464,440,224 bytes (15.32 GiB), SHA-256 `322e194ff79741c7baa497c240f677f54b201b0efab44ca8e50f122b39123482`, and the hash equals the Hugging Face LFS object id. The architecture is `qwen35`.

The run used the same 16-inch M1 Max chain with 10 CPUs online, llama.cpp commit `65840ed53c8653bfbf3e9014d9cbf71ac8c08725` (Vulkan), `-ngl 99`, `GGML_VK_DISABLE_HOST_VISIBLE_VIDMEM=1`, and the private ANV build with the same five descriptor and state pools in VRAM. The kernel carried the Apple PCIe prefetchable-window commit. This run used a later private `xe` build than the 7B runs above (call it 0015; those used 0014). It keeps the same buffers in VRAM and keeps the GPU page tables and the firmware scheduler buffer there too. It is private and not upstream. The xe 0015 module SHA-256 is `69424489ef836487633bf941812e674d9c02d9658d37a47a98b77046748f8722`.

| Flash attention | pp512 t/s | tg128 t/s |
|---|---:|---:|
| 1 | 442.61 ± 0.22 | 13.12 ± 0.00 |
| 0 | 450.55 ± 0.70 | 13.12 ± 0.01 |

Five repetitions per cell, mean ± standard deviation, from `llama-bench`. The system log showed no xe timeout, wedge or error lines after the runs.

A second file of the same model, unsloth `Qwen3.8-27B-Q4_0.gguf` (plain Q4_0, 16,056,478,688 bytes, 14.94 GiB, SHA-256 `ede16c7b36e578ca87a8c70e011e4b4633a32c831c0ce76d0f474582384e671d`, equal to the Hugging Face LFS object id), ran on the same setup, boot, build and method, one hour later. It also loads fully on the card: 66 of 66 layers, a 14367.22 MiB Vulkan model buffer, the same 512 MiB KV buffer, 149.62 MiB recurrent state and 150.02 MiB compute buffer, and free card memory fell from 21573 MiB to 8021 MiB. The temperature-0 answer to "The capital of France is" was "Paris". The system log showed no xe timeout, wedge or error lines.

| File | Size | Flash attention | pp512 t/s | tg128 t/s |
|---|---:|---:|---:|---:|
| UD-Q4_K_M | 15.32 GiB | 1 | 442.61 ± 0.22 | 13.12 ± 0.00 |
| UD-Q4_K_M | 15.32 GiB | 0 | 450.55 ± 0.70 | 13.12 ± 0.01 |
| Q4_0 | 14.94 GiB | 1 | 428.04 ± 0.86 | 17.28 ± 0.01 |
| Q4_0 | 14.94 GiB | 0 | 432.70 ± 1.70 | 17.32 ± 0.01 |

Plain Q4_0 decodes about 32 percent faster than UD-Q4_K_M (17.28 against 13.12 at flash attention 1) and prompt processing is about 3 percent slower. The per-op breakdown below was measured on the UD-Q4_K_M file only. The Q4_0 gain fits that explanation (a uniform quantization avoids the slow `iq4_xs` kernels) but I did not run the per-op logger on the Q4_0 file, so that part is INFERRED.

Load proof with `-ngl 99 -c 8192`: `offloaded 66/66 layers to GPU`. The Vulkan model buffer is 14674.45 MiB. The 682.03 MiB token-embedding table stays in host memory because llama.cpp keeps it there by design. The KV buffer is 512 MiB, the recurrent-state buffer is 149.62 MiB and the compute buffer is 150.02 MiB, all on the card. Free card memory fell from 21575 MiB to 7712 MiB of 24480 MiB. A temperature-0 run completed. It started in thinking mode and answered the prompt "The capital of France is" with "Answer Paris." The generation rate in that run includes warm-up and is not a benchmark.

Why UD-Q4_K_M decode is 13 t/s. MEASURED with the llama.cpp Vulkan per-op logger on a 32-token decode: the GPU kernels take 72.9 ms of each 76.2 ms token, so about 96 percent of decode time is inside GPU kernels. This file mixes quantization types. The `q4_K` matrix-vector kernel for one shape runs near 375 GB/s, while the `iq4_xs` kernel for the same shape runs near 165 GB/s. The 61 `iq4_xs` calls per token cost 17.5 ms. The low rate comes from the file's quantization mix and the Vulkan shaders. INFERRED, not measured: a native PCIe slot would give the same rate, because the time is spent inside the GPU kernels.

There is no native-PCIe reference for this model. No machine here has the card in a native slot, and the public llama.cpp thread has only a Llama-2-7B Q4_0 entry. No percent-of-native is given for this 27B result.

## Required workarounds, measured

- `GGML_VK_DISABLE_HOST_VISIBLE_VIDMEM=1` is required. Without it, llama.cpp's host-visible device-local buffers land in system memory here and a small-model run fell from pp128 573.41 / tg32 16.50 to pp128 6.8 / tg32 1.9 t/s.
- The card's 32 GiB resizable-BAR request cannot fit the tunnel window, so the run loads with `xe.vram_bar_size=-1` (no resize attempt). BAR0 16 MiB and BAR2 256 MiB assign on a normal boot with no rescan.
- On this host, every CPU read through the Apple root port's prefetchable window returned all-ones regardless of the device-tree mapping; only the root port's non-prefetchable window forwards. A runtime `setpci` bisect proved the window routing. The one-line kernel fix (extending the prefetchable-window enable condition to `tunnel_cold_init` ports) was later built into a full kernel and booted: on a fresh boot the card's registers and VRAM read correctly with no manual register write. The register reads 0 before and after because it is a write strobe, so the test is the BAR read. The address-equals-CPU-address part is still a runtime `setpci` step until the device-tree identity range reaches the boot image. The change is not upstream.
- Buffer placement rules this card needs behind the tunnel: VRAM BAR mappings must be non-posted; the GuC SLPC shared-data buffer must stay in VRAM; page tables and the migration VM must stay in VRAM (`xe.np_keep_vram_mask=0x7`); other pinned kernel buffers moved to write-combined system memory; user-space mapped buffers must not live in the BAR. The kernel must report the real 256 MiB host-visible VRAM or ANV ignores VRAM entirely and puts weights in system memory.

## Limits

The first run used one CPU; the 10-CPU reruns and the driver-buffer section above are the current reference. In the stock-placement runs decode did not move beyond its 20-25 percent run-to-run spread, so no number here is CPU-starved in a way that hides capacity - but that spread itself is unexplained. Hot-plug is untested. The 32 GiB BAR resize is impossible on this tunnel. The patches are local; kernel pull-request cleanup is next. After a card hang the device wedges and needs a reboot. The address-equals-CPU-address `setpci` step is re-applied after each boot until the device-tree identity range reaches the boot image. The root-port window enable no longer needs a manual write on the newer kernel.

## Not measured

The matched macOS Metal baseline from the [method](method.md#matched-linux-vulkan-and-macos-metal-runs) has not run. Cross-card comparison is still premature: decode on both the RX 7600 and this card is GPU- or driver-side and varies run to run, and the two records were taken under different co-load. On full-core boots the RX 7600 reads pp512 945.8-1097.6 and tg128 28.9-31.9; this card read pp512 985.7-1097.6 and tg128 20.6-25.4 on Qwen2.5-7B before the driver-buffer change above; with it the same model reads tg128 55.8-55.9.
