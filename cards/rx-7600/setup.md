# RX 7600 setup

Practical setup for the ASRock Radeon RX 7600 Challenger 8GB OC. Status and
identity live in [README.md](README.md). Nothing here is a performance claim.

## Hardware chain and power

Measured chain on 2026-10-22: host USB4 port, cable, OwlTree
M.2-to-PCIe x16 dock (ASMedia ASM2464PD, external ATX PSU), card in the x16
slot. The cable's certification and PSU model were not recorded. See [docks/](../../docks/) for power requirements.

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

## Card and host constraints (Apple Silicon)

Measured and source-read facts that decide what this card can do behind the
Apple PCIe tunnel:

- The tunnel **requires a 16 KiB-page kernel** (`CONFIG_PCIE_APPLE` depends on
  `PAGE_SIZE_16KB` in the kernel source). amdgpu GPU pages are 4 KiB and
  independent of the host page size (source read), so the driver is expected
  to be portable. Expected, not yet proven at runtime.
- Tunnel memory windows by SoC (device-tree source read): **2 GiB**
  64-bit prefetchable on base M1 and M2 parts; **8 GiB** on Pro/Max/Ultra and
  M3 parts. Every variant also has a 1 GiB 32-bit prefetchable window and
  roughly 1 GiB non-prefetchable.
- Resizable BAR: a full-VRAM BAR (8 GiB for this card) cannot map inside the
  2 GiB base-part window. Whether it can fit the 8 GiB Pro/Max window alongside
  the other consumers is untested; the measured run got the 256 MiB fallback
  BAR assigned and the small windows exhausted. Design for the 256 MiB BAR.
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

## Known issues (all measured 2026-10-22 unless noted)

1. **First hotplug clips the tunnel bus range.** The bridge stack trains one
   level per scan and the first pass leaves a bus-number conflict, so deeper
   devices are unusable:

   ```text
   pci_bus 0001:04: busn_res: can not insert [bus 04-03] under [bus 03]
   pci 0001:03:00.0: devices behind bridge are unusable because [bus 04] cannot be assigned for them
   ```

   The host-specific fix (remove the dock's upstream bridge, rescan its
   parent, repeat once per level) is documented with safety boundaries in the
   [M2 Max host guide](../../hosts/m2-max/README.md).

2. **Small BARs fail to assign while the large BARs succeed.** The 256 MiB
   BAR 0 and 2 MiB BAR 2 landed inside the 8 GiB prefetchable window; the
   small windows across five bridge levels did not:

   ```text
   pci 0001:05:00.0: BAR 0 [mem 0xc00000000-0xc0fffffff 64bit pref]: assigned
   pci 0001:05:00.0: BAR 2 [mem 0xc10000000-0xc101fffff 64bit pref]: assigned
   pci 0001:05:00.0: BAR 5 [mem size 0x00100000]: can't assign; no space
   pci 0001:05:00.0: BAR 4 [io  size 0x0100]: can't assign; no space
   pci 0001:05:00.0: ROM [mem size 0x00020000 pref]: can't assign; no space
   pci 0001:05:00.1: BAR 0 [mem size 0x00004000]: can't assign; no space
   ```

   Whether an incomplete small-BAR set blocks a driver bind is unknown; no
   driver run exists yet.

3. **The PCIe link inside the tunnel trained at its minimum.** The kernel
   reports the slowest link in the path, while the Thunderbolt layer reports
   40 Gb/s each way:

   ```text
   pci 0001:05:00.0: 2.000 Gb/s available PCIe bandwidth, limited by 2.5 GT/s PCIe x1 link at 0001:01:00.0 (capable of 126.024 Gb/s with 16.0 GT/s PCIe x8 link)
   ```

   Treat 2 Gb/s as the measured idle-state link, not a transport ceiling:
   re-read `LnkSta` under load before drawing bandwidth conclusions.

4. **No driver binds on the published kernel config.** Scoped fact: the
   `linux-aurora` 7.2.10-2 config has `CONFIG_DRM_AMDGPU` off (read
   2026-10-22). In logs the signature is silence: no `amdgpu` lines at all,
   no `Kernel driver in use`. It is a packaging state, not a card fault, and
   it can change with a future package.

5. **Firmware is missing until installed.** On our lab hosts
   `/usr/lib/firmware/amdgpu` did not exist (checked 2026-10-16). Expected log
   signature once a driver loads: `Direct firmware load for amdgpu/... failed`.

6. **Never hot-unplug.** A cable pull with the card still known to the kernel
   is a surprise removal; the kernel source comments that NVMe teardown
   through a dead aperture can wedge the SoC. Eject and power-down sequences
   live in the host guides.

The verbatim excerpts behind items 1 to 3, plus the full environment record,
are in [benchmarks/](../../benchmarks/2026-10-22-rx7600-14in-m2max-transport.md).
