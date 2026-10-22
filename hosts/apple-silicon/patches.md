# Transport patch status

No transport source patch is carried against kernel source `6f63677751854d57bcfac172314957bc2197c05f`. That baseline already contains the M1/M1 Max/M2 Max tunnel initialization and USB4 PCIe routing. The local transport patch series is empty. No new upstream transport submission was made for this delivery.

The [transport config fragment](transport.config) states the shared build requirements. It matched 21 of 21 required settings in the retained `.18` configuration, with the two debug-write/test options disabled and PCI realloc autodetection disabled. It is not a full kernel configuration or proof of endpoint readiness.

Integrate GPU fragments into the same host kernel configuration. Build the kernel and its matching modules together. Do not combine modules from different kernel releases or use a C-only diagnostic build as a complete package.

The [public kernel tree](https://github.com/aurora-silicon/linux) is the source location. The current baseline is downstream work; the upstream USB4 series alone does not establish the complete Apple PCIe endpoint path. The [M2 Max observation](../m2-max/) records the remaining allocation failure.

`CONFIG_PCI_REALLOC_ENABLE_AUTO` detects firmware SR-IOV allocation conditions. It is not a generic eGPU BAR fix. No default command-line or device-tree aperture change is validated by this repository.
