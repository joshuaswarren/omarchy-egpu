# x86 Omarchy reference setup

This is a reference procedure, not a measured x86 result from this project. Use an x86-64 host whose Thunderbolt or USB4 implementation supports PCIe tunneling.

## Prepare the host

1. Update the host through its normal Omarchy update path. Keep the running kernel and its modules matched.
2. Check firmware settings for Thunderbolt/USB4 PCIe tunneling. Keep IOMMU protection enabled. If the firmware offers Above 4G Decoding, use the vendor's documented eGPU setting.
3. Install the card's driver, official firmware package, Vulkan ICD, and `vulkan-tools` as the card guide describes. Keep the integrated GPU's driver.
4. Power the card and dock, attach a certified data cable, then inspect authorization with `boltctl list`. Authorize only the device you trust through your existing policy.
5. Run the diagnostic and confirm the external card appears in Vulkan. Continue to inference only after the card passes those checks.

## Kernel parameters and BARs

Start without extra eGPU parameters. Capture `cat /proc/cmdline`, the full PCI tree, and allocation errors before changing settings. `pci=realloc` is an optional diagnostic for bridge-window allocation on x86; it is not a validated fix in this repo. It does not repair missing host tunneling or an incompatible GPU driver.

Do not force maximum ReBAR size. Use the working aperture reported by the host. The enclosure's advertised bandwidth is not the negotiated PCIe speed or measured application throughput.

For a headless inference test, leave the desktop on the integrated GPU. Do not move the display session or unplug an active compute device during the first test.
