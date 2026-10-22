# omarchy-egpu

Set up an external GPU on Omarchy, check each layer, and run local inference when the card is ready. This repo covers AMD RX 7600 and RX 9070, Intel Arc Pro B60, and NVIDIA RTX 5060 Ti on x86 and Apple Silicon Linux hosts.

The RX 7600 on a 14-inch M2 Max MacBook Pro now has assigned BARs on normal boots. A locally patched amdgpu passes PSP, SMU and DMUB initialization, then fails the MES KIQ ring test in GFX initialization. The card remains **BLOCKED**. RADV and llama.cpp have not run; cable hot-plug is still untested. See the [measured result](hosts/m2-max/).

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
| RX 7600 8GB | BLOCKED: no GPU runtime proof | BLOCKED: no GPU runtime proof | MEASURED: normal-boot BARs and partial driver initialization; BLOCKED: GFX ring test | BLOCKED: host transport support | BLOCKED: no reference run recorded |
| RX 9070 16GB | BLOCKED: no GPU runtime proof | BLOCKED: no GPU runtime proof | BLOCKED: no GPU runtime proof | BLOCKED: host transport support | BLOCKED: no reference run recorded |
| Arc Pro B60 24GB | BLOCKED: xe 4K-page requirement | BLOCKED: xe 4K-page requirement | BLOCKED: xe 4K-page requirement | BLOCKED: host transport support | BLOCKED: no reference run recorded |
| RTX 5060 Ti 16GB | BUILT-UNTESTED: nouveau, shared 16K target | BUILT-UNTESTED: shared target, host config unverified | BUILT-UNTESTED: nouveau, shared 16K target | BLOCKED: no host-specific build or transport proof | BLOCKED: no reference run recorded |

Evidence cutoff: 2026-10-22. The shared NVIDIA build targets kernel `7.1.12-2-20261013.18-sep-ARCH`, source `6f63677751854d57bcfac172314957bc2197c05f`. It is not proof that a module was installed or loaded. AMD and Intel build details belong in their card guides; the matrix reports runtime readiness.

## Cards

| Card | Guide | First Linux route | Other recipes |
|---|---|---|---|
| ASRock Radeon RX 7600 Challenger 8GB OC | [RX 7600](cards/rx-7600/) | amdgpu + RADV + llama.cpp Vulkan | ROCm and runner constraints in guide |
| ASRock RX 9070 Challenger 16GB | [RX 9070](cards/rx-9070/) | amdgpu + RADV + llama.cpp Vulkan | ROCm and runner constraints in guide |
| Intel Arc Pro B60 | [Arc Pro B60](cards/arc-pro-b60/) | xe + ANV + llama.cpp Vulkan | Intel-specific runtime constraints in guide |
| NVIDIA RTX 5060 Ti 16GB | [RTX 5060 Ti](cards/rtx-5060-ti/) | nouveau + NVK for the Apple Silicon build | NVIDIA-open/CUDA reference path in guide |

MLX support on an integrated Apple GPU does not establish support for an external AMD, Intel, or NVIDIA card. Each guide states its limits. Retain the integrated GPU's driver and Vulkan ICD.

## Hosts and docks

[Host guides](hosts/) cover page size, kernel parameters, PCI apertures, and the M2 hot-plug bus-range failure. [Dock notes](docks/) cover the OwlTree ASM2464PD chain, Maskedfish MK-Q1L, Sonnet Breakaway Box 850 T5, and ACASIS TB501 Pro. A USB-C connector or a USB4 label alone does not prove PCIe tunneling.

The M1 Ultra Mac Studio is not a Linux host in this repo. No result from it counts as an Apple Silicon Linux eGPU result.

## Patches and measurements

Card guides identify carried patches and config fragments, their base revisions, and upstream status. No patch is described as upstream unless a public merge proves it. No firmware is bundled.

[Benchmarks](benchmarks/) contains the method and measured data. Attachment observations are separate from inference performance. Unknown power or link metadata remains unknown; it is never replaced with a vendor specification.

Our scripts and documentation use [MIT](LICENSE). Kernel and Mesa patches retain their own licenses; see [license boundaries](LICENSES.md).
