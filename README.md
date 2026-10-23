# omarchy-egpu

Set up an external GPU on Omarchy, check each layer, and run local inference when the card is ready. This repo covers AMD RX 7600 and RX 9070, Intel Arc Pro B60, and NVIDIA RTX 5060 Ti on x86 and Apple Silicon Linux hosts.

The RX 7600 (Navi 33, RDNA3) now runs local inference on a 14-inch M2 Max MacBook Pro. amdgpu loads with no ring errors and llama.cpp on Vulkan (RADV) runs on it with all 12 CPUs online. On the exact command and model from a community native-PCIe thread, the card keeps 86 percent of native prompt processing and 50 percent of native decode over the USB4 tunnel (tg128 29.26 vs 58.03 with default driver settings; with `RADV_PERFTEST=nogttspill,dmashaders` the same model reads 38.0 to 38.2, about 66 percent of native); Qwen2.5-7B Q4_K_M reads tg128 28.9-31.9 across boots, and decode is GPU- or driver-side, not CPU-limited. One free gain: `GGML_VK_DISABLE_MMVQ=1` adds 7-8 percent decode. It took a one-line device-tree memory-window change plus kernel patch 0014, which fixes a Vulkan SIGBUS. The kernel work is open as [linux-aurora PR #188](https://github.com/omacom/linux-aurora/pull/188) (ten commits, head `3f5c88fa`), which replaces the earlier PR #184. It is not merged, so none of it is upstream yet. Real cable hot-plug is still untested: the card was attached at boot. See the [host result](hosts/m2-max/), the [benchmark record](benchmarks/2026-10-22-rx7600-m2max-llamacpp-vulkan.md), and [how to check your own chain](#quick-start).

## Quick start

1. Read your [host guide](hosts/) and [card guide](#cards). Check the status before changing packages or boot settings.
2. Check the [dock, power, and cable requirements](docks/). Power the dock and card before connecting the host cable.
3. Run the read-only diagnostic from a terminal:

   ```bash
   git clone https://github.com/joshuaswarren/omarchy-egpu.git
   cd omarchy-egpu
   python3 scripts/egpu_doctor.py --help
   python3 scripts/egpu_doctor.py
   ```

4. Confirm that the external card has assigned memory BARs, a bound driver, and a matching hardware Vulkan device. A software renderer or the integrated GPU does not qualify.
5. Use the card's inference recipe. Record the exact model, command, versions, and result with the [benchmark method](benchmarks/).

The helper never installs packages, authorizes devices, rescans a bus, or changes a boot entry. See [its options and exit codes](scripts/).

## Status

This matrix separates evidence stages. `MEASURED` names an actual runtime observation. `BUILT-UNTESTED` means a driver compiled for the shared target but has no card runtime proof. `BLOCKED` names the missing prerequisite or observed failure. An untested cell does not mean the hardware cannot work.

| Card | 13-inch M1 MacBook Pro | 16-inch M1 Max MacBook Pro | 14-inch M2 Max MacBook Pro | M6 Mac mini | x86 Omarchy |
|---|---|---|---|---|---|
| RX 7600 8GB | BLOCKED: no GPU runtime proof | BLOCKED: no GPU runtime proof | MEASURED: amdgpu loads with all rings; llama.cpp Vulkan runs (Qwen2.5-7B Q4_K_M pp512 945.8-967.6, tg128 28.9-31.9 t/s across boots; Llama-2-7B Q4_0 tg128 38.0-38.2 with the `dmashaders` setting); needs local device-tree and kernel changes; hot-plug untested | BLOCKED: host transport support | BLOCKED: no reference run recorded |
| RX 9070 16GB | BLOCKED: no GPU runtime proof | BLOCKED: no GPU runtime proof | BLOCKED: no GPU runtime proof | BLOCKED: host transport support | BLOCKED: no reference run recorded |
| Arc Pro B60 24GB | BLOCKED: xe 4K-page requirement | MEASURED: llama.cpp Vulkan runs on a 10-CPU boot. Headline: Qwen3.8-27B Q4_0 (unsloth) runs fully on the card (66 of 66 layers) at pp512 428.04 and tg128 17.28 t/s. That is fa1, n=5. Flash attention 0 gave 432.70 and 17.32. The UD-Q4_K_M file of the same model gives pp512 442.61 and tg128 13.12. No native reference was measured for the 27B. Private ANV and xe patches (not upstream) give Llama-2-7B Q4_0 tg128 of 63.8 fa0 and 66.0 fa1. That is about 93 to 94 percent of the thread's native B60 at matched flash attention. The stock buffer placement gave Qwen2.5-7B Q4_K_M tg128 20.6 t/s. It needs local xe patches. Hot-plug is untested | BLOCKED: no GPU runtime proof | BLOCKED: host transport support | BLOCKED: no reference run recorded |
| RTX 5060 Ti 16GB | BUILT-UNTESTED: nouveau, shared 16K target | BUILT-UNTESTED: shared target, host config unverified | BUILT-UNTESTED: nouveau, shared 16K target | BLOCKED: no host-specific build or transport proof | BLOCKED: no reference run recorded |

Evidence cutoff: 2026-10-23 for the RX 7600 and Arc Pro B60 rows, 2026-10-22 for the others. The shared NVIDIA build targets kernel `7.1.12-2-20261013.18-sep-ARCH`, source `6f63677751854d57bcfac172314957bc2197c05f`. It is not proof that a module was installed or loaded. AMD and Intel build details belong in their card guides; the matrix reports runtime readiness.

## FAQ

### How is this different from tinygrad's TinyGPU?

TinyGPU is a macOS app that installs a driver extension. Its [documentation](https://github.com/tinygrad/tinygrad/blob/master/docs/tinygpu.md) says it lets tinygrad use AMD RDNA3 and newer and NVIDIA Ampere and newer cards over USB4 on macOS. This project boots Linux on the Mac and uses the kernel's own `amdgpu` and `xe` drivers with Mesa Vulkan. Any Vulkan program can then use the card. llama.cpp is the one we measured, and it ran on both an AMD and an Intel card. We have not run TinyGPU and make no speed comparison with it.

### Is this a virtual machine?

No. Linux boots directly on the Mac hardware through the m1n1 boot chain, and the USB4 tunnel to the card is handled by the Linux Apple PCIe driver. The [M2 Max host page](hosts/m2-max/README.md) and the [headline record](benchmarks/2026-10-22-rx7600-m2max-llamacpp-vulkan.md) describe the boot chain and the 12-CPU result.

### Does the whole model sit on the card?

In our runs, yes. The Qwen3.8-27B Q4_0 run reported `offloaded 66/66 layers to GPU` with a 14367.22 MiB model buffer on the card, and free card memory fell from 21573 MiB to 8021 MiB. One small table of 682.03 MiB stays in host memory because llama.cpp keeps the token embeddings there. No layers were split between the card and the Mac's unified memory. See the [B60 record](benchmarks/2026-10-23-b60-m1max-llamacpp-vulkan.md#qwen38-27b-fully-on-the-card-2026-10-23).

### When does the card beat the Mac's own GPU?

We have not measured the built-in GPU of either Mac. The matched macOS Metal baseline in the [method](benchmarks/method.md) has not been run. The table sets our card numbers beside the public llama.cpp [Apple Silicon thread](https://github.com/ggml-org/llama.cpp/discussions/4167), which lists Llama-2-7B Q4_0 for each chip at two GPU core counts. Our receipts do not record our Macs' core counts, so both thread values are shown. The thread used a different llama.cpp commit, did not state a flash attention setting for these rows, and did not run on our machines. Read the table as a rough guide and not as a matched ratio.

| Mac and card | Our built-in GPU run | Thread built-in GPU, pp512 / tg128 | Card over USB4, pp512 / tg128 |
|---|---|---|---|
| 14-inch M2 Max with RX 7600 | not measured | 537.60 / 60.99 (30 cores), 671.31 / 65.95 (38 cores) | 1024.5 to 1025.1 / 38.15 to 38.18 (fa0), 1242.3 to 1259.4 / 40.95 to 41.07 (fa1) |
| 16-inch M1 Max with Arc Pro B60 | not measured | 400.26 / 54.61 (24 cores), 530.06 / 61.19 (32 cores) | 1330.26 / 63.80 (fa0), 1418.34 / 65.96 (fa1) |

On these numbers the card is faster at prompt processing on both Macs. For decode, the B60 is above the thread's M1 Max values, and the RX 7600 is well below the thread's M2 Max values. The RX 7600 decode uses the `dmashaders` setting from the [headline record](benchmarks/2026-10-22-rx7600-m2max-llamacpp-vulkan.md). The B60 decode uses private driver patches that are not upstream, from the [B60 record](benchmarks/2026-10-23-b60-m1max-llamacpp-vulkan.md). Larger models are where a 24 GiB card can matter most, but we have no built-in-GPU number for them either.

## Cards

| Card | Guide | First Linux route | Other recipes |
|---|---|---|---|
| ASRock Radeon RX 7600 Challenger 8GB OC | [RX 7600](cards/rx-7600/) | amdgpu + RADV + llama.cpp Vulkan | ROCm and runner constraints in guide |
| ASRock RX 9070 Challenger 16GB | [RX 9070](cards/rx-9070/) | amdgpu + RADV + llama.cpp Vulkan | ROCm and runner constraints in guide |
| Intel Arc Pro B60 | [Arc Pro B60](cards/arc-pro-b60/) | xe + ANV + llama.cpp Vulkan | Intel-specific runtime constraints in guide |
| NVIDIA RTX 5060 Ti 16GB | [RTX 5060 Ti](cards/rtx-5060-ti/) | nouveau + NVK for the Apple Silicon build | NVIDIA-open/CUDA reference path in guide |

MLX support on an integrated Apple GPU does not establish support for an external AMD, Intel, or NVIDIA card. Each guide states its limits. Retain the integrated GPU's driver and Vulkan ICD.

## Hosts and docks

[Host guides](hosts/) cover page size, kernel parameters, PCI apertures, and the M2 hot-plug bus-range failure. [Dock notes](docks/) cover the OwlTree/Rosewill chain, Maskedfish MK-Q1L, Sonnet Breakaway Box 850 T5, ACASIS TB501 Pro, and ADT-Link UT3G. A USB-C connector or a USB4 label alone does not prove PCIe tunneling.

The M1 Ultra Mac Studio is not a Linux host in this repo. No result from it counts as an Apple Silicon Linux eGPU result.

## Patches and measurements

Card guides identify carried patches and config fragments, their base revisions, and upstream status. No patch is described as upstream unless a public merge proves it. No firmware is bundled.

[Benchmarks](benchmarks/) contains the method and measured data. Attachment observations are separate from inference performance. Unknown power or link metadata remains unknown; it is never replaced with a vendor specification.

Our scripts and documentation use [MIT](LICENSE). Kernel and Mesa patches retain their own licenses; see [license boundaries](LICENSES.md).
