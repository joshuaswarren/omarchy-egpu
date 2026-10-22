# Driver patches and upstream status: RX 7600 (Navi 33)

State as of 2026-10-22.

## Patches carried: none

No AMD kernel source patch and no Mesa patch is carried for this card. The
work that exists is packaging and build evidence, described below for what it
is: evidence, not an installation path.

## Kernel driver status

- The published Omarchy kernel package `linux-aurora` 7.2.10-2 sets
  `# CONFIG_DRM_AMDGPU is not set` in its config
  ([config file](https://github.com/omacom/omarchy-pkgs/blob/master/pkgbuilds/linux-aurora/config),
  read 2026-10-22). That statement is scoped to this published revision; a
  later package can change it, and this page will be updated when it does.
- amdgpu has no Kconfig dependency on host page size, and its GPU pages are
  4 KiB independent of the host page size (kernel source read,
  `drivers/gpu/drm/amd/include/amdgpu_gart.h`). Compiling and running it on a
  16 KiB-page Apple Silicon kernel is therefore expected to be possible. That
  is expectation; there is no runtime proof yet on any host.

## What has been built (evidence, not a setup path)

An amdgpu module package compiled against the lab kernel pinned at
[aurora-silicon/linux `6f636777`](https://github.com/aurora-silicon/linux/commit/6f63677751854d57bcfac172314957bc2197c05f)
(the `7.1.12-2-20261013.18-sep-ARCH` build, aarch64, 16 KiB pages). Status,
precisely:

- **BUILT-UNTESTED.** The package passed a strict `modpost` (no unresolved
  symbols) on 2026-10-22. It has **not** been installed on any host, not been
  loaded into any running kernel, and has never touched the card. No runtime
  claim exists.
- The build shows that amdgpu and its DRM helper modules (`ttm`, DRM core and
  display helpers, `amdxcp`, scheduler and buddy helpers) compile for this
  16 KiB-page aarch64 target from unmodified kernel sources.
- It does **not** prove a complete shared kernel package, a boot
  qualification, or GPU function. The shared-kernel package route is the
  intended deliverable; when it ships in a package, this page links it with
  per-file licensing (kernel modules remain GPL-2.0).

## Upstream status that gates this card

| Piece | Status | Source |
|---|---|---|
| amdgpu support for Navi 33 / `gfx1102` | Upstream long since; any current kernel | [kernel.org amdgpu docs](https://www.kernel.org/doc/html/latest/gpu/amdgpu.html) |
| Apple PCIe tunnel (the transport) | **Not upstream.** The 2026-08-30 Apple USB4/Thunderbolt series supports only XDomain and USB3 via USB4: "Both PCIe and DisplayPort tunnels will come later" | [LKML series cover, 2026-08-30](https://lkml.iu.edu/2608.3/12164.html) |
| PCIe tunnel in Omarchy's kernel | Present as tree-specific work (ACIO coprocessor bring-up, PCIe-C root complexes, tunnel DART domains, `usb4-pcie-tunnel` device-tree nodes), measured enumerating real docks 2026-10-12 and 2026-10-22 | [aurora-silicon/linux](https://github.com/aurora-silicon/linux), commits `6110014cc`, `97bf64789`, `c2b4c790d`, `13d048367` (read 2026-10-12) |
| `CONFIG_DRM_AMDGPU` in the published kernel package | Off at revision 7.2.10-2 (see above) | [omacom/omarchy-pkgs config](https://github.com/omacom/omarchy-pkgs/blob/master/pkgbuilds/linux-aurora/config) |
| RADV (vulkan-radeon) for RDNA3 | Upstream Mesa; packaged for aarch64 | [Arch Linux ARM vulkan-radeon](https://archlinuxarm.org/packages/aarch64/vulkan-radeon) |