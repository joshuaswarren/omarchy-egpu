# 14-inch M2 Max MacBook Pro

Status on 2026-10-22: **BLOCKED before a working RX 7600.** With a locally patched amdgpu, PSP, SMU and DMUB initialize. GFX initialization then stops at the MES KIQ ring test. RADV and llama.cpp have not run.

The tested chain is an ASRock RX 7600 Challenger OC, OwlTree dock, and Rosewill ASM2464PD USB4 enclosure. The latest captured probe ran at 21:15Z with kernel `7.1.12-2-20261013.18-egpu-ARCH`, aarch64, and 16 KiB pages. The local driver changes are not distributed here. They are not a released installation recipe.

## Measured results

| Stage | Observation | Limit |
|---|---|---|
| Normal boot | BAR0 256 MiB, BAR2 2 MiB, BAR5 1 MiB, and the audio BAR are assigned without a manual rescan; the same result occurred across four boots | This is boot enumeration, not a cable hot-plug test |
| Resizable BAR | The driver's 8 GiB request fails; PCI restores BAR0 to 256 MiB and initialization continues | An assigned BAR does not prove working CPU access |
| CPU VRAM writes | Ordinary `memset`, wide or unaligned stores, and struct copies cause an arm64 alignment fault: ESR `0x96000061`, FSC `0x21` | Tunnel BARs use Device-nGnRnE mappings; aligned I/O accessors avoided these faults |
| Memory mapping experiment | Mapping the VRAM BAR as Normal-NC hangs the host without an oops | Do not use Normal-NC as a tunnel workaround |
| Indirect VRAM access | A 4 KiB pattern written and read through MM_INDEX/MM_DATA has zero mismatches | This verifies the tested register-window access, not the direct BAR mapping |
| Direct BAR reads | CPU reads of BAR0 and BAR2 return all-ones for both 32-bit and 64-bit accesses; BAR5 and ROM reads work | The bridge window registers are correct and no AER bits appear in the inspected path; direct 64-bit-window access still fails |
| Driver initialization | With kernel CPU VRAM accesses routed through MM_INDEX, including GART, and PSP/TA buffers in system memory, PSP, SMU 82.97.0 and DMUB on DCN 3.2.1 initialize | These are local diagnostic driver changes, not a working GPU |
| GFX initialization | `ring mes_kiq_3.1.0 test failed (-110)`; the GPU probe fails | No usable card bind, Vulkan result, or inference result |

The direct mappings use CPU address `0xc00000000` for PCI address `0x800000000`. BAR0 and BAR2 are in that 64-bit prefetchable window. The successful BAR5 access uses the 32-bit window.

The 21:15Z capture includes these diagnostic results:

```text
egpu vram test 0: MM_INDEX readback mismatches 0 of 1024 dwords (first 0x7f4a7c15), BAR0 mismatches 512 of 512 qwords (first 0xffffffffffffffff)
SMU is initialized successfully!
[drm] DMUB hardware initialized: version=0x07003300
[drm:amdgpu_ring_test_helper [amdgpu]] *ERROR* ring mes_kiq_3.1.0 test failed (-110)
hw_init of IP block <gfx_v11_0> failed -110
Fatal error during GPU init
probe with driver amdgpu failed with error -110
```

The loader returned `MODPROBE_EXIT=0` despite the failed GPU probe. Cleanup also emitted warnings in `amdgpu_irq_put`. Neither a zero loader exit nor firmware initialization qualifies as a working GPU or a clean driver run.

Earlier probes failed PSP loading with `PSP load kdb failed!` while the VRAM-resident GART table was unusable. The later indirect-access probe passed that stage. It did not repair the direct BAR window.

## Inference, not a measured cause

The MES KIQ ring uses a doorbell in BAR2. Its location in the failing 64-bit window is a possible explanation for the timeout. **INFERENCE:** the timeout's cause and a device-tree range fix have not been verified. No replacement-DTB result is claimed here.

## Still untested

A true cable hot-plug test, RADV enumeration and a graphics or compute workload, and llama.cpp Vulkan on a 7-8B Q4 model remain unrun. There are no prefill or decode measurements. See the [conditional inference recipe](../../cards/rx-7600/ai.md); do not run it as a validated setup path.

## Historical hot-plug bus-range clipping

The [13:10Z transport snapshot](../../benchmarks/2026-10-22-rx7600-14in-m2max-transport.md) predates the driver probes above. Its initial scan ended the parent bus range at bus 03. Linux could not insert bus 04:

```text
pci_bus 0001:04: busn_res: can not insert [bus 04-03] under [bus 03]
pci 0001:03:00.0: devices behind bridge are unusable because [bus 04] cannot be assigned for them
```

The operator removed the dock's upstream bridge and rescanned its parent root port. Three passes reached the card at `0001:05:00.0`, with audio at `.1`. The small BAR allocation still failed in that snapshot. Later normal-boot allocation does not qualify this hot-plug path.

This historical workaround removes every child of the selected bridge. Stop compute and unmount storage in that subtree first. Never target the internal PCI root or reuse these addresses on another topology. Verify the dock and parent with `lspci -Dtv` and sysfs parent links.

For that observed topology only, the manual operations were:

```bash
# Removes active devices in the dock subtree. Verify the addresses first.
printf '1\n' | sudo tee /sys/bus/pci/devices/0001:01:00.0/remove
printf '1\n' | sudo tee /sys/bus/pci/devices/0001:00:00.0/rescan
```

Do not loop these operations blindly. Inspect the tree and kernel log after each pass. The diagnostic helper does not perform them.
