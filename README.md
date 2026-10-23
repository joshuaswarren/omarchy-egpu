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
| RTX 5060 Ti 16GB | BLOCKED: no GPU runtime proof | MEASURED: NVIDIA open 595.112.07 loads (two 16K fixes), CUDA 13.2 and Vulkan enumerate; benchmarks pending | BLOCKED: no GPU runtime proof | BLOCKED: host transport support | BLOCKED: no reference run recorded |

Evidence cutoff: 2026-10-23 for the RX 7600 and Arc Pro B60 rows, 2026-10-22 for the others. The shared NVIDIA build targets kernel `7.1.12-2-20261013.18-sep-ARCH`, source `6f63677751854d57bcfac172314957bc2197c05f`. It is not proof that a module was installed or loaded. AMD and Intel build details belong in their card guides; the matrix reports runtime readiness.

## FAQ

### How is this different from tinygrad's TinyGPU?

TinyGPU is a macOS app that installs a driver extension. Its [documentation](https://github.com/tinygrad/tinygrad/blob/master/docs/tinygpu.md) says it lets tinygrad use AMD RDNA3 and newer and NVIDIA Ampere and newer cards over USB4 on macOS. This project boots Linux on the Mac and uses the kernel's own `amdgpu` and `xe` drivers with Mesa Vulkan. Any Vulkan program can then use the card. llama.cpp is the one we measured, and it ran on both an AMD and an Intel card. We have not run TinyGPU and make no speed comparison with it.

### Is this a virtual machine?

No. Linux boots directly on the Mac hardware through the m1n1 boot chain, and the USB4 tunnel to the card is handled by the Linux Apple PCIe driver. The [M2 Max host page](hosts/m2-max/README.md) and the [headline record](benchmarks/2026-10-22-rx7600-m2max-llamacpp-vulkan.md) describe the boot chain and the 12-CPU result.

### Does the whole model sit on the card?

In our runs, yes. The Qwen3.8-27B Q4_0 run reported `offloaded 66/66 layers to GPU` with a 14367.22 MiB model buffer on the card, and free card memory fell from 21573 MiB to 8021 MiB. One small table of 682.03 MiB stays in host memory because llama.cpp keeps the token embeddings there. No layers were split between the card and the Mac's unified memory. See the [B60 record](benchmarks/2026-10-23-b60-m1max-llamacpp-vulkan.md#qwen38-27b-fully-on-the-card-2026-10-23).

### When does the card beat the Mac's own GPU?

It depends on what you measure. We ran llama.cpp on each Mac's own GPU and on its card, with the same llama.cpp commit and the same models. On the 14-inch M2 Max, the RX 7600 was about 3.5 to 4.1 times faster at prompt processing and tied on decode. On the 16-inch M1 Max, the Arc Pro B60 was about 5.7 to 7.4 times faster at prompt processing and about 1.9 to 2.1 times faster at decode. The built-in run used the Mesa Honeykrisp Vulkan driver on Linux, not Metal. The matched macOS Metal baseline in the [method](benchmarks/method.md) has not been run. The table also shows the public llama.cpp [Apple Silicon thread](https://github.com/ggml-org/llama.cpp/discussions/4167), which lists Metal results for each chip at two GPU core counts. Our receipts do not record our Macs' core counts, so both thread values are shown. The thread used a different llama.cpp commit, did not state a flash attention setting for these rows, and did not run on our machines.

| Mac and card | Model | Built-in GPU on Linux, pp512 / tg128 | Card over USB4, pp512 / tg128 |
|---|---|---|---|
| 14-inch M2 Max, RX 7600 | Llama-2-7B Q4_0, fa0 | 293.96 / 38.64 | 1024.5 to 1025.1 / 38.15 to 38.18 |
| 14-inch M2 Max, RX 7600 | Llama-2-7B Q4_0, fa1 | 304.05 / 40.44 | 1242.3 to 1259.4 / 40.95 to 41.07 |
| 14-inch M2 Max, RX 7600 | Qwen2.5-7B Q4_K_M, fa0 | 245.74 / 29.82 | 945.81 / 28.93 (repeats 29.57, 29.49) |
| 14-inch M2 Max, RX 7600 | Qwen2.5-7B Q4_K_M, fa1 | 240.91 / 30.35 | 967.59 / 28.90 (repeats 31.86, 31.39) |
| 16-inch M1 Max, Arc Pro B60 | Llama-2-7B Q4_0, fa0 | 233.76 / 33.16 | 1330.26 / 63.80 |
| 16-inch M1 Max, Arc Pro B60 | Llama-2-7B Q4_0, fa1 | 240.08 / 34.28 | 1418.34 / 65.96 |
| 16-inch M1 Max, Arc Pro B60 | Qwen2.5-7B Q4_K_M, fa0 | 194.36 / 26.10 | 1429.87 / 55.78 |
| 16-inch M1 Max, Arc Pro B60 | Qwen2.5-7B Q4_K_M, fa1 | 197.54 / 26.34 | 1439.92 / 55.88 |

The built-in rows are five repetitions each, from llama.cpp commit `65840ed53` with Mesa 26.2.4, run on the 14-inch machine with the same kernel as its card runs, and on the 16-inch machine with its stock kernel while the B60 runs used the patched kernel. Each Mac built its own ggml libraries from that commit, and the two Macs use different builds of the same Mesa version, so the two built-in sets are not strictly comparable with each other. The card rows are three repetitions: RX 7600 with Mesa 26.2.5 RADV, and B60 with a private Mesa 26.2.4 build and the private driver patches described in the [B60 record](benchmarks/2026-10-23-b60-m1max-llamacpp-vulkan.md). The B60 Qwen2.5 rows match the built-in file by name and size only. The Llama-2 rows use the `dmashaders` setting from the [headline record](benchmarks/2026-10-22-rx7600-m2max-llamacpp-vulkan.md). The Qwen2.5 card rows are the 12-CPU rerun, first run of each setting, with the later repeats in brackets. Decode on that model moved between 28.9 and 31.9 t/s from run to run, so it overlaps the built-in 29.8 to 30.4. The Qwen2.5 file name is the same on both. The Llama-2 file was staged at SHA-256 `78b8f977...` for the card runs and the built-in run used that same hash, though the card run logs do not repeat it.

For reference, the thread's Metal values for the same Llama-2-7B Q4_0 are pp512 537.60 and tg128 60.99 on an M2 Max with 30 GPU cores, and 671.31 and 65.95 with 38 cores. For the M1 Max they are 400.26 and 54.61 with 24 cores, and 530.06 and 61.19 with 32 cores. Those Metal values are well above our Linux built-in runs (for example 61.19 against 34.28 tg128 on the M1 Max). So against Metal, which is what a Mac user gets on macOS, the B60 decodes only about 4 to 21 percent faster than the thread's M1 Max rows, and the RX 7600 decodes well below the thread's M2 Max rows. The B60 decode uses private driver patches that are not upstream. Larger models are where a 24 GiB card should matter most. We have no built-in-GPU number for those either.

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
