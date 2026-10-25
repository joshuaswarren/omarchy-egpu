# RX 9070 setup

Practical setup for the ASRock RX 9070 Challenger 16GB. Status and identity
live in [README.md](README.md). This card has been attached to one host, the 14-inch M2 Max (see the
[benchmark record](../../benchmarks/2026-10-25-rx9070-m2max-llamacpp-vulkan.md)); nothing here is a performance claim
beyond that record.

## Hardware and power

Same chain class as the RX 7600: host USB4/Thunderbolt port, certified cable,
enclosure or dock with a real PCIe slot, card. See
[docks/](../../docks/) for enclosure notes and the measured OwlTree chain.

1. Connect **both** 8-pin connectors, plus the dock's 24-pin ATX lead. The
   vendor spec page lists 2x 8-pin; a single-lead setup is not a supported
   configuration for this card.
2. The vendor recommends a 700 W PSU (card on a desktop board; leave headroom
   for dock conversion losses).
3. PSU on before the cable goes into the host. Never swap a card with the PSU
   on.
4. Attach, eject, and unplug procedures are host-specific: use the
   [host guides](../../hosts/), which carry the observed topology and safety
   boundaries.

## Driver support facts (upstream, not our runs)

- RDNA4 / `gfx1201` support is upstream in the kernel and Mesa; launch
  coverage confirmed no out-of-tree code was needed
  ([Phoronix, 2025-03](https://www.phoronix.com/review/amd-radeon-rx9070-linux)).
  Community setup notes put the practical floor at kernel 6.13.5 or newer with
  current `linux-firmware` and Mesa 25
  ([Level1Techs forum](https://forum.level1techs.com/t/9070-and-9070-xt-setup-notes-for-linux/227038)).
- **Driver on Apple Silicon hosts:** the published Omarchy kernel package
  `linux-aurora` 7.2.10-2 sets `# CONFIG_DRM_AMDGPU is not set` in its config
  ([omacom/omarchy-pkgs](https://github.com/omacom/omarchy-pkgs/blob/master/pkgbuilds/linux-aurora/config),
  read 2026-10-22). An amdgpu module package has been built against the
  lab-pinned kernel (status in [rx-7600/patches.md](../rx-7600/patches.md));
  on 2026-10-25 that module loaded and initialized a `gfx1201` card on the M2 Max.
- RADV (Vulkan) supports `gfx1201` in Mesa 25+; `vulkan-radeon` 26.2.5-1
  exists for aarch64 in Arch Linux ARM (checked 2026-10-22).
- ROCm officially supports the RX 9070 for compute since ROCm 6.4.1
  ([release notes](https://rocm.docs.amd.com/en/docs-6.4.1/about/release-notes.html)),
  x86_64 Linux only.

## Packages

Same package set as the [RX 7600](../rx-7600/setup.md#packages):

```bash
pacman -S linux-firmware-amdgpu linux-firmware-whence vulkan-radeon vulkan-icd-loader vulkan-tools
```

At the published kernel revision 7.2.10-2 the config leaves
`CONFIG_DRM_AMDGPU` off, so these packages alone do not give you a driver;
current status of that prerequisite: [rx-7600/patches.md](../rx-7600/patches.md).

## Card and host constraints (Apple Silicon)

The transport constraints in
[rx-7600/setup.md](../rx-7600/setup.md#card-and-host-constraints-apple-silicon)
apply unchanged (16 KiB-page kernel required; tunnel windows of 2 GiB on base
M1/M2 parts and 8 GiB on Pro/Max/Ultra and M3; no `dma-coherent` on tunnel
nodes). The parts that matter more on a 16 GB card:

- A full-VRAM resizable BAR (16 GiB) cannot map inside any Apple tunnel window
  (2 GiB or 8 GiB). Expect the 256 MiB fallback BAR; treat full-VRAM ReBAR as
  unavailable on these hosts.
- The measured RX 7600 run on an 8 GiB-window host ran out of *small* window
  space across five bridge levels while the large BARs assigned. This card
  exposes the same small BARs plus an audio function, so the same
  `can't assign; no space` lines are the first thing to look for.
- A `SError` or `Unhandled fault` after attach is a stop signal, not a log
  line: pull nothing, power the host off with the card attached.

## Read-only inspection

Use the [RX 7600 inspection commands](../rx-7600/setup.md#read-only-inspection)
with this card's IDs:

```bash
lspci -nn -d 1002:    # expect 1002:7550 plus an audio function
```

## Known issues

Measured on this card, one host: the 16 GiB resizable BAR is not available
(the tunnel window is 8 GiB and the card keeps its 256 MiB BAR), and decode
is limited by a per-dispatch cost of 40 to 50 us (see the
[README](README.md#why-decode-is-dispatch-bound-on-this-setup)). The measured
transport-level issues that any card hits behind the same dock (bus-range
clipping on first hotplug, small-BAR exhaustion, minimum idle link training)
are documented with verbatim excerpts in the
[RX 7600 known issues](../rx-7600/setup.md#known-issues)
and the [M2 Max host guide](../../hosts/m2-max/README.md). This card's own
behavior beyond that stays unrecorded; the logs will say it, we will not
predict it.

## First-run requirements

When this card is first attached, the run must also record (per the
[benchmark method](../../benchmarks/method.md)): PSU model, connectors used, a
1 Hz power log if telemetry exists, and `LnkSta` under load. The first RX 7600
snapshot has no power metadata; that gap is what the method page requires
future runs to close.
