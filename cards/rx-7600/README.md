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
| 14-inch M2 Max MacBook Pro | **MEASURED:** amdgpu initializes all rings, RADV enumerates the card, and llama.cpp Vulkan runs on it. Numbers in the benchmark record. Reproduction requires unpublished local driver and device-tree changes; a hot-plug attempt needed a bridge-removal and rescan workaround | [Benchmark record](../../benchmarks/2026-10-22-rx7600-m2max-llamacpp-vulkan.md), [host result](../../hosts/m2-max/README.md) |
| 13-inch M1 MacBook Pro | **BLOCKED**: no amdgpu in the kernel build that host runs (checked 2026-10-16); no attach attempted | [setup.md](setup.md) |
| 16-inch M1 Max MacBook Pro | **BLOCKED**: no attach attempted, no run | |
| x86 Omarchy | **BLOCKED**: no reference run recorded on our x86 hosts | |

This is the first card in this repo with a measured Linux inference result on an Apple Silicon host. It is not yet a recipe a stock system can follow: the working run depends on a local amdgpu build and one device-tree change that are not published. Enumerated BARs and a healthy link alone never proved compute; the numbers below did.

## In this directory

| Page | Contents |
|---|---|
| [setup.md](setup.md) | Packages, card and host constraints, read-only inspection, known issues |
| [patches.md](patches.md) | Public patch boundary, local experimental status, and upstream status |
| [ai.md](ai.md) | Which local-AI stacks can use this card and where |
