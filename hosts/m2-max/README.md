# 14-inch M2 Max MacBook Pro

MEASURED on 2026-10-22: an ASRock RX 7600 on an OwlTree ASM2464PD dock reached PCI enumeration. The host ran kernel `7.1.12-2-20261013.18-sep-ARCH` with 16 KiB pages. The USB4 router reported 40 Gb/s in each direction. This is a transport observation, not measured GPU throughput.

## Hot-plug bus-range clipping

The initial scan found the dock bridges before the card's nested bridges. The parent bus range ended at bus 03. When the card arrived, Linux could not insert bus 04:

```text
pci_bus 0001:04: busn_res: can not insert [bus 04-03] under [bus 03]
pci 0001:03:00.0: devices behind bridge are unusable because [bus 04] cannot be assigned for them
```

The operator removed the dock's upstream PCI bridge from sysfs and rescanned its parent root port. Three passes exposed another bridge level each time. The card then appeared as `0001:05:00.0` (`1002:7480`), with an audio function at `.1`.

This workaround removes every child of the selected bridge. Stop compute and unmount any storage in that subtree first. Never target the internal PCI root or copy these addresses onto another host. Confirm the dock and parent with `lspci -Dtv` and the sysfs parent links.

For the observed topology only, the manual operations were:

```bash
# Destructive to active devices in this dock subtree. Verify addresses first.
printf '1\n' | sudo tee /sys/bus/pci/devices/0001:01:00.0/remove
printf '1\n' | sudo tee /sys/bus/pci/devices/0001:00:00.0/rescan
```

Do not loop this blindly. Inspect the PCI tree and kernel log after each pass. The read-only diagnostic does not perform this workaround.

## BAR allocation remains blocked

The final scan assigned the 256 MiB BAR0 and 2 MiB BAR2, but failed the 1 MiB non-prefetchable BAR5. The bridge non-prefetchable windows also failed. The source capture includes:

```text
pci 0001:05:00.0: BAR 0 [mem 0xc00000000-0xc0fffffff 64bit pref]: assigned
pci 0001:05:00.0: BAR 2 [mem 0xc10000000-0xc101fffff 64bit pref]: assigned
pci 0001:05:00.0: BAR 5 [mem size 0x00100000]: can't assign; no space
```

The log also reported a 2.5 GT/s x1 bottleneck at the upstream dock bridge. The USB4 40 Gb/s reading does not replace that PCIe reading. No power draw, Vulkan device, or inference rate was measured in this snapshot.

See the [measurement data](../../benchmarks/) and [RX 7600 guide](../../cards/rx-7600/). The next readiness condition is complete memory BAR assignment and successful driver initialization, followed by a hardware Vulkan probe.
