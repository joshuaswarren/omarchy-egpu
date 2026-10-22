# Driver patches and upstream status: Arc Pro B60 (Battlemage, BMG-G21)

State as of 2026-10-22. Read [setup.md](setup.md) for what the patches are for
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

## Licensing

Each patch carries a preamble naming its own `SPDX-License-Identifier`, the
base revision, its experimental status, and the license state of each file it
touches as read from that file's own header. It adds no copyright line and
changes no SPDX identifier in the files it modifies; the upstream notices stay
exactly where they are. Nothing here relabels the kernel. See
[LICENSES.md](../../LICENSES.md): kernel patches keep their original per-file
licenses, and this repository's MIT license does not replace them.

## Status, precisely

**BUILT-UNTESTED, build stage only.** With these patches applied, xe compiled
through `xe.o` on a 16K arm64 configuration. The full shared kernel (which also
carries TTM, buddy, suballoc, GPUSVM, HMM and VMAP_PFN) has not been built or
linked; a C-only diagnostic kernel was deliberately stopped before link and
was never installable. The series applies cleanly with `git apply --check`
against an aurora xe checkout; that is a text check, not a build.

Not established at any point:

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
  speculative mapping change is carried.

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

After the shared kernel is built and promoted: a no-card `modprobe xe`, then
the first attach with a full capture of the kernel log, PCI topology, BAR sizes
and parent bridge windows. Only once the card appears in `vulkaninfo` output
with clean logs does anything in [ai.md](ai.md) become testable.