# RX 7600 setup

Practical setup for the ASRock Radeon RX 7600 Challenger 8GB OC. Status and
identity live in [README.md](README.md). Nothing here is a performance claim.

The latest M2 Max result is a **working Vulkan inference run**, reached with local driver patches and one device-tree change; both remain unpublished. See the [current host result](../../hosts/m2-max/README.md) and the [benchmark record](../../benchmarks/2026-10-22-rx7600-m2max-llamacpp-vulkan.md). A stock system does not reproduce it yet.

## Hardware chain and power

The measured driver-probe chain on 2026-10-22 uses the host USB4 port,
OwlTree dock, Rosewill ASM2464PD USB4 enclosure, and this card.
The cable's certification and PSU model were not recorded. See [docks/](../../docks/) for power requirements.

Power rules:

1. Connect every power connector on the card label: one 8-pin for this card,
   plus the 24-pin ATX lead to the dock.
2. Switch the PSU on before the cable goes into the host.
3. One tunnel device at a time while testing.
4. Attach, eject, and unplug procedures are host-specific. Use the host guide
   ([14-inch M2 Max](../../hosts/m2-max/README.md), [other hosts](../../hosts/));
   it carries the exact observed topology and the safety boundaries. Do not
   improvise a remove-and-rescan loop from a card page.

## Packages

On Apple Silicon hosts (aarch64, 16 KiB-page kernel):

```bash
# firmware for the card (absent on our lab hosts, checked 2026-10-16)
sudo pacman -S linux-firmware-amdgpu linux-firmware-whence
# userspace Vulkan stack
sudo pacman -S vulkan-radeon vulkan-icd-loader vulkan-tools
# diagnostics
sudo pacman -S pciutils bolt
```

`vulkan-radeon` 26.2.5-1 and `linux-firmware-amdgpu` 20260916-1 exist for
aarch64 in Arch Linux ARM (checked 2026-10-22).

**Driver:** the published Omarchy kernel package `linux-aurora` 7.2.10-2 sets
`# CONFIG_DRM_AMDGPU is not set` in its config
([omacom/omarchy-pkgs](https://github.com/omacom/omarchy-pkgs/blob/master/pkgbuilds/linux-aurora/config),
read 2026-10-22). A host running that revision enumerates the card but cannot
bind a driver. Current driver status is in [patches.md](patches.md).

On x86 Omarchy the kernel already carries amdgpu; the firmware and Vulkan
package lines are the same.

## Decode environment setting (Apple Silicon eGPU hosts)

Once the driver is running, export this before any llama.cpp Vulkan run:

```bash
export RADV_PERFTEST=nogttspill,dmashaders
export GGML_VK_ALLOW_GRAPHICS_QUEUE=1
```

Measured on the 14-inch M2 Max: decode +32 percent (fa0) and +22.5 percent (fa1) on Llama-2-7B Q4_0, prompt processing unchanged (see the [benchmark record](../../benchmarks/2026-10-22-rx7600-m2max-llamacpp-vulkan.md)). The buffer placement behind it is now measured: with the default, the 256 KiB buffer that matches RADV's shader arena is in system memory (`GTT CPU_ACCESS_REQUIRED`); with `dmashaders` it is in VRAM. Window l re-measured the gain at +26 to +30 percent (fa0) and +20 to +22 percent (fa1) in an alternating test (see the [benchmark record](../../benchmarks/2026-10-22-rx7600-m2max-llamacpp-vulkan.md)). Why that costs decode (instruction fetch across the tunnel) is inferred, not isolated.

## Card and host constraints (Apple Silicon)

Measured and source-read facts that decide what this card can do behind the
Apple PCIe tunnel:

- The tunnel **requires a 16 KiB-page kernel** (`CONFIG_PCIE_APPLE` depends on
  `PAGE_SIZE_16KB` in the kernel source). amdgpu GPU pages are 4 KiB and
  independent of the host page size. A locally patched driver now initializes every
  ring and runs llama.cpp Vulkan on the 14-inch M2 Max. This is not an unmodified-driver portability result.
- Tunnel memory windows by SoC (device-tree source read): **2 GiB**
  64-bit prefetchable on base M1 and M2 parts; **8 GiB** on Pro/Max/Ultra and
  M3 parts. Every variant also has a 1 GiB 32-bit prefetchable window and
  roughly 1 GiB non-prefetchable.
- Resizable BAR: a full-VRAM BAR (8 GiB for this card) cannot map inside the
  2 GiB base-part window. Whether it can fit the 8 GiB Pro/Max window alongside
  the other consumers is untested. The driver requested 8 GiB in later probes,
  then continued with the restored 256 MiB BAR after resizing failed.
- BAR mapping type is SoC-specific in the kernel source. Base M1 uses posted
  mappings; a non-posted mapping there risks an SError. M2 Max requires
  non-posted mappings. Stop at an SError or unhandled fault; retain the powered
  card and logs while recovering the host.
- Tunnel PCIe-C nodes carry no `dma-coherent` (source read). DMA cost is
  unmeasured.
- The tunnel transport itself ships in the published kernel config
  (`CONFIG_USB4_APPLE_SOC=m`, `CONFIG_PCIE_APPLE=y`), which is why enumeration
  works on a driverless kernel.

## Read-only inspection

Inspect the powered device and its parent bridges:

```bash
lspci -Dtv                              # full tree with domains
lspci -nn -d 1002:                      # AMD devices and IDs
lspci -k -d 1002:                       # bound driver, if any
lspci -vv -s <bdf> | grep -E 'LnkCap|LnkSta|Region|Resizable|BAR'
sudo grep -iE 'amdgpu|0001:0[1-9]:' /proc/iomem   # window usage (domain may differ)
boltctl list                            # tunnel authorization and speed
sudo dmesg | grep -iE 'amdgpu|bar |no space|busn_res|serror|pcie-apple|thunderbolt|usb4|firmware'
```

With a driver bound, `vulkaninfo --summary` must list the Radeon as a device.
A software renderer or the integrated Apple GPU does not qualify.

## Known issues

1. **Stock BAR reads fail; the working run needed a device-tree fix.** Normal boots assign BAR0, BAR2, BAR5 and audio without a rescan. Before the fix, every CPU read of the 64-bit BAR0/BAR2 window returned all-ones while BAR5 worked. Changing the tunnel node's `ranges` entry to an identity mapping made the window work.
2. **Device-memory access needs care.** Tunnel BARs map as Device-nGnRnE. Ordinary `memset`, wide or unaligned stores, and struct copies took alignment faults. Mapping the BAR Normal-NC instead hung the host; do not use that as a workaround.
3. **Userspace mappings can fault.** A Vulkan driver `memcpy` into a VRAM buffer hit SIGBUS until a local change moved faulting buffers to system memory. That change is unpublished.
4. **GFX now initializes after the window fix.** All rings register, RADV enumerates the card, and llama.cpp runs. Hot-plug, the 8 GiB BAR resize, and a display run remain untested.
5. **Firmware and driver packages remain separate prerequisites.** Firmware alone cannot add amdgpu to a kernel built without it. The local test build is not a released package.

The [host guide](../../hosts/m2-max/README.md) contains the measured stages, the decisive device-tree window fix, diagnostic output, and the historical rescan safety notes.
