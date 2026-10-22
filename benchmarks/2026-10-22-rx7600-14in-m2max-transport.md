# RX 7600 on a 14-inch M2 Max MacBook Pro: transport record, 2026-10-22

**This is not a performance benchmark.** No GPU driver was bound, no compute
ran, and no throughput number exists. This page records what the PCI layer
actually did when an ASRock Radeon RX 7600 Challenger 8GB OC was attached
through an OwlTree M.2-to-PCIe x16 dock (ASMedia ASM2464PD USB4 bridge).

## Environment

| Field | Value |
|---|---|
| Host | 14-inch M2 Max MacBook Pro, Omarchy Linux, 16 KiB pages |
| Kernel | `7.1.12-2-20261013.18-sep-ARCH` (aarch64) |
| GPU driver | **None bound.** The kernel build has `CONFIG_DRM_AMDGPU` off; `lspci -k` shows no driver for the card |
| Vulkan ICD | Not exercised. No `vulkaninfo` ran |
| Chain | Host USB4 port, cable, OwlTree dock (ASM2464PD), card in x16 slot. The link passed through an in-line Thunderbolt retimer on the host side |
| PSU and power wiring | **Not recorded.** No PSU model, connector check, or power/temperature log exists for this snapshot |
| Cable | **Not recorded** (brand and standard unknown) |
| Commands | Read-only: `lspci -Dtv`, `lspci -Dnnvvk`, `lspci -k`, `boltctl list`, `cat /proc/iomem`, `dmesg`. No configuration was changed by the capture |

## Timeline (UTC, from the kernel log)

| Time | Event |
|---|---|
| 12:54:18Z | Tunnel authorized: `ASMedia 246x`, USB4 generation, reported `40 Gb/s = 2 lanes * 20 Gb/s` in each direction |
| first hotplug | Bridge stack trains one level per scan; the bus range ends too early and the card's level is unreachable (issue 1 below) |
| next minutes | The operator removed the dock's upstream PCI bridge and rescanned its parent root port. Each pass exposed one more bridge level; the third pass reached the card |
| 13:10Z | Read-only snapshot captured |

## What enumerated

The card and its audio function, behind four bridge levels:

```text
-[0001:00]---00.0-[01-05]----00.0-[02-05]----00.0-[03-05]----00.0-[04-05]----00.0-[05]--+-00.0  Advanced Micro Devices, Inc. [AMD/ATI] Navi 33 [Radeon RX 7600/7600 XT/7600M XT/7600S/7700S / PRO W7600]
                                                                                        \-00.1  Advanced Micro Devices, Inc. [AMD/ATI] Navi 31 HDMI/DP Audio
```

Device IDs: GPU `1002:7480` at `0001:05:00.0`, audio `1002:ab30` at
`0001:05:00.1`. The bridge chain: dock upstream `0001:01:00.0` (ASMedia
`1b21:2463`), an intermediate bridge at `0001:02:00.0`, then a PCIe switch
pair `1002:1478` (upstream) and `1002:1479` (downstream) in front of the card.

## Issue 1: bus-range clipping on first hotplug

```text
pci_bus 0001:04: busn_res: can not insert [bus 04-03] under [bus 03]
pci 0001:03:00.0: devices behind bridge are unusable because [bus 04] cannot be assigned for them
```

The workaround (remove the dock's upstream bridge, rescan its parent, repeat
once per level) is host-specific and documented with safety boundaries in the
[M2 Max host guide](../hosts/m2-max/README.md).

## Issue 2: large BARs assigned, small BARs refused

```text
pci 0001:05:00.0: BAR 0 [mem 0xc00000000-0xc0fffffff 64bit pref]: assigned
pci 0001:05:00.0: BAR 2 [mem 0xc10000000-0xc101fffff 64bit pref]: assigned
pci 0001:05:00.0: BAR 5 [mem size 0x00100000]: can't assign; no space
pci 0001:05:00.0: BAR 4 [io  size 0x0100]: can't assign; no space
pci 0001:05:00.0: ROM [mem size 0x00020000 pref]: can't assign; no space
pci 0001:05:00.1: BAR 0 [mem size 0x00004000]: can't assign; no space
```

The tunnel root window used here is 8 GiB 64-bit prefetchable
(`0xc00000000-0xdffffffff`) plus a roughly 1 GiB 32-bit prefetchable window
and a roughly 1 GiB non-prefetchable window. `/proc/iomem` after assignment:

```text
c00000000-dffffffff : pcie@b30000000
  c00000000-c101fffff : PCI Bus 0001:01
    c00000000-c101fffff : PCI Bus 0001:02
      c00000000-c101fffff : PCI Bus 0001:03
        c00000000-c101fffff : PCI Bus 0001:04
          c00000000-c101fffff : PCI Bus 0001:05
            c00000000-c0fffffff : 0001:05:00.0
            c10000000-c101fffff : 0001:05:00.0
```

Both assigned ranges are the card's 64-bit prefetchable BARs (256 MiB and
2 MiB). The refusals are all small-window resources (non-prefetchable memory,
I/O, option ROM, audio BAR) spread across five bridge levels, each of which
also needs a window. Whether this blocks a driver bind is unknown.

## Issue 3: idle-state PCIe link

```text
pci 0001:05:00.0: 2.000 Gb/s available PCIe bandwidth, limited by 2.5 GT/s PCIe x1 link at 0001:01:00.0 (capable of 126.024 Gb/s with 16.0 GT/s PCIe x8 link)
```

The kernel names the slowest link in the path: the dock's upstream bridge
reports `LnkSta: Speed 2.5GT/s, Width x1` while advertising up to 16 GT/s.
The Thunderbolt layer independently reports 40 Gb/s each way on the tunnel.
Both are idle-state readings; the link was never read under load, so no
transport-bandwidth conclusion is drawn from this record.

## What this record does not establish

- That the card works as a GPU. No driver bound.
- Any throughput, latency, or power number. None was measured.
- That the 40 Gb/s tunnel reading is usable bandwidth for a GPU. The PCIe
  layer's own reading at idle was 2.000 Gb/s; under-load behavior is unknown.

The card guide for the follow-up work: [cards/rx-7600/](../cards/rx-7600/).
