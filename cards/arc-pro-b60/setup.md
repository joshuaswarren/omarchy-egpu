# ASRock Intel Arc Pro B60 Creator 24GB on Omarchy

Battlemage (BMG-G21), 24 GB GDDR6, PCIe 5.0 x8, up to 200 W board power
([Intel press deck](https://download.intel.com/newsroom/2025/client-computing/Intel-Arc-Pro-B-Series-Press-Deck.pdf)).
PCI ID: vendor `8086`; Battlemage G21 device IDs include
`E202 E209 E20B E20C E20D E210 E211 E212 E216` (Linux kernel `pciids.h`).
Our board's exact device and subsystem ID has not been read off the card yet.
Read `lspci -nn` on first attach and do not substitute a guessed ID: Intel's
Thunderbolt bridges are also vendor `8086`, so the vendor alone never identifies
the GPU.

Common host setup, aperture checks and removal rules live in
[hosts/apple-silicon/](../../hosts/apple-silicon/) and
[docks/](../../docks/). This page covers only what is specific to this card.

## Status (updated 2026-10-23)

| Host | Status | What is proven |
|---|---|---|
| x86 Omarchy desktop | **BLOCKED** (no recorded reference run) | The stock `xe` path is what x86 uses; we have run nothing on our own x86 hardware with this card |
| 13-inch M1 MacBook Pro | **BLOCKED** (16K xe kernel not built or shipped) | Nothing. No attach, no bind, no firmware boot, no compute |
| 14-inch M2 Max MacBook Pro | **BLOCKED** (same kernel gate) | Same |
| 16-inch M1 Max MacBook Pro | **MEASURED** (local patches, not upstream) | xe loads, ANV enumerates the card and llama.cpp Vulkan runs on it; hot-plug untested. See the [benchmark record](../../benchmarks/2026-10-23-b60-m1max-llamacpp-vulkan.md) |
| M6 Mac mini | **BLOCKED** (no recorded reference run; Thunderbolt host support for this machine is still in progress) | No M6-specific build or run of any kind |

Two supporting facts, kept apart from the card itself:

- **MEASURED on the 16-inch M1 Max.** The four-patch 16 KiB series builds and loads there. The measured run also needs local patches 0005 to 0014 (non-posted BAR mappings and buffer placement) and a local Apple PCIe change, none of them published. The shared kernel package does not carry any of this. See [patches.md](patches.md).
- **MEASURED elsewhere, not on this card.** A dock's bridges and its USB and
  network endpoints enumerate over the PCIe tunnel on the 13-inch M1 under
  aurora. Transport enumeration is not a GPU run.

One host has a benchmark record: the 16-inch M1 Max, in the [benchmark record](../../benchmarks/2026-10-23-b60-m1max-llamacpp-vulkan.md). Nothing else on this page is a performance claim.

## Power

The board draws up to 200 W. Size the enclosure supply above that with
headroom, connect every power connector the card label shows, and follow the
dock and enclosure rules in [docks/](../../docks/): PSU on before the cable goes
into the host, one tunnel device at a time during a card test, and never swap a
card with the PSU on.

## x86 setup (the stock path)

Ordinary Intel stack. Nothing in this repo changes it.

1. Host firmware: enable Above-4G decoding and Resizable BAR. The B60 exposes
   its full 32 GB VRAM as BAR0, and Intel Arc desktop cards are documented to
   fail initialization when the aperture is too small. A 32 GB BAR fits
   comfortably on any x86 root complex.
2. Install the stack:

```bash
pacman -S --needed linux-firmware-intel vulkan-intel vulkan-tools \
  intel-compute-runtime level-zero-loader intel-media-driver
```

3. Card visible and bound:

```bash
lspci -nn | grep -iE 'VGA|3D'      # expect 8086:xxxx, class 03
lspci -k | grep -A3 -i intel        # "Kernel driver in use: xe"
modinfo -F version xe 2>/dev/null || echo "xe module missing"
```

4. Firmware and Vulkan. `xe/bmg_guc_70.bin` is required for compute and
   `xe/bmg_huc.bin` is optional media firmware. The BMG table in the driver has
   no GSC host blob and requests none, so there is no mandatory `bmg_gsc.bin`
   to look for.

```bash
ls /usr/lib/firmware/xe/           # expect bmg_guc_70.bin and bmg_huc.bin
vulkaninfo --summary               # expect the Intel device under ANV
```

Level Zero and the compute runtime are needed for anything that is not
llama.cpp; both are in the package line above.

Known x86 wrinkle: community reports exist of this board downtraining its PCIe
link to Gen1 x1 under `xe` on some systems. If bandwidth looks wrong, compare
`LnkSta` in `lspci -vv` against the slot capability before blaming the card.

## Apple Silicon path

This section was written before the 2026-10-23 measured run on the 16-inch M1 Max and is kept as the map of what had to be true. Measured since, on that host: a local kernel with xe was built and booted (blocker 1); BAR0 is 16 MiB of registers and BAR2 is 256 MiB of VRAM (blocker 2); the 32 GiB resize cannot fit, and the run works with `xe.vram_bar_size=-1` and the 256 MiB window (blocker 3); VRAM BAR mappings must be non-posted, and CPU stores into them took an arm64 alignment fault until CPU-written buffers moved to system memory (blocker 4). Blockers 5 and 6 were not isolated. Details: the [required workarounds](../../benchmarks/2026-10-23-b60-m1max-llamacpp-vulkan.md#required-workarounds-measured).

### The 16K page constraint is the whole problem

The laptops run aurora at a mandatory 16 KiB host page size: the platform PCI
controller that provides the Thunderbolt tunnels is only built for 16K-page
kernels, and the tunnel DART granules are fixed at 16 KiB. Upstream `xe` refuses
to build there:

```text
drivers/gpu/drm/xe/Kconfig:  depends on PAGE_SIZE_4KB || COMPILE_TEST || BROKEN
```

Our [patch series](patches.md) fixes the page-unit mismatches and permits the
build. It compiles to object files. Nothing beyond that is proven, and the
[host guide](../../hosts/apple-silicon/) already explains why switching to 4K
pages is not a workaround: the platform PCI controller and internal storage
depend on the supported configuration.

### Blockers, in order

1. **Shared kernel.** A 16K aurora kernel with `xe`, TTM, buddy, GPUSVM and
   HMM enabled is not yet built, packaged or promoted, so there is no module to
   load. Build and install a complete kernel package through the normal
   installer chain (m1n1-aurora, U-Boot, then Limine with a UKI); an initramfs
   change only takes effect after `limine-update`.
2. **B60 BAR2 is unknown.** The card's shipped local-memory BAR size and its
   resizable-BAR mask are firmware properties read off the card with
   `lspci -vv`. No source tree contains them.
3. **The full aperture cannot fit.** The 64-bit prefetchable window behind the
   tunnel is 2 GiB on the 13-inch M1 and 8 GiB on the 14-inch M2 Max and
   16-inch M1 Max (source-defined apertures, not measured free space; see
   [hosts/apple-silicon/](../../hosts/apple-silicon/)). Neither a 24 GB VRAM
   aperture nor the 32 GB BAR0 can map. `xe` models small-BAR operation
   explicitly and its BAR resize is best-effort: nothing in the probe path
   requires the resize to succeed. Whether this card probes and computes in
   small-BAR mode is untested. `xe.vram_bar_size=-1` skips the resize attempt
   if you need that for diagnosis.
4. **MMIO attributes.** `xe` maps the local-memory BAR unconditionally
   write-combining. T602x-family fabrics are documented to fault on that
   mapping type while the T8103 fabric tolerates it. First contact on an
   M2-class host must watch for a synchronous external abort on the first
   aperture write. This is a source-derived risk, not a measurement.
5. **DMA coherency.** The tunnel devices are non-coherent per the device tree,
   while `xe` assumes coherent system memory: its system-memory maps pass
   `DMA_ATTR_SKIP_CPU_SYNC`, and dGPU system memory is forced write-back on the
   assumption of CPU coherence. If this bites it looks like load-dependent
   corruption or GuC boot hangs, not a clean probe failure. Unresolved; review
   rejected two incomplete fixes for exactly this reason (see
   [patches.md](patches.md)).
6. **IOVA window, source-derived and unmeasured.** Device DMA is clamped to the
   tunnel aperture: `[0, 4 GiB)` on the 13-inch M1 and the upper half of the
   32-bit bus (a 2 GiB window) on the 14-inch M2 Max. On that reading a single
   system-memory buffer larger than the window cannot map. Nobody has measured
   it, so treat the per-allocation ceiling as a hypothesis to test, not a
   known limit, and do not quote it as a KV cache figure.

### What you would run (conditional)

Only after the shared kernel is installed and the card enumerates:

```bash
getconf PAGESIZE                        # 16384, you are on the 16K kernel
modinfo xe | grep -E 'filename|vermagic'
ls /usr/lib/firmware/xe/                # bmg_guc_70.bin must be present
sudo modprobe xe
dmesg | grep -iE 'xe|guc|bar|firmware'  # read this before anything else
```

## Known failure signatures

Classes, not diagnoses. Copy the first verbatim failing line and stop. Removal
and shutdown rules are in the host guides; do not script a vendor-wide function
select, and do not loop removal over every display-class device, because those
sets include the integrated GPU and the Thunderbolt bridges.

| Signature | What it means | Do |
|---|---|---|
| No Intel display-class device appears | Power, cable, authorization or tunnel enumeration | Compare `lspci -tv` and `boltctl list`; a missing card is not a driver failure |
| `can't assign`, `failed to assign`, unassigned BAR | A bridge window could not fit | Compare every parent bridge window with the card's actual BARs |
| `Direct firmware load for xe/bmg_guc_70.bin failed` | The exact required file is absent | Fix the `linux-firmware-intel` package; do not guess another blob |
| `Small BAR device` in the log | xe's CPU-visible VRAM window is smaller than the card's VRAM | Expected behind a tunnel; record both sizes. The message alone is not a failure |
| GuC boot or command-transmission timeout, garbage in the GuC log | Coherency, firmware boot or page mapping | Save the full log with kernel and module identity |
| DART or IOMMU fault | Address range, granule or non-coherent DMA | Record the fault address and IOMMU group, then stop |
| `SError`, external abort, oops, panic, host stops answering | Unsafe MMIO or a tunnel wedge | Hard stop. Shut the host down with the card attached and powered; never pull a live cable |

## Firmware

GPU firmware comes from the distribution `linux-firmware-intel` package, which
carries both BMG blobs. Intel's xe blobs carry their own redistribution terms
(the `LICENSE.xe` file upstream in linux-firmware: unmodified redistribution
with the notice, no endorsement claims). This repository vendors no firmware;
see [LICENSES.md](../../LICENSES.md).