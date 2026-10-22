# ASRock Radeon RX 7600 Challenger 8GB OC

RDNA3 (Navi 33), 8 GB GDDR6, LLVM target `gfx1102`.

| Property | Value | Source |
|---|---|---|
| PCI ID (GPU) | `1002:7480` | `pci.ids` and `lspci` on our host, 2026-10-22 |
| PCI ID (HDMI/DP audio function) | `1002:ab30` | `lspci` on our host, 2026-10-22 |
| Card power | 1x 8-pin PCIe | [vendor spec page](https://www.asrock.com/Graphics-Card/AMD/Radeon%20RX%207600%20Challenger%208GB%20OC/index.asp), read 2026-10-12 |
| Recommended PSU | 550 W | same page |
| Slot interface | PCIe 4.0 x8 | same page |
| Board power draw | Not published on the vendor page. Not measured by us | |

## Status

Labels follow the repo definition: `MEASURED` is an actual runtime
observation, `BUILT-UNTESTED` means a driver compiled for the shared target
with no card runtime proof, `BLOCKED` names the missing prerequisite or the
observed failure.

| Host | Stage | Evidence |
|---|---|---|
| 14-inch M2 Max MacBook Pro | **MEASURED:** normal-boot BAR assignment and partial amdgpu initialization. **BLOCKED:** GFX MES KIQ ring test fails; RADV and inference unrun; cable hot-plug untested | [Current host result](../../hosts/m2-max/README.md), [historical transport snapshot](../../benchmarks/2026-10-22-rx7600-14in-m2max-transport.md) |
| 13-inch M1 MacBook Pro | **BLOCKED**: no amdgpu in the kernel build that host runs (checked 2026-10-16); no attach attempted | [setup.md](setup.md) |
| 16-inch M1 Max MacBook Pro | **BLOCKED**: no attach attempted, no run | |
| x86 Omarchy | **BLOCKED**: no reference run recorded on our x86 hosts | |
| Driver experiments | **MEASURED:** locally patched amdgpu reaches PSP, SMU and DMUB initialization on the M2 Max, but the GPU probe fails | [patches.md](patches.md) |

There is no GPU compute or inference result for this card on any host. PCI
enumeration and a healthy Thunderbolt link are not GPU throughput.

## In this directory

| Page | Contents |
|---|---|
| [setup.md](setup.md) | Packages, card and host constraints, read-only inspection, known issues |
| [patches.md](patches.md) | Public patch boundary, local experimental status, and upstream status |
| [ai.md](ai.md) | Which local-AI stacks can use this card and where |