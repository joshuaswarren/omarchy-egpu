# ASRock RX 9070 Challenger 16GB

RDNA4 (Navi 48), 16 GB GDDR6, LLVM target `gfx1201`.

| Property | Value | Source |
|---|---|---|
| PCI ID (GPU) | `1002:7550` | `pci.ids` lookup, recorded 2026-10-16 |
| PCI ID (audio function) | `1002:ab40` | `pci.ids` lookup, recorded 2026-10-16 |
| Card power | 2x 8-pin PCIe | [vendor spec page](https://www.asrock.com/Graphics-Card/AMD/Radeon%20RX%209070%20Challenger%2016GB/index.asp), read 2026-10-12 |
| Recommended PSU | 700 W | same page |
| Slot interface | PCIe 5.0 x16 | same page |
| Board power draw | 115 to 125 W during llama.cpp decode (amdgpu `power1_average`, 2026-10-25). The vendor page publishes no figure | [benchmark record](../../benchmarks/2026-10-25-rx9070-m2max-llamacpp-vulkan.md) |

## Status

Labels follow the repo definition: `MEASURED` is an actual runtime
observation, `BUILT-UNTESTED` means a driver compiled for the shared target
with no card runtime proof, `BLOCKED` names the missing prerequisite or the
observed failure.

| Host | Stage | Evidence |
|---|---|---|
| 14-inch M2 Max MacBook Pro | **MEASURED:** amdgpu initializes the card and its rings, RADV enumerates it, and llama.cpp Vulkan runs on it: Qwen2.5-7B Q4_K_M pp512 2426.43, tg128 24.04 t/s. Needs the same unpublished local driver and device-tree changes as the RX 7600 | [Benchmark record](../../benchmarks/2026-10-25-rx9070-m2max-llamacpp-vulkan.md) |
| 13-inch M1 MacBook Pro | **BLOCKED**: no amdgpu in the kernel build that host runs (checked 2026-10-16); no attach attempted | [setup.md](setup.md) |
| 16-inch M1 Max MacBook Pro | **BLOCKED**: no attach attempted, no run | |
| x86 Omarchy | **BLOCKED**: no reference run recorded on our x86 hosts | |
| Driver module set | **MEASURED** on the M2 Max: a local amdgpu module build (SHA-256 `1388ccac…`, see patches.md for what it changes) loaded and initialized the `gfx1201` card | [patches.md](patches.md) |

The one measured result is on the 14-inch M2 Max, behind unpublished local kernel and device-tree changes. It is not a recipe a stock system can follow yet. No result exists on any other host.

## Why decode is dispatch-bound on this setup

Generating one token runs the whole model as a chain of small GPU jobs, called dispatches, one after another. For Qwen2.5-7B Q4_K_M this is 397 dispatches per token. Each dispatch waits for the one before it.

On this card even the smallest dispatches cost 46 to 52 microseconds each. The element-wise ops (ADD, GET_ROWS, GLU, ROPE, SET_ROWS) move very little data, yet they sit at that level. The large matrix-vector dispatches cost 110 to 150 us, and the output projection 808 us. Total GPU time was 34.3 ms per token, about 24 tokens per second. At 40 us each, 397 dispatches are 15.9 ms of that 34.3 ms: that is arithmetic from the numbers, not a separate measurement.

Three measurements show that the count of dispatches, and not the data volume, sets the speed:

| Test | Result |
|---|---|
| Turn llama.cpp's fusion off: 224 more dispatches | +9.0 ms per token: 40 us per extra dispatch (24.94 to 20.43 t/s) |
| A 3.56 GiB and a 4.36 GiB model | Same decode rate (23.93 and 24.04 t/s) |
| Auto and high power level | Same decode rate (24.27 and 24.20 t/s) |

Over the Thunderbolt tunnel, an empty submit-and-wait to this card takes 89 to 101 us, against 1.0 us on the M2's own GPU. That is the same order of size as the cost per dispatch, but we did not measure that decode dispatches pay it. Why each dispatch costs 40 to 50 us is not established. A newer llama.cpp and the 7600 on the same boot have not been tried. On the next day the flag pair `nogttspill,dmashaders` raised decode by about 27 to 28 percent on two boots, and `dmashaders` alone by 32.6 percent on a third; see the [RADV_PERFTEST record](../../benchmarks/2026-10-26-rx9070-m2max-radv-perftest.md). That record does not say why. The full per-op table and the method are in the [benchmark record](../../benchmarks/2026-10-25-rx9070-m2max-llamacpp-vulkan.md).

The RX 9070 decodes slower (24.0 t/s) than the RX 7600 (28.9 to 31.9 t/s) while prefilling about 2.5 times faster. We did not run the per-op log on the 7600 on the same boot, so we cannot say whether its dispatch cost differs.

## In this directory

| Page | Contents |
|---|---|
| [setup.md](setup.md) | Power, packages, upstream driver facts, read-only inspection, open questions |
| [patches.md](patches.md) | Upstream status, packaging, what is and is not proven |
| [ai.md](ai.md) | Which local-AI stacks can use this card and where |
