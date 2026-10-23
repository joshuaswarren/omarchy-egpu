# Driver patches and upstream status: RTX 5060 Ti

## The 16K-page fixes

Two local source changes to NVIDIA open modules 595.112.07 make the module load on this host's 16 KiB pages. An unpatched stock module was never tested; the failure below was observed with fix (a) applied and fix (b) missing.

- Fix (a), `kernel-open/common/inc/nv-linux.h`: the DMA submap size was rounded to whole 2 MiB blocks only under `CONFIG_ARM64_4K_PAGES`; on 16K/64K pages it computed 4 GiB minus one page. The fix rounds down to whole 2 MiB blocks on all ARM64 page sizes. Source-level correction; not independently exercised on this hardware (it comes from reading the source and the upstream open-gpu-kernel-modules issue about 64K-page submap sizing).
- Fix (b), `src/nvidia/src/kernel/gpu/mem_mgr/mem_mgr.c` in `memmgrDeterminePageSize`: the system-memory default page size is the OS page size (16384 here); the final switch had no 16K case and returned 0, which became `NV_ERR_INVALID_STATE` and killed the load at `RmInitAdapter` (`0x25:0x40`). The fix keeps the 16K size for alignment and reports the 4K PTE attribute. This is the fix whose absence fails the load; with it, the module loads and initializes.

The two fixes are local; neither has been submitted upstream yet, so no upstream link exists. This page links them the day a public pull request appears.

Plus the registry key from [setup.md](setup.md) (`RmForceDisableIomapWC=1`), which is a load option, not a patch.

## Upstream status

No NVIDIA contribution existed before these two fixes; they will be the first from this effort. NVIDIA requires a CLA on contributions to their repository; the PRs follow that process.
