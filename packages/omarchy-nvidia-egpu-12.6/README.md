# omarchy-nvidia-egpu-12.6

Pacman package source for the boot-time Thunderbolt eGPU bind on the lab 16-inch M1 Max (`jw16`, `t6001`): NVIDIA 615.78.08 open kernel modules plus the BAR identity pass that makes both eGPUs reachable through the Apple PCIe-C root port. The modules are built out of tree; this directory only packages them.

`identity-all.py` rewrites the upper 32 bits of every enabled prefetchable bridge window and every 64-bit prefetchable BAR under `0001:00:00.0` so that DT bus addresses equal the CPU addresses the root port forwards on the wire. It reads the destination dword from the root port's own `ranges` property, so it is correct on any USB-C port; the previous hardcoded `0x8 -> 0x10` was only correct on USB-C Right (`pcie@f30000000`) and left every 64-bit BAR unreadable (`0xffffffff` reads) when the tunnel landed on `pcie@b30000000` (`0xc`).

`test-identity-all.py` is the no-root fixture test (synthetic `ranges` blobs and stubbed `lspci`/`setpci` for each USB-C port). The repo-level copy lives in `tests/test_identity_all.py` and runs in CI.
