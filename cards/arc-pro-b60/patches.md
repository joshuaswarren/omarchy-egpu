# Driver patches and upstream status: Arc Pro B60 (Battlemage, BMG-G21)

State as of 2026-10-23. Read [setup.md](setup.md) for what the patches are for
and what is still blocked.

## Patches carried: four, experimental, upstream status none

Base revision: linux-aurora source
`6f63677751854d57bcfac172314957bc2197c05f`. Apply the whole series in filename
order:

```bash
git am cards/arc-pro-b60/patches/000[1-4]-*.patch
# or, dry run first:
git apply --check cards/arc-pro-b60/patches/000[1-4]-*.patch
```

| Patch | What it fixes | Files touched | SPDX in those files at the base revision |
|---|---|---|---|
| `0001-xe-separate-host-allocation-from-hardware-pages.patch` | Buffer allocation rounds to the host page instead of assuming 4 KiB, and the userspace minimum-alignment query reports the real host page unless the device needs 64K | `drivers/gpu/drm/xe/xe_bo.c`, `drivers/gpu/drm/xe/xe_query.c` | MIT (Intel Corporation copyright headers) |
| `0002-xe-keep-firmware-and-ring-units-at-4k.patch` | GuC addresses, command-transmission layout assertions and ring-size encoding stay in 4 KiB GPU-page units | `xe_guc.c`, `xe_guc_ct.c`, `regs/xe_engine_regs.h` | MIT (Intel Corporation copyright headers) |
| `0003-xe-enable-experimental-16k-build.patch` | The Kconfig gate also accepts 16K host pages | `drivers/gpu/drm/xe/Kconfig` | GPL-2.0-only |
| `0004-xe-step-migration-ptes-in-gpu-pages.patch` | The migration engine masks and steps in GPU-page units, and the page-table backing check accepts host-page-rounded backing | `xe_migrate.c` | MIT (Intel Corporation copyright headers) |

## Private patches behind the 2026-10-23 decode result: not yet upstream

The measured decode result in the [benchmark record](../../benchmarks/2026-10-23-b60-m1max-llamacpp-vulkan.md#intel-driver-buffers-in-vram-2026-10-23) uses patches that are not in this directory and are not upstream:

| Piece | What it does | Status |
|---|---|---|
| xe patches 0005 to 0014 | Non-posted VRAM mappings, buffer placement rules, and patch 0014: an opt-in `xe` GEM property (`0x4e50`) that keeps selected user buffers in VRAM | Private, not yet upstream; no pull request exists. 0014 SHA-256 `967e91a9c2ee9b47a40b95e50b156865093b148780335db8ae3fc0ca1d7f3384` |
| ANV change (Mesa 26.2.4 build patch) | Sets that property for the shader heap and for selected state pools, chosen by `ANV_SHADER_HEAP_VRAM=1` and `ANV_NP_VRAM_POOLS`; CPU writes to those buffers use aligned stores only | Private, not yet upstream; no merge request exists. SHA-256 `d15848dd88753c1e8e39ca6806486b2fb8e5da7262fa333ff65806d115845572` |
| Apple PCIe root-port change | Sets the prefetchable-window enable for cold-initialized tunnel ports | Private, not yet upstream; booted and measured on the 16-inch M1 Max |

Nothing here should be read as a supported configuration. It was measured on one card on one host, and hot-plug is untested.

## Licensing

Each patch carries a preamble naming its own `SPDX-License-Identifier`, the
base revision, its experimental status, and the license state of each file it
touches as read from that file's own header. It adds no copyright line and
changes no SPDX identifier in the files it modifies; the upstream notices stay
exactly where they are. Nothing here relabels the kernel. See
[LICENSES.md](../../LICENSES.md): kernel patches keep their original per-file
licenses, and this repository's MIT license does not replace them.

## Status, precisely

**BUILT-UNTESTED for this directory's four-patch series on its own.** With these patches applied, xe compiled
through `xe.o` on a 16K arm64 configuration. The full shared kernel (which also
carries TTM, buddy, suballoc, GPUSVM, HMM and VMAP_PFN) has not been built or
linked; a C-only diagnostic kernel was deliberately stopped before link and
was never installable. The series applies cleanly with `git apply --check`
against an aurora xe checkout; that is a text check, not a build.

The measured run on the 16-inch M1 Max (see the [benchmark record](../../benchmarks/2026-10-23-b60-m1max-llamacpp-vulkan.md)) used these four patches plus local patches 0005 to 0014 and a local Apple PCIe change, none of them in this directory. It built a full local kernel, loaded xe, started the GuC and ran llama.cpp. That does not qualify the four-patch series in the shared kernel package.

Not established for the four-patch series alone:

- a final `xe.ko` link inside the shared kernel package,
- a permitted no-card `modprobe`,
- a B60 bind, GuC startup, buffer copy, migration or compute run,
- any qualified host, enclosure or card cell.

Nothing has been submitted upstream. There is no public or upstream xe pull
request, issue or patch. These patches have internal review only.

## What is deliberately not patched

Two rejected fixes matter to anyone reading this file:

- **Coherency.** Every xe system-memory DMA map passes
  `DMA_ATTR_SKIP_CPU_SYNC`, and dGPU system memory is forced write-back because
  the driver assumes CPU-coherent access. Dropping the skip flag only cleans
  pages dirtied before the single map; it does not cover continuous CPU writes,
  GPU to CPU reads, TTM moves or dma-buf re-export. A pool-level allocation
  change was rejected for the same reason: it misses imported pages and
  ownership transitions.
- **MMIO mapping.** Honouring the non-posted resource flag for local memory is
  approved in principle, but the two-call version is incomplete:
  non-contiguous VRAM mappings and dma-buf export paths need separate work. No
  speculative mapping change is carried in this directory. The local run's patch 0005 does map VRAM non-posted; it is private and not published.

The barrier-mmap guard that rejects memory-mapped I/O on hosts with pages
larger than 4 KiB is kept as is.

## Kernel config fragment

The series needs the driver and its dependencies enabled in the shared kernel
config:

```text
CONFIG_DRM_XE=m
CONFIG_DRM_BUDDY=m
CONFIG_DRM_SUBALLOC_HELPER=m
CONFIG_DRM_TTM=m
CONFIG_DRM_TTM_HELPER=m
CONFIG_DRM_GPUSVM=m
CONFIG_HMM_MIRROR=y
CONFIG_MMU_NOTIFIER=y
CONFIG_VMAP_PFN=y
```

Keep the architecture's existing 16K page selection, the integrated GPU, BTF and
Rust settings, as [hosts/apple-silicon/](../../hosts/apple-silicon/) describes.
A config fragment does not change the kernel's license, and a module-only build
that disables Rust and skips BTF emission is not a kernel-package recipe.

## Next gate

The card now appears in `vulkaninfo` and runs llama.cpp on a local kernel with private patches. The next gate is cleaning those patches up for a kernel pull request, and then building and promoting the shared kernel with them. Nothing here is submitted upstream. Stacks in [ai.md](ai.md) other than llama.cpp Vulkan remain untested.