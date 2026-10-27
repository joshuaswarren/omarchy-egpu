# Driver patches and upstream status: RX 9070 (Navi 48)

State as of 2026-10-26 (corrected; first written 2026-10-22).

## Patches carried: local kernel and module changes

The measured RX 9070 runs used a local kernel and a local amdgpu module. They are not unmodified upstream. An earlier version of this page said the module was built from unmodified sources; that had no receipt and is withdrawn. RDNA4 (`gfx1201`) support itself is upstream in the kernel and Mesa (see the table below).

- **Module:** SHA-256 `1388ccac…`, internal revision r0014. By the builder's retained build history it was built on 2026-10-22 from the 7.1.12 kernel package pin plus patches numbered 0001 to 0005 and local patches 0006 to 0014. This module's patch files are not in this repository. It changes memory placement: patch 0014 moves a VRAM buffer the CPU faults on into GTT and pins domains, makes GTT buffers write-combined by default when DMA is not coherent, and adds PSP-buffer-aware accessors. Its `egpu_vram_map` parameter (the 2026-10-25 benchmark ran with `egpu_vram_map=4`) is a BAR self-test switch, not a placement control.
- **Rebuild check (2026-10-26):** in two clean rebuilds, the 63 other ELF sections of the module reproduce from the recipe; its `.BTF` type-information section does not. The rebuilds used that source state (base plus patches 0006 to 0014), clang and LLD 22.1.8, rustc 1.93.1, bindgen 0.73.2, pahole 1.24, the same prepared kernel tree and config, and the same build paths. The stripped modules are `cd705d02…` (19,422,568 bytes) and `8a44648e…` (19,422,056 bytes), against `1388ccac…` (19,521,960 bytes) for the original. All three have the same GNU build-id (`4cd8045c…`), and 63 of the 64 ELF sections compared are byte-identical. Only `.BTF` differs. It differs between the two rebuilds, whose inputs were identical, so the file hash cannot be reproduced with this recipe; the original's `.BTF` is also about 100 KB larger than either rebuild's (3,046,936 bytes against 2,947,540 and 2,947,026). With `.BTF` removed in comparison copies, all three hash to `6ccd0cc1…`. The cause of the `.BTF` difference was not isolated (pahole 1.24 generates it in these builds), and whether it matters at run time was not tested. The build receipts and the comparison outputs are kept by the lab and are not in this repository.
- **Kernel:** `7.1.12-2-20261013.18-egpu-ARCH`, with the local kernel and device-tree changes described on the [RX 7600 page](../rx-7600/patches.md). The pull request named there is a later series (created 2026-10-23); this module is not that series' head.
- **Mesa:** the benchmark record names the staged Arch Linux ARM package `26.2.5-arch1.1`. On 2026-10-26 the loaded `libvulkan_radeon.so` was byte-identical (SHA-256 `e4acbd79…`) to the one inside that package. No Mesa patch is documented for the RX 9070 runs recorded here.

**Tested once, 2026-10-27: the amdgpu module inside our published egpu kernel package took the M2 down.** That module (SHA-256 `37f6dec1…`, 19,509,752 bytes) has none of the four `egpu_*` parameters that the local patches add; its patch set was not examined here. It was loaded with no module parameters on the 14-inch M2 Max with the RX 9070 attached. The network console logged amdgpu finishing its memory setup (16304 MiB VRAM, 256 MiB BAR), loading the display firmware and finding the video firmware, and printing the MES masks; 1.4 ms later it logged `Unable to handle kernel paging request at virtual address ffff8000c8104000` at about 23.2 s of uptime, and nothing more. About 40 s after the probe started the M2 came back by itself on the stock kernel. No call trace reached the log and the kernel was not otherwise inspected, so the cause is not established, and this was one attempt on one boot. The only module that has initialized this card on this host is the r0014-based module above (three boots, 2026-10-25 and 2026-10-26). So for this card on this host, use that module, not the package's own.

**Not tested:** an unmodified upstream amdgpu. A build of unmodified sources passed strict `modpost` on 2026-10-22 (see the RX 7600 page); that is a build check, not a run. This page does not claim that a stock module cannot work, only what was observed.

**Measured on one host:** on 2026-10-25 the module above loaded on the 14-inch M2 Max and initialized the `gfx1201` card: rings up, the driver's own VRAM test passed, and llama.cpp ran (see the
[benchmark record](../../benchmarks/2026-10-25-rx9070-m2max-llamacpp-vulkan.md)). Nothing is proven on another host.

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