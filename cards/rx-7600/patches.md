# Driver patches and upstream status: RX 7600

## Patch series: submitted

The kernel work is open as [omacom/linux-aurora PR #188](https://github.com/omacom/linux-aurora/pull/188), head `3f5c88fa` (10 commits on `integration/aurora`): the amdgpu changes, identity `ranges` entries for the tunnel windows of the T600x/T602x families, a link-wait fix, and a tunnel root-port prefetchable-window enable fix. The pull request was created on 2026-10-23, after the module that produced the measured runs was built (next paragraph). It replaces PR #184, which carried the same head and was closed when its branch was deleted by mistake. The PR is open and not merged, so no part of it is upstream. A reviewer passed this full head on PR #184. Local checks: all commits signed off, checkpatch clean, amdgpu/TTM/pcie-apple objects compile with LLVM 22 `W=1` (one pre-existing frame-size warning), and the T600x/T602x DTBs build showing identity ranges. The PR states the runtime proof comes from the same logic on the 7.1.12 tree; the 7.2.11 tree itself has not been booted on hardware, and the one hot-plug attempt on this host enumerated the card but failed BAR allocation (see the host README).

The measured runs used a local amdgpu module, SHA-256 `1388ccac…` (internal revision r0014; the [2026-10-22 record](../../benchmarks/2026-10-22-rx7600-m2max-llamacpp-vulkan.md) names this hash), built on 2026-10-22 from the 7.1.12 kernel package pin plus patches numbered 0001 to 0005 and local patches 0006 to 0014, per the builder's retained build history. It is not the head of the pull request above, and its patch files are not in this repository. The local changes, as the builder describes them, do three things. They handle Device-memory accesses during initialization. They move userspace buffers that fault on a non-posted BAR to system memory. Together with the device-tree window fix, they let the driver initialize every ring and run Vulkan compute. See the [measured host result](../../hosts/m2-max/README.md) and the [benchmark record](../../benchmarks/2026-10-22-rx7600-m2max-llamacpp-vulkan.md).

The earlier unmodified module package passed strict modpost against source [aurora-silicon/linux `6f636777`](https://github.com/aurora-silicon/linux/commit/6f63677751854d57bcfac172314957bc2197c05f), targeting `7.1.12-2-20261013.18-sep-ARCH`. That build result is separate from the locally patched driver that produced the working run on `7.1.12-2-20261013.18-egpu-ARCH`.

Do not treat the module build or the working run as a complete shared-kernel qualification. The result depends on unpublished changes, covers one card on one host, and the one hot-plug attempt (host README, Historical hot-plug) enumerated the card but failed BAR allocation, so only the attached-at-boot path is measured.

## Proposed Mesa change: not yet submitted

RADV writes shader code with the CPU into a VRAM buffer that has CPU access. On this host the kernel reports no CPU-visible VRAM, so that buffer is placed in system memory behind the tunnel. The existing `RADV_PERFTEST=dmashaders` path (invisible VRAM plus an SDMA upload) avoids that. The proposed change makes that path the default when the device has dedicated VRAM and `vram_vis_size_kb == 0`.

Status: proposed upstream fix, not yet submitted. It has not been posted to Mesa. Base: Mesa 26.2.5. Patch SHA-256 `73c54d12d1da138e4abc11b6abad406712efe7ed1da8f21b4729696bfae840a6`. Measured only on the RX 7600 on the 14-inch M2 Max: the patched build matches the environment switch within 0.1 t/s (see the [window l section](../../benchmarks/2026-10-22-rx7600-m2max-llamacpp-vulkan.md)). Not tested: any other GPU or host, any test suite beyond llama.cpp.

```diff
--- a/src/amd/vulkan/radv_device.c
+++ b/src/amd/vulkan/radv_device.c
@@ -1598,7 +1598,13 @@
    }
    device->private_sdma_queue = VK_NULL_HANDLE;
 
-   device->shader_use_invisible_vram = (instance->perftest_flags & RADV_PERFTEST_DMA_SHADERS) &&
+   /* Shader code is written by the CPU. When the kernel exposes no CPU-visible VRAM (for example a dGPU behind a
+    * non-posted PCIe tunnel), a CPU-accessed VRAM buffer ends up in system memory and every instruction cache miss
+    * crosses the link, so upload the code with SDMA into invisible VRAM instead.
+    */
+   const bool no_visible_vram = pdev->info.has_dedicated_vram && pdev->info.vram_vis_size_kb == 0;
+
+   device->shader_use_invisible_vram = ((instance->perftest_flags & RADV_PERFTEST_DMA_SHADERS) || no_visible_vram) &&
                                        /* SDMA buffer copy is only implemented for GFX7+. */
                                        pdev->info.gfx_level >= GFX7;
    result = radv_init_shader_upload_queue(device);
```

## Published package boundary

The inspected `linux-aurora` 7.2.10-2 [package config](https://github.com/omacom/omarchy-pkgs/blob/master/pkgbuilds/linux-aurora/config) has `CONFIG_DRM_AMDGPU` disabled, as read on 2026-10-22. Installing firmware and RADV alone does not add that kernel driver. The local experimental build does not change this published-package observation.

amdgpu has no Kconfig host-page-size dependency. Its 4 KiB GPU pages differ from the 16 KiB host pages. The working run is evidence the portability gap was not page size; the blockers were the device-tree window and Device-memory access rules.

## Upstream status

| Piece | Status | Source |
|---|---|---|
| Navi 33 / `gfx1102` support | Present in upstream amdgpu | [Kernel amdgpu documentation](https://www.kernel.org/doc/html/latest/gpu/amdgpu.html) |
| Apple PCIe tunnel in the tested kernel | Downstream platform support; the upstream USB4 series alone does not provide this endpoint path | [Kernel tree](https://github.com/aurora-silicon/linux), [USB4 series cover](https://lkml.iu.edu/2608.3/12164.html) |
| RADV for RDNA3 | Packaged for aarch64; the working run used Mesa 26.2.5 | [Arch Linux ARM vulkan-radeon](https://archlinuxarm.org/packages/aarch64/vulkan-radeon) |
| Local RX 7600 changes and the device-tree fix | Open as [PR #188](https://github.com/omacom/linux-aurora/pull/188), not merged | [PR](https://github.com/omacom/linux-aurora/pull/188), [measured host result](../../hosts/m2-max/README.md) |
