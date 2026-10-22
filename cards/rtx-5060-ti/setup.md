# NVIDIA GeForce RTX 5060 Ti 16GB on Omarchy

Blackwell (GB206), 16 GB, PCI ID `10de:2d04`. Our card is the PNY GeForce
RTX 5060 Ti 16GB. Power, cable order, enclosure selection and removal rules
live in [docks/](../../docks/) and [hosts/apple-silicon/](../../hosts/);
this page covers only what is specific to this card.

Two driver routes exist. **nouveau with NVK** is the only one with a package
path for aarch64, so it is the primary route on the laptops. The **NVIDIA open
kernel modules** are the normal x86 route and the only route to CUDA.

## Status (2026-10-22)

| Host | Status | What is proven |
|---|---|---|
| x86 Omarchy desktop | **BLOCKED** (no recorded reference run) | Both routes are stock distribution paths; we have run neither on our own x86 hardware with this card |
| 13-inch M1 MacBook Pro | nouveau route **BUILT-UNTESTED** / overall **BLOCKED** | nouveau and its helpers compiled, linked and passed modpost for the 16K arm64 kernel with no source patches. No install, no load, no attach, no GSP boot, no NVK run. The NVIDIA-open route is blocked at userspace (below) |
| 14-inch M2 Max MacBook Pro | Same | Same |
| 16-inch M1 Max MacBook Pro | Same | Same |
| M6 Mac mini | **BLOCKED** (no recorded reference run; Thunderbolt host support for this machine is still in progress) | No M6-specific build or run of any kind |

What "built" means here, precisely: a compiler and linker ran on a build host.
That is not a GPU run. Across every host and enclosure, nothing has been
attached, loaded, bound or executed with this card, and no benchmark of any
kind exists. See [patches.md](patches.md) for the per-route status and
[ai.md](ai.md) for what each model runner can and cannot use.

## Route 1: nouveau with NVK

The kernel's nouveau driver already knows this chip. It identifies GB206 from
the GPU's BOOT0 register rather than matching a wildcard, and its firmware
interface for Blackwell is pinned to GSP-RM **570.144**. **No kernel source
patch is required**, only a config fragment:

```text
CONFIG_DRM_NOUVEAU=m
CONFIG_DRM_TTM=m
CONFIG_DRM_TTM_HELPER=m
```

Firmware comes from the distribution `linux-firmware-nvidia` package together
with `linux-firmware-whence`. The driver requests exactly three files and the
package ships all three through its preserved symlinks
(`nvidia/gb206 -> gb202`):

```text
nvidia/gb206/gsp/fmc-570.144.bin
nvidia/gb206/gsp/bootloader-570.144.bin
nvidia/gb206/gsp/gsp-570.144.bin
```

Do not substitute 615-series GSP images here: this kernel's GB20x firmware
interface is pinned to 570.144 and `linux-firmware` carries no 615.x GSP at
all. A nouveau system and an NVIDIA-open system need two different firmware
sets, so pick one route per card.

Userspace is Mesa's NVK Vulkan driver (`vulkan-nouveau`, which ships for
aarch64). NVK has been Vulkan 1.4 conformant on the RTX 50 series since Mesa
25.2. Keep the integrated GPU's ICD (honeykrisp) installed, and select the NVK
ICD explicitly when probing the eGPU.

### x86

```bash
pacman -S --needed linux-firmware-nvidia mesa vulkan-nouveau vulkan-tools
sudo modprobe nouveau
vulkaninfo --summary      # expect the NVIDIA device under NVK
```

### Apple Silicon (conditional, unverified)

Only after the shared 16K kernel ships:

```bash
getconf PAGESIZE                              # 16384
modinfo nouveau | grep -E 'filename|vermagic'
ls /usr/lib/firmware/nvidia/gb206/gsp/        # must list the three 570.144 files
sudo modprobe nouveau
VK_DRIVER_FILES=/usr/share/vulkan/icd.d/nouveau_icd.json timeout 90 vulkaninfo --summary
```

Success means this card appears in the actual `vulkaninfo` output with clean
kernel logs. A source match, a compiled module or a firmware hash proves
nothing about a bind.

## Route 2: NVIDIA open kernel modules (CUDA on x86)

Blackwell requires the open kernel modules: NVIDIA's legacy proprietary
kernel-module flavor does not support this generation. The proprietary driver
for this card therefore means the open kernel modules plus the closed
user-space stack (`nvidia-utils`, CUDA), which is what the normal Arch packages
provide:

```bash
pacman -S --needed nvidia-open-dkms nvidia-utils
nvidia-smi
nvidia-smi -q | grep -i "GSP Firmware"     # expect the installed release version
```

GSP firmware ships inside the driver package for this route (installed under
`/lib/firmware/nvidia/<version>/`), not from `linux-firmware`. Blackwell
requires GSP firmware to boot: never disable it as a recovery shortcut.

On the laptops this route is **blocked at userspace**. The kernel modules build
unpatched for the 16K arm64 target, but no version-matched aarch64 driver
installer could be found (the checked installer URLs return 404). Building
kernel modules for a userspace that does not exist is not a path. **There is no
CUDA on these laptops with this card.**

## Apple Silicon constraints (both routes)

From the aurora kernel and this card's BAR sizes, none of it exercised with a
GPU. Aperture sizes are source-defined, not measured free space; see
[hosts/apple-silicon/](../../hosts/apple-silicon/).

- **Prefetch window.** The 64-bit prefetchable window behind the tunnel is
  2 GiB on the 13-inch M1 and 8 GiB on the 14-inch M2 Max and 16-inch M1 Max. A
  16 GiB resizable-BAR aperture fits none of them, and none is needed: nouveau
  makes no full-VRAM aperture demand, and the NVIDIA driver resizes best-effort,
  stepping down on failure and refusing when host firmware forbids moving
  windows. Do not force full-VRAM ReBAR.
- **Firmware identity.** Route 1 wants 570.144 from `linux-firmware`; Route 2
  wants its own release's images from the driver package. A
  `Direct firmware load ... failed with error -2` line means the exact requested
  file is absent: check the `ls` above before anything else.
- **Coherency.** The tunnel is non-coherent per the device tree. The NVIDIA
  driver performs explicit cache maintenance on arm64, so it is built for the
  problem. That is a source-reading fact, not a run.
- **Known upstream defect, unmeasured here.**
  [open-gpu-kernel-modules #1269](https://github.com/NVIDIA/open-gpu-kernel-modules/issues/1269),
  open as of 2026-10-22: on ARM64 kernels with pages larger than 4 KiB, the
  system-memory DMA submap size is not 2 MiB-aligned, so mappings of 4 GiB and
  above take unusable pages just below each 4 GiB boundary (Xid 31,
  FAULT_PTE). Reproduced upstream on 64K-page hosts, and the guard is still
  present in 615.78.08. On a 16K kernel the same code path is arithmetically
  exposed; nobody has measured it on these hosts. If you push large host-memory
  allocations through this card, that is where to look first.
- **Driver contention.** One route per card, with the other module blacklisted.
  Both match NVIDIA display-class devices.

## Known failure signatures

Classes, not diagnoses. Copy the first verbatim failing line and stop. Removal
and shutdown rules are in the host guides; do not script a vendor-wide function
select, and do not loop removal over every display-class device, because those
sets include the integrated GPU and the Thunderbolt bridges.

| Signature | What it means | Do |
|---|---|---|
| No NVIDIA endpoint after attach | Tunnel, authorization, link or power | Compare Thunderbolt devices and bridges before and after; use a known-good PCIe endpoint as the positive control |
| `BAR ... no space`, `can't assign`, `failed to assign` | A bridge window cannot fit a BAR | Record endpoint BARs and every parent window; do not force a 16 GiB BAR |
| `Direct firmware load ... failed ... -2` | The exact requested firmware is absent | Compare the requested path against the lists above |
| GSP or RM boot timeout, `RmInitAdapter` | Firmware, MMIO or DMA failure | Preserve the preceding BAR and DART lines and the full error. Never disable GSP |
| `nouveau ... unknown chipset` | Kernel and chip dispatch mismatch, or unreadable BOOT0 | Confirm the running kernel and PCI ID |
| Xid 31, DART or IOMMU fault | DMA aperture, mapping or coherency | Record the IOVA and the DMA masks, then stop repeated probes |
| `SError`, oops, panic, repeated link flap, lost SSH | SoC, MMIO or tunnel failure | Hard stop. Shut the host down with the card attached and powered; never pull a live cable |

## Firmware

Install GPU firmware through the official packages named above; this repository
vendors none. See [LICENSES.md](../../LICENSES.md).