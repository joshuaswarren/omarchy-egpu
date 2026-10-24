# Driver patches and upstream status: RTX 5060 Ti

## The 16K-page fixes

Two local source changes to NVIDIA open modules 595.112.07 make the module load on this host's 16 KiB pages. An unpatched stock module was never tested; the failure below was observed with fix (a) applied and fix (b) missing.

- Fix (a), `kernel-open/common/inc/nv-linux.h`: the DMA submap size was rounded to whole 2 MiB blocks only under `CONFIG_ARM64_4K_PAGES`; on 16K/64K pages it computed 4 GiB minus one page. The fix rounds down to whole 2 MiB blocks on all ARM64 page sizes. Source-level correction; not independently exercised on this hardware (it comes from reading the source and [open-gpu-kernel-modules issue #1269](https://github.com/NVIDIA/open-gpu-kernel-modules/issues/1269)).
- Fix (b), `src/nvidia/src/kernel/gpu/mem_mgr/mem_mgr.c` in `memmgrDeterminePageSize`: the system-memory default page size is the OS page size (16384 here); the final switch had no 16K case and returned 0, which became `NV_ERR_INVALID_STATE` and killed the load at `RmInitAdapter` (`0x25:0x40`). The fix keeps the 16K size for alignment and reports the 4K PTE attribute. This is the fix whose absence fails the load; with it, the module loads and initializes.

Fix (b), the page-size fix - the one proven on hardware - is submitted upstream as [open-gpu-kernel-modules PR #1480](https://github.com/NVIDIA/open-gpu-kernel-modules/pull/1480) (open). Fix (a), the submap-alignment correction - source-derived, not exercised on this hardware - is submitted as [open-gpu-kernel-modules PR #1481](https://github.com/NVIDIA/open-gpu-kernel-modules/pull/1481) (open; the PR states the derivation).

A third change is submitted upstream: [open-gpu-kernel-modules PR #1482](https://github.com/NVIDIA/open-gpu-kernel-modules/pull/1482) (open) adds a chipset-table entry for the Apple Thunderbolt/USB4 tunnel root port (`106b:100f`) that sets the same write-combining disable the registry key provides. Hardware-tested on a local 595.112.07 branch build WITH this entry and WITHOUT the registry key: no "Chipset not recognized" line, `nvidia-smi` healthy, CUDA allocation succeeds, and llama.cpp CUDA Gemma-4-12B (n=2, fa1) reads pp512 2066.22 ± 39.09 and tg128 49.88 ± 0.03 with zero Xid lines. n=1, one machine, 595 branch build. With this patch (our local build now, upstream once merged) the registry key is not needed on this host; until it merges, the key stays the documented workaround.

Plus the registry key from [setup.md](setup.md) (`RmForceDisableIomapWC=1`), which is a load option, not a patch.

## Upstream status

No NVIDIA contribution existed before these two fixes. NVIDIA requires a CLA on contributions to their repository.
The CLA is signed (October 2026). PRs #1480, #1481 and #1482 are open and
awaiting maintainer review; none had a maintainer response at publication
time.
