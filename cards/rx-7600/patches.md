# Driver patches and upstream status: RX 7600

## Public patch series: none

No AMD kernel or Mesa patch is distributed in this repository. The latest 14-inch M2 Max results use a local amdgpu patch series. It remains private and is not an installation path. No upstream submission or acceptance is claimed for those changes.

The local changes handle Device-memory accesses during initialization and test indirect VRAM access through MM_INDEX. They allow PSP, SMU and DMUB initialization. GFX initialization still fails at the MES KIQ ring test. See the [measured host result](../../hosts/m2-max/README.md).

The earlier unmodified module package passed strict modpost against source [aurora-silicon/linux `6f636777`](https://github.com/aurora-silicon/linux/commit/6f63677751854d57bcfac172314957bc2197c05f), targeting `7.1.12-2-20261013.18-sep-ARCH`. That build result is separate from the later locally patched driver probes on `7.1.12-2-20261013.18-egpu-ARCH`.

Do not treat the module build or the partial initialization as a complete shared-kernel qualification. The current GPU probe fails; no usable card bind or Vulkan run is established.

## Published package boundary

The inspected `linux-aurora` 7.2.10-2 [package config](https://github.com/omacom/omarchy-pkgs/blob/master/pkgbuilds/linux-aurora/config) has `CONFIG_DRM_AMDGPU` disabled, as read on 2026-10-22. Installing firmware and RADV alone does not add that kernel driver. The local experimental build does not change this published-package observation.

amdgpu has no Kconfig host-page-size dependency. Its 4 KiB GPU pages differ from the 16 KiB host pages. The measured partial initialization does not establish that every driver access path works on this platform.

## Upstream status

| Piece | Status | Source |
|---|---|---|
| Navi 33 / `gfx1102` support | Present in upstream amdgpu | [Kernel amdgpu documentation](https://www.kernel.org/doc/html/latest/gpu/amdgpu.html) |
| Apple PCIe tunnel in the tested kernel | Downstream platform support; the upstream USB4 series alone does not provide this endpoint path | [Kernel tree](https://github.com/aurora-silicon/linux), [USB4 series cover](https://lkml.iu.edu/2608.3/12164.html) |
| RADV for RDNA3 | Packaged for aarch64; not run on this card in the current setup | [Arch Linux ARM vulkan-radeon](https://archlinuxarm.org/packages/aarch64/vulkan-radeon) |
| Local RX 7600 changes | Not distributed here; partial initialization only; no upstream acceptance claimed | [Current measured result](../../hosts/m2-max/README.md) |
