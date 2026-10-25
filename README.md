# omarchy-egpu

Set up an external GPU on Omarchy Linux, check each layer, and run local
inference when the card is ready. Covers AMD RX 7600 and RX 9070, Intel Arc
Pro B60, and NVIDIA RTX 5060 Ti on x86 and Apple Silicon Linux hosts, with
[measured benchmark data](benchmarks/).

Linux boots directly on the Mac (no virtual machine): the m1n1 boot chain, and
the USB4 tunnel to the card handled by the Linux Apple PCIe driver. Status as
of 2026-10-23:

- **RX 7600**: runs local inference on a 14-inch M2 Max. llama.cpp on Vulkan
  keeps 86 percent of native prompt processing and about 66 percent of native
  decode over USB4 with the driver tuning in its [card guide](cards/rx-7600/).
  Requires unpublished kernel and device-tree changes; not yet reproducible on
  a stock system. Hot-plug is untested (the card was attached at boot).
- **Arc Pro B60**: runs llama.cpp on Vulkan on a 16-inch M1 Max with local
  `xe` and ANV patches. Qwen3.8-27B Q4_0 (unsloth) runs fully on the card
  (66 of 66 layers) at pp512 428.04 / tg128 17.28 t/s. See its
  [card guide](cards/arc-pro-b60/).
- **RTX 5060 Ti**: runs via NVIDIA open modules 595.112.07 with the 16K-page
  fix, CUDA and Vulkan, on the 16-inch M1 Max. The nouveau route has no
  runtime run yet. See its [card guide](cards/rtx-5060-ti/).
- **RX 9070**: no runtime run yet; see its [card guide](cards/rx-9070/).

## Requirements

- A host that can drive the card: check the [host guides](hosts/) first
  (page size, kernel parameters, PCI apertures). The M1 Ultra Mac Studio is
  not a supported Linux host in this repo.
- A dock with real PCIe tunneling and enough power: check
  [dock, power, and cable requirements](docks/). A USB-C connector or a USB4
  label alone does not prove PCIe tunneling. Power the dock and card before
  connecting the host cable.

## Quick start

1. Check the [status matrix](#status) before changing packages or boot
   settings.
2. Run the read-only diagnostic from a terminal:

   ```bash
   git clone https://github.com/joshuaswarren/omarchy-egpu.git
   cd omarchy-egpu
   python3 scripts/egpu_doctor.py --help
   python3 scripts/egpu_doctor.py
   ```

3. Confirm that the external card has assigned memory BARs, a bound driver,
   and a matching hardware Vulkan device. A software renderer or the
   integrated GPU does not qualify.
4. Use your card's inference recipe, then record the exact model, command,
   versions, and result with the [benchmark method](benchmarks/).

The helper never installs packages, authorizes devices, rescans a bus, or
changes a boot entry. See [its options and exit codes](scripts/).

## Status

This matrix separates evidence stages. `MEASURED` names an actual runtime
observation. `BUILT-UNTESTED` means a driver compiled for the shared target
but no card runtime proof. `BLOCKED` names the missing prerequisite or
observed failure. An untested cell does not mean the hardware cannot work.

| Card | 13-inch M1 MacBook Pro | 16-inch M1 Max MacBook Pro | 14-inch M2 Max MacBook Pro | M6 Mac mini | x86 Omarchy |
|---|---|---|---|---|---|
| RX 7600 8GB | BLOCKED: no GPU runtime proof | BLOCKED: no GPU runtime proof | MEASURED: amdgpu loads with all rings; llama.cpp Vulkan runs (Qwen2.5-7B Q4_K_M pp512 945.8-967.6, tg128 28.9-31.9 t/s across boots; Llama-2-7B Q4_0 tg128 38.0-38.2 with the `dmashaders` setting); needs local device-tree and kernel changes; hot-plug untested | BLOCKED: host transport support | BLOCKED: no reference run recorded |
| RX 9070 16GB | BLOCKED: no GPU runtime proof | BLOCKED: no GPU runtime proof | BLOCKED: no GPU runtime proof | BLOCKED: host transport support | BLOCKED: no reference run recorded |
| Arc Pro B60 24GB | BLOCKED: xe 4K-page requirement | MEASURED: llama.cpp Vulkan runs on a 10-CPU boot; Qwen3.8-27B runs fully on the card (66 of 66 layers) at pp512 428.04 / tg128 17.28 t/s; numbers, quant variants, and the required local xe patches are in the [B60 record](benchmarks/2026-10-23-b60-m1max-llamacpp-vulkan.md) and [card guide](cards/arc-pro-b60/); hot-plug untested | BLOCKED: no GPU runtime proof | BLOCKED: host transport support | BLOCKED: no reference run recorded |
| RTX 5060 Ti 16GB | not run on this host | MEASURED: NVIDIA open 595.112.07 loads (16K fix), CUDA and Vulkan run; Gemma-4-12B tg128 44.88 Vulkan / 49.83 CUDA; Qwen3.8-27B 22.52 Vulkan / 24.63 CUDA | not run on this host | not run on this host | not run on this host |

The RTX 5060 Ti rows come from the NVIDIA-open route; the nouveau route has no
runtime run. Both RTX 5060 Ti 16K fixes are submitted upstream, not merged:
[PR #1480](https://github.com/NVIDIA/open-gpu-kernel-modules/pull/1480) (page
size, hardware-proven) and
[PR #1481](https://github.com/NVIDIA/open-gpu-kernel-modules/pull/1481)
(submap alignment, source-derived). AMD and Intel build details belong in
their card guides; the matrix reports runtime readiness.

## Limits

- Nothing here is reproducible on a stock Omarchy install yet. Each measured
  run depends on the local patches listed in its card guide; no patch is
  described as upstream unless a public merge proves it.
- Hot-plug is untested everywhere; every measured run attached the card at
  boot.
- MLX support on an integrated Apple GPU does not establish support for an
  external AMD, Intel, or NVIDIA card. Retain the integrated GPU's driver and
  Vulkan ICD.
- The [matched macOS Metal baseline](benchmarks/method.md) has not been run.
  Comparisons in this repo are Linux-to-Linux unless stated otherwise.
- Unknown power or link metadata stays unknown; it is never replaced with a
  vendor specification.

## Cards

| Card | Guide | First Linux route | Other recipes |
|---|---|---|---|
| ASRock Radeon RX 7600 Challenger 8GB OC | [RX 7600](cards/rx-7600/) | amdgpu + RADV + llama.cpp Vulkan | ROCm and runner constraints in guide |
| ASRock RX 9070 Challenger 16GB | [RX 9070](cards/rx-9070/) | amdgpu + RADV + llama.cpp Vulkan | ROCm and runner constraints in guide |
| Intel Arc Pro B60 | [Arc Pro B60](cards/arc-pro-b60/) | xe + ANV + llama.cpp Vulkan | Intel-specific runtime constraints in guide |
| NVIDIA RTX 5060 Ti 16GB | [RTX 5060 Ti](cards/rtx-5060-ti/) | NVIDIA open modules + CUDA/Vulkan (measured route) | nouveau + NVK build documented, no runtime run yet |

Each guide states its limits, carried patches, base revisions, and upstream
status.

## Hosts and docks

[Host guides](hosts/) cover page size, kernel parameters, PCI apertures, and
the M2 hot-plug bus-range failure. [Dock notes](docks/) cover the
OwlTree/Rosewill chain, Maskedfish MK-Q1L, Sonnet Breakaway Box 850 T5, ACASIS
TB501 Pro, and ADT-Link UT3G.

## FAQ

### How is this different from tinygrad's TinyGPU?

TinyGPU is a macOS app that installs a driver extension. Its
[documentation](https://github.com/tinygrad/tinygrad/blob/master/docs/tinygpu.md)
says it lets tinygrad use AMD RDNA3 and newer and NVIDIA Ampere and newer
cards over USB4 on macOS. This project boots Linux on the Mac and uses the
kernel's own `amdgpu` and `xe` drivers with Mesa Vulkan, so any Vulkan program
can use the card. We have not run TinyGPU and make no speed comparison with
it.

### Does the whole model sit on the card?

In our runs, yes. The Qwen3.8-27B Q4_0 run reported `offloaded 66/66 layers to
GPU` with a 14367.22 MiB model buffer on the card, and free card memory fell
from 21573 MiB to 8021 MiB. One small table of 682.03 MiB stays in host memory
because llama.cpp keeps the token embeddings there. No layers were split
between the card and the Mac's unified memory. See the [B60
record](benchmarks/2026-10-23-b60-m1max-llamacpp-vulkan.md#qwen38-27b-fully-on-the-card-2026-10-23).

### How fast is the card against the Mac's own GPU?

On Linux, the RX 7600 was 3.5 to 4.1 times faster than the M2 Max's built-in
GPU at prompt processing and tied on decode; the Arc Pro B60 was 5.7 to 7.4
times faster than the M1 Max's built-in GPU at prompt processing and 1.9 to
2.1 times faster at decode. These are Linux-to-Linux results, not a matched
comparison with macOS Metal. The full tables and unmatched published Metal
reference values are in
[benchmarks/method.md](benchmarks/method.md#card-vs-built-in-gpu-on-linux-2026-10-23-runs).

## Patches and measurements

[Benchmarks](benchmarks/) contains the method and all measured records. Our
scripts and documentation use [MIT](LICENSE). Kernel and Mesa patches retain
their own licenses; see [license boundaries](LICENSES.md).
