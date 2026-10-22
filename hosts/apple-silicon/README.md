# Apple Silicon Linux hosts

Use an existing Omarchy installation from the Omarchy MX Mac Installer. These notes cover the 13-inch M1, 16-inch M1 Max, and 14-inch M2 Max MacBook Pro. The M1 Ultra Mac Studio is not a Linux target here.

The tested kernel target uses 16 KiB host pages. Do not switch to a 4 KiB kernel to bypass a GPU driver constraint: the platform PCI controller and internal storage depend on the supported platform configuration.

## Check the boot and driver pair

```bash
uname -r
getconf PAGESIZE
cat /proc/cmdline
modinfo amdgpu
modinfo nouveau
```

A missing module or mismatched vermagic blocks a runtime test. Do not force-load it. Build and install a complete kernel package for your host, retaining a known-good boot entry. A module build against one shared configuration does not qualify every host configuration.

The boot chain is m1n1-aurora, U-Boot, then Limine with a UKI. An initramfs change takes effect only after `limine-update` rebuilds that UKI. This repo does not replace the installer, distribute boot firmware, or automate kernel installation.

## PCI apertures and DMA

The inspected platform device trees define a 2 GiB 64-bit prefetchable window on the base M1, and an 8 GiB window on M1 Max and M2 Max. These are source-defined aperture sizes, not measured free space on every port. Existing devices and bridge windows can reduce usable space.

Do not force a full-VRAM resizable BAR. A 16 GiB card cannot fit a 16 GiB BAR in an 8 GiB aperture. VRAM capacity and CPU-visible aperture size are different limits.

Check the full parent chain, not only the GPU:

```bash
lspci -Dtv
sudo lspci -Dnnvvk
journalctl -k -b --no-pager
```

Stop at BAR allocation errors, DART faults, MMIO faults, or driver initialization failure. Authorization proves access to the dock; it does not prove DMA or Vulkan support. See the [M2 Max failure and recovery notes](../m2-max/) before any manual rescan.

## Kernel parameters

No additional kernel parameter is validated here as an eGPU fix. Keep the baseline command line. In particular, `pci=realloc` cannot create physical address space beyond the platform's device-tree aperture. Never disable IOMMU protection to hide an unresolved DMA fault.
