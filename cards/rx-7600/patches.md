# Driver patches and upstream status: RX 7600

## Public patch series: none

No AMD kernel or Mesa patch is distributed in this repository. The working 14-inch M2 Max result uses a local amdgpu patch series and one device-tree change; both remain unpublished. Cleanup for a kernel pull request is in progress. No upstream acceptance is claimed for changes that are not yet submitted.

The local changes do three things. They handle Device-memory accesses during initialization. They move userspace buffers that fault on a non-posted BAR to system memory. Together with the device-tree window fix, they let the driver initialize every ring and run Vulkan compute. See the [measured host result](../../hosts/m2-max/README.md) and the [benchmark record](../../benchmarks/2026-10-22-rx7600-m2max-llamacpp-vulkan.md).

The earlier unmodified module package passed strict modpost against source [aurora-silicon/linux `6f636777`](https://github.com/aurora-silicon/linux/commit/6f63677751854d57bcfac172314957bc2197c05f), targeting `7.1.12-2-20261013.18-sep-ARCH`. That build result is separate from the locally patched driver that produced the working run on `7.1.12-2-20261013.18-egpu-ARCH`.

Do not treat the module build or the working run as a complete shared-kernel qualification. The result depends on unpublished changes, covers one card on one host, and has not been exercised with hot-plug.

## Published package boundary

The inspected `linux-aurora` 7.2.10-2 [package config](https://github.com/omacom/omarchy-pkgs/blob/master/pkgbuilds/linux-aurora/config) has `CONFIG_DRM_AMDGPU` disabled, as read on 2026-10-22. Installing firmware and RADV alone does not add that kernel driver. The local experimental build does not change this published-package observation.

amdgpu has no Kconfig host-page-size dependency. Its 4 KiB GPU pages differ from the 16 KiB host pages. The working run is evidence the portability gap was not page size; the blockers were the device-tree window and Device-memory access rules.

## Upstream status

| Piece | Status | Source |
|---|---|---|
| Navi 33 / `gfx1102` support | Present in upstream amdgpu | [Kernel amdgpu documentation](https://www.kernel.org/doc/html/latest/gpu/amdgpu.html) |
| Apple PCIe tunnel in the tested kernel | Downstream platform support; the upstream USB4 series alone does not provide this endpoint path | [Kernel tree](https://github.com/aurora-silicon/linux), [USB4 series cover](https://lkml.iu.edu/2608.3/12164.html) |
| RADV for RDNA3 | Packaged for aarch64; the working run used Mesa 26.2.5 | [Arch Linux ARM vulkan-radeon](https://archlinuxarm.org/packages/aarch64/vulkan-radeon) |
| Local RX 7600 changes and the device-tree fix | Not distributed here; a kernel pull request is being prepared; no upstream acceptance claimed | [Measured host result](../../hosts/m2-max/README.md) |
