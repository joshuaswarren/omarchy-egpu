# Driver patches and upstream status: RTX 5060 Ti (Blackwell, GB206)

State as of 2026-10-22. Read [setup.md](setup.md) for the two routes and the
host constraints.

## Patches carried: none, for either route

No NVIDIA or nouveau source patch is carried in this repository, and the patch
series for this card is intentionally empty.

- **nouveau route:** the pinned kernel already contains GB206 chipset dispatch
  (the driver reads the chip id from the GPU's BOOT0 register and has a full
  chipset entry for it, not just a wildcard probe) and already pins the 570.144
  GSP interface. Only a config fragment is needed:

```text
CONFIG_DRM_NOUVEAU=m
CONFIG_DRM_TTM=m
CONFIG_DRM_TTM_HELPER=m
```

- **NVIDIA open modules route:** the released source (615.78.08) compiles
  unpatched for the same 16K arm64 target, matches the card on PCI class and
  identifies GB206 in its HAL tables, and needs no chipset patch. Its
  userspace and firmware come from NVIDIA's own package, not from a patch.

A config fragment or recipe does not change the kernel's license
([LICENSES.md](../../LICENSES.md)).

## Status, precisely

**BUILT-UNTESTED, build stage only.** On an arm64 16K build host:

- nouveau plus its DRM helper modules compiled, linked and passed modpost with
  no source patch, against kernel source
  `6f63677751854d57bcfac172314957bc2197c05f`;
- the NVIDIA open kernel modules also compiled unpatched for the same target.

Not established at any point:

- an install of either driver on any host,
- a `modprobe`, a PCI bind, a GSP boot, a Vulkan instance or a CUDA context,
- a card attach on any host or enclosure,
- any qualified host, enclosure or card cell, and any benchmark.

## Upstream status

Nothing has been submitted upstream from this work: no nouveau patch, no Mesa
patch, no NVIDIA issue or pull request. The NVIDIA open modules are NVIDIA's
own published source, dual licensed per file (MIT, with linked Linux modules
under MIT and GPLv2 terms); preserve each file's notices and the full license
when you build it. NVIDIA asks for a CLA on contributions to that repository;
no contribution is proposed here.

The nouveau in-kernel source carries an MIT permission notice. The surrounding
kernel carries its own per-file license requirements; do not relabel the kernel
as MIT.

## Firmware licensing

The GSP binaries are not covered by the open modules' MIT or GPLv2 terms. The
distribution firmware package declares its own license identifiers
(`LicenseRef-WHENCE`, `LicenseRef-nvidia`) and depends on `linux-firmware-whence`.
Use the official package and do not vendor blobs into this repository.

## Known upstream defect, not patched here

[open-gpu-kernel-modules #1269](https://github.com/NVIDIA/open-gpu-kernel-modules/issues/1269)
remains open as of 2026-10-22: `NV_DMA_SUBMAP_MAX_PAGES` is sized only for 4 KiB
ARM pages, and on larger ARM pages the resulting window is not 2 MiB-aligned, so
system-memory mappings of 4 GiB and above can take unusable pages just below
each 4 GiB boundary. It was reproduced upstream on 64K-page hosts and the guard
is unchanged in 615.78.08. We have not measured it on a 16K kernel, so we carry
no speculative fix for it: publish nothing here that has not been reproduced.

## Next gate

After the shared 16K kernel is promoted: a no-card `modprobe nouveau`, the
firmware file check from [setup.md](setup.md), then the first attach with a
full capture of the kernel log, PCI topology, BAR sizes and parent bridge
windows. Only once the card appears in `vulkaninfo` output with clean logs does
anything in [ai.md](ai.md) become testable.