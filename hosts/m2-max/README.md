# 14-inch M2 Max MacBook Pro

Status on 2026-10-23: **an RX 7600 runs llama.cpp Vulkan inference on this host.** With local driver changes and the identity-range fix now in the boot chain's device trees, amdgpu initializes every ring, RADV enumerates the card, and llama.cpp runs on it with all 12 CPUs online. Current reference on Qwen2.5-7B Q4_K_M: pp512 945.81 / tg128 28.93 t/s with flash attention off; the decode rate varies 28.9 to 31.9 t/s across boots and is GPU- or driver-side, not CPU-limited. Those changes are not published, so no stock system reproduces this yet. Hot-plug remains untested: the card was attached at boot.

**Single-CPU correction, resolved 2026-10-23.** The first eGPU boots ran with only 1 of 12 CPUs online: a saved replacement device tree carries stale spin-table `cpu-release-addr` values, which change every boot, so the secondary cores failed to start (`CPU1..CPU11: failed to come online`, `Brought up 1 node, 1 CPU`). Rebuilding the DTB from the same boot's live tree did not help. The fix is structural: the identity-range rule ships in the boot chain's own device trees, so the bootloader writes fresh spin-table addresses and all cores start (`nproc` 12 verified). The 12-CPU rerun re-measured every model; 7B decode did not improve (it is GPU- or driver-side; a thread/core test held it flat from 1 to 12 threads and across core pinning), while the 3B gained 24 percent. The kernel, device-tree, and PR findings never depended on the CPU count.

The tested chain is an ASRock RX 7600 Challenger OC, OwlTree dock, and Rosewill ASM2464PD USB4 enclosure. The latest captured probe ran at 22:24Z with kernel `7.1.12-2-20261013.18-egpu-ARCH`, aarch64, and 16 KiB pages. Measured numbers and command: [llama.cpp record](../../benchmarks/2026-10-22-rx7600-m2max-llamacpp-vulkan.md).

## What the working run required, in order

| Stage | Observation |
|---|---|
| Normal boot | BAR0 256 MiB, BAR2 2 MiB, BAR5 1 MiB, and the audio BAR assign on every boot with the card attached, with no rescan |
| Resizable BAR | The 8 GiB request fails; PCI restores BAR0 to 256 MiB and initialization continues |
| Device-memory rules | Tunnel BARs map as Device-nGnRnE. Ordinary `memset`, wide or unaligned stores, and struct copies take an arm64 alignment fault (ESR `0x96000061`, FSC `0x21`). Aligned I/O accessors work |
| System-memory init buffers | PSP fence/command/ring buffers and the MES MQD in VRAM caused the faults; moving them to system memory removed all alignment faults |
| Failed alternative | Mapping the VRAM BAR Normal-NC hangs the host with no oops. Do not use this on the PCIe tunnel |
| The decisive fix | The device tree mapped the 64-bit prefetchable window PCI `0x8_00000000` to CPU `0xc_00000000`, while the firmware tables use PCI address equal to CPU address. Changing that one `ranges` entry of the tunnel node to identity (PCI `0xc_00000000` to CPU `0xc_00000000`) made BAR0 reads return data; before it, every BAR0/BAR2 CPU read returned all-ones while BAR5 worked |
| Full initialization | With the window working, VRAM tests pass with zero mismatches, PSP, SMU 82.97.0 and DMUB on DCN 3.2.1 initialize, and every ring registers: gfx, 8 compute, 2 sdma, vcn, jpeg, mes_kiq |
| Userspace mappings | A Vulkan driver `memcpy` into a 256 KiB VRAM buffer hit SIGBUS (alignment) on the first llama.cpp run. The local fix moves a buffer to system memory when a CPU fault occurs on a non-posted BAR; the same run then completed |

The kernel log of the completed run registers the rings without error:

```text
SMU is initialized successfully!
[drm] DMUB hardware initialized: version=0x07003300
ring gfx_0.0.0 uses VM inv eng 0 on hub 0
ring mes_kiq_3.1.0 uses VM inv eng 14 on hub 0
[drm] Initialized amdgpu 3.64.0 for 0001:05:00.0 on minor 0
```

`vulkaninfo --summary` reports `AMD Radeon RX 7600 (RADV NAVI33)`, driver radv, Mesa 26.2.5, Vulkan conformance 1.4.5.3. No display was attached and `vkcube` did not run.

## Inference, not measured cause

The earlier MES KIQ ring timeout disappeared once the 64-bit window worked. Doorbell writes to BAR2 are the presumed mechanism; that causation was not isolated. Decode speed sits below what a native PCIe x16 host would give the same model, and CPU-touched buffers live in system memory behind the tunnel. Weight placement was not profiled.

## Not done

Cable hot-plug needs a person at the dock. The 8 GiB BAR resize is unresolved. A display or cube run and the matched macOS Metal baseline from the [method](../../benchmarks/method.md) remain unrun. The identity window fix ships as DTS changes in [PR #184](https://github.com/omacom/linux-aurora/pull/184); the working boot chain carries that rule in its own device trees. No saved-DTB shortcut exists on this platform.

## Historical hot-plug bus-range clipping

The [13:10Z transport snapshot](../../benchmarks/2026-10-22-rx7600-14in-m2max-transport.md) predates all driver work. Its initial scan ended the parent bus range at bus 03, and Linux could not insert bus 04:

```text
pci_bus 0001:04: busn_res: can not insert [bus 04-03] under [bus 03]
pci 0001:03:00.0: devices behind bridge are unusable because [bus 04] cannot be assigned for them
```

The operator removed the dock's upstream bridge and rescanned its parent root port. Three passes reached the card at `0001:05:00.0`, with audio at `.1`. Small-BAR allocation also failed in that snapshot. No later result qualifies this hot-plug path; the working run had the card attached at boot.

That workaround removes every child of the selected bridge. Stop compute and unmount storage in that subtree first. Never target the internal PCI root or reuse these addresses on another topology. Verify the dock and parent with `lspci -Dtv` and sysfs parent links. For that observed topology only:

```bash
# Removes active devices in the dock subtree. Verify the addresses first.
printf '1\n' | sudo tee /sys/bus/pci/devices/0001:01:00.0/remove
printf '1\n' | sudo tee /sys/bus/pci/devices/0001:00:00.0/rescan
```

Do not loop these operations blindly. The diagnostic helper does not perform them.
