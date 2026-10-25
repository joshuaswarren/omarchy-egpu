# Driver patches and upstream status: RX 9070 (Navi 48)

State as of 2026-10-22.

## Patches carried: none

No AMD kernel source patch and no Mesa patch is carried for this card. RDNA4
(`gfx1201`) support is upstream in the kernel and Mesa, and the amdgpu module
package built for the [RX 7600](../rx-7600/patches.md) compiles the whole
amdgpu driver set from unmodified sources, so this card's target is inside
what it compiles.

**Measured on one host:** the module package passed strict `modpost` on
2026-10-22. On 2026-10-25 the same module (SHA-256 `1388ccac…`) loaded on the
14-inch M2 Max and initialized the `gfx1201` card: rings up, the driver's own
VRAM test passed, and llama.cpp ran (see the
[benchmark record](../../benchmarks/2026-10-25-rx9070-m2max-llamacpp-vulkan.md)). That used the local kernel and device-tree
changes described on the RX 7600 page. Nothing is proven on another host.

## Upstream status that gates this card

| Piece | Status | Source |
|---|---|---|
| amdgpu support for Navi 48 / `gfx1201` | Upstream (kernel + Mesa); no out-of-tree code needed at launch | [Phoronix, 2025-03](https://www.phoronix.com/review/amd-radeon-rx9070-linux) |
| Practical kernel/firmware/Mesa floor | Kernel 6.13.5+, current `linux-firmware`, Mesa 25+ (community notes) | [Level1Techs forum](https://forum.level1techs.com/t/9070-and-9070-xt-setup-notes-for-linux/227038) |
| `CONFIG_DRM_AMDGPU` in the published kernel package | Off at revision 7.2.10-2 | [omacom/omarchy-pkgs config](https://github.com/omacom/omarchy-pkgs/blob/master/pkgbuilds/linux-aurora/config) |
| Apple PCIe tunnel | Not upstream; tree-specific in Omarchy's kernel (see RX 7600 page) | [LKML series cover, 2026-08-30](https://lkml.iu.edu/2608.3/12164.html) |
| RADV for RDNA4 | Mesa 25+; `vulkan-radeon` packaged for aarch64 | [Arch Linux ARM vulkan-radeon](https://archlinuxarm.org/packages/aarch64/vulkan-radeon) |
| ROCm for `gfx1201` | Supported since ROCm 6.4.1 (x86_64 Linux) | [ROCm 6.4.1 release notes](https://rocm.docs.amd.com/en/docs-6.4.1/about/release-notes.html) |

## Packaging notes

Same package set as the [RX 7600](../rx-7600/setup.md#packages):

```bash
pacman -S linux-firmware-amdgpu linux-firmware-whence vulkan-radeon vulkan-icd-loader vulkan-tools
```

At the published kernel revision 7.2.10-2 this is not enough on its own: the
config leaves `CONFIG_DRM_AMDGPU` off, so a kernel or module package with the
driver enabled is required first. Current status of that work:
[rx-7600/patches.md](../rx-7600/patches.md).