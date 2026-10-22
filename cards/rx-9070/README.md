# ASRock RX 9070 Challenger 16GB

RDNA4 (Navi 48), 16 GB GDDR6, LLVM target `gfx1201`.

| Property | Value | Source |
|---|---|---|
| PCI ID (GPU) | `1002:7550` | `pci.ids` lookup, recorded 2026-10-16 |
| PCI ID (audio function) | `1002:ab40` | `pci.ids` lookup, recorded 2026-10-16 |
| Card power | 2x 8-pin PCIe | [vendor spec page](https://www.asrock.com/Graphics-Card/AMD/Radeon%20RX%209070%20Challenger%2016GB/index.asp), read 2026-10-12 |
| Recommended PSU | 700 W | same page |
| Slot interface | PCIe 5.0 x16 | same page |
| Board power draw | Not published on the vendor page. Not measured by us | |

## Status

Labels follow the repo definition: `MEASURED` is an actual runtime
observation, `BUILT-UNTESTED` means a driver compiled for the shared target
with no card runtime proof, `BLOCKED` names the missing prerequisite or the
observed failure.

| Host | Stage | Evidence |
|---|---|---|
| 14-inch M2 Max MacBook Pro | **BLOCKED**: no attach attempted; only the RX 7600 has been attached to this host | |
| 13-inch M1 MacBook Pro | **BLOCKED**: no amdgpu in the kernel build that host runs (checked 2026-10-16); no attach attempted | [setup.md](setup.md) |
| 16-inch M1 Max MacBook Pro | **BLOCKED**: no attach attempted, no run | |
| x86 Omarchy | **BLOCKED**: no reference run recorded on our x86 hosts | |
| Driver module set | **BUILT-UNTESTED** (shared with the RX 7600; never run against a `gfx1201` device) | [patches.md](patches.md) |

There is no GPU compute or inference result for this card on any host.

## In this directory

| Page | Contents |
|---|---|
| [setup.md](setup.md) | Power, packages, upstream driver facts, read-only inspection, open questions |
| [patches.md](patches.md) | Upstream status, packaging, what is and is not proven |
| [ai.md](ai.md) | Which local-AI stacks can use this card and where |
