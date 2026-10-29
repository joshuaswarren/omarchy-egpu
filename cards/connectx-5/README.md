# Mellanox ConnectX-5 Ex (MT28800) in a Thunderbolt dock

A dual-port ConnectX-4/5 class network card in a Thunderbolt PCIe dock on Apple Silicon Linux. This page records what was observed on two hosts and what a user needs today. Everything here is an observation from a run, with its date. Nothing here is a throughput or RDMA result.

## Status

Labels follow the repo definition: `MEASURED` is an actual runtime observation, `BLOCKED` names the observed failure.

| Host | Stage | Evidence |
|---|---|---|
| 14-inch M2 Max MacBook Pro | **MEASURED** (2026-10-29): the card enumerates behind the dock (after one Thunderbolt retry), the kernel's `mlx5_core` source (with an optional diagnostic patch, off) probes it, reads firmware `16.35.4030`, brings up the eswitch and both network interfaces, and unloads without error. No traffic, no RDMA, no cable attached | below |
| M6 Mac mini | **NOT MEASURED**: `mlx5_core` reads the card's registers and firmware version, then the first firmware command never completes. Under investigation | [M6 note](#m6-mac-mini) |
| 13-inch M1, 16-inch M1 Max | not run | |

## What was used

| Part | Value |
|---|---|
| Card | ConnectX-5 Ex, `15b3:1019` (two PCI functions), subsystem `15b3:0002`, firmware `16.35.4030`, PSID `MT_0000000009` |
| Dock | Thunderbolt 3 PCIe dock that reports itself as "TB4 eGFX" (Intel JHL6340 bridges `8086:15da`), own power supply |
| Host | 14-inch M2 Max MacBook Pro, kernel `7.1.12-2-12.6-sep-ARCH`, dock on the right-hand USB-C port (its Thunderbolt controller is `f01ac0000.cio` in the log) |
| Driver | `mlx5_core`, `mlxfw` and the RDMA modules built from the running kernel's own source tree, as external modules, with one optional diagnostic patch compiled in whose parameters were at their default (off) (see "What you need") |

## What you need

1. **A kernel with `mlx5_core`.** The Apple Silicon kernel packages used here ship none. Enable these options in the kernel you run, as modules:

   ```text
   CONFIG_NET_VENDOR_MELLANOX=y
   CONFIG_MLX5_CORE=m
   CONFIG_MLX5_CORE_EN=y
   CONFIG_MLXFW=m
   CONFIG_INFINIBAND=m          # only if you want the RDMA modules
   CONFIG_MLX5_INFINIBAND=m     # same
   # CONFIG_INFINIBAND_ON_DEMAND_PAGING is not set   (it pulls a built-in HMM_MIRROR)
   ```

   `mlx5_core` depends on the PTP clock support (`CONFIG_PTP_1588_CLOCK_OPTIONAL`; it is the `ptp` module here). If you only want to try the card, you can build the modules out of tree against the exact running kernel: same source, same `.config`, same kernel release string, and the kernel's own `Module.symvers`. That works because these kernels are built without `CONFIG_MODVERSIONS`, so a module is accepted when its vermagic string matches. A module built for any other kernel is refused.
2. **Nothing else was needed on the M2 Max**: no device-tree change, no patch to the PCI or Thunderbolt code, no bridge window change. The dock showed as authorized (`auth=1`) and the card's registers were readable through the tunnel.
3. **Power the dock before connecting the cable**, and plug the cable after the host has booted. Hot-plug worked, after one retry: the first attempt failed with `-ETIMEDOUT` (`thunderbolt-apple-nhi`: `failed to add TB domain`, and `tps6598x`: `failed to configure Type-C connection: -110`, at 23759.24 s in the log) and the retry about one second later succeeded.

## Try it safely

Block automatic loading before the first plug. A first probe that goes wrong should not run unattended:

```bash
printf 'install mlx5_core /bin/false\ninstall mlx5_ib /bin/false\n' | sudo tee /run/modprobe.d/block-mlx5.conf
```

(`/run` is cleared at reboot.) Plug the dock, then check the chain and the card before loading anything:

```bash
ls /sys/bus/thunderbolt/devices
lspci -tnn | grep -E '15da|15b3'
```

Load the driver by hand with `insmod` (which ignores the `install` rule above; load `ptp` and `mlxfw` first), then look:

```bash
sudo dmesg | grep -E 'mlx5|0001:03'
lspci -nnk -d 15b3:
ethtool -i <interface>
```

Before unplugging the dock, unload the driver (`sudo rmmod mlx5_ib mlx5_core`) and remove the block file. On the M2 Max `rmmod` of both modules returned 0 after about 5 seconds (that run's log is not attached).

## What was observed (M2 Max, 2026-10-29)

- The dock appeared as a Thunderbolt device with 2 x 20 Gb/s lanes. Both ConnectX functions were enumerated behind two JHL6340 bridges.
- `mlx5_core` printed `firmware version: 16.35.4030`; 0.49 seconds later the rate-limit and eswitch lines; 1.56 seconds after the firmware line the first interface was renamed (`enP1p3s0f0np0`, and the second function followed with `enP1p3s0f1np1`). No mlx5 timeout, no mlx5 `-110` and no probe failure (the `-110` above is the Thunderbolt domain, before mlx5 loaded). `ethtool -i` and `devlink dev info` report the same firmware.
- The ports stayed `NO-CARRIER` (no cable was attached), so no link, traffic or RDMA result exists.
- Linux printed `8.000 Gb/s available PCIe bandwidth, limited by 2.5 GT/s PCIe x4 link at <the dock's upstream bridge>`. The upstream bridge of the dock reports 2.5 GT/s x4 and the downstream port to the card trained at 8 GT/s x4. The dock's own tunnel runs at 2 x 20 Gb/s. Treat the 2.5 GT/s figure as what the tunnel's virtual port reports, not as a measured limit.
- The driver was the kernel's own `mlx5` source with one optional diagnostic patch compiled in. Its two parameters were at their default (off), which is meant to behave like the unpatched driver. This is the first run of that build on a card, so "like the unpatched driver" is not yet compared against an unpatched build on the same card.

## M6 Mac mini

These M6 observations come from the lab's own boot logs, which are not attached to this page. On the M6 the same card and dock enumerate, `mlx5_core` reads the firmware version and the command queue address, and then the first firmware command (`ENABLE_HCA`) does not complete before its timeout. After that, further accesses to the card hang. In two of two runs a configuration write in the driver's error path froze the whole machine; with that write skipped, five runs survived. The same card and dock complete that command on the M2 Max, which points at the host side and not at the card, dock or firmware. This is being worked on; do not rely on a ConnectX card on the M6 today.

## Not tested

Traffic with a cable, link speed negotiation with a switch, RoCE and RDMA, firmware flashing, power cycling the dock with the driver loaded, and anything on the 13-inch M1 and 16-inch M1 Max.
