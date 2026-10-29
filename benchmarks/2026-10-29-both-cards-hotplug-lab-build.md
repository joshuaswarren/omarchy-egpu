# Both AMD cards on one kernel, with surprise unplug/replug (2026-10-29)

Kernel: a lab build of 7.2.11 (release string ending in `-7f91446`; tree
commit `7f91446be` on base `7876c8e83` of omacom/linux-aurora, an ancestor of
`integration/aurora`), carrying the amdgpu/ttm half of the eGPU series (7 of
the 10 commits of PR #188), an unrelated GPU statistics export, and a lab
kernel config. Not a test of the PR head.
The three PCI/DTS commits of the PR (identity tunnel windows, tunneled-slot
link wait, root-port prefetchable window) were not in this tree; its device
trees come from the base. Host: 14-inch M2 Max MacBook Pro (T6021), Wi-Fi only,
both cards in USB4 enclosures.

## What this run adds over the earlier records

- Both cards initialized on the same boot (Navi 33 DCN 3.2.1 and Navi 48
  DCN 4.0.1), MES programmed on both, every ring up, zero SError or
  alignment-fault lines across the whole day including the hotplug below.
- Output equality: a 2B-model Vulkan decode (TensorFold probe, 63 steady tokens,
  two runs per card) returned token ids equal to the on-Apple-GPU reference on
  both cards, with one identical result hash across all four runs and the
  reference (`6bfbb1a5...`). Steady median 19.6 ms/token (RX 7600) and
  27.7 ms (RX 9070); the kernel reports each card's own link at full width and
  speed, which does not rule out the USB4 tunnel or the enclosure; the cause of
  the gap is unmeasured.
- Numerics contract: 2 kernels passed gates 1-4 on both cards; 13 of 13
  deliberate-control kernels were caught (fault-injection checks of the contract
  itself). Gate time 69.1 s (7600) and 75.6 s (9070).
- Surprise unplug and replug, one cable at a time, with the driver loaded and
  the machine idle: Thunderbolt lanes retrained to CL0, the enclosure
  re-enumerated, PCI rescan restored the card, amdgpu rebuilt its rings and
  re-initialized the minor, RADV re-enumerated, and the same decode still
  returned the same hash and matching ids. No reset was needed.

## What a stock install still needs

1. The series of PR #188 merged.
2. amdgpu enabled in the kernel config (PR #67).
3. The `vulkan-radeon` userspace package (Mesa RADV 26.2.5 was used here).
4. An explicit `modprobe amdgpu`; the default distro config blacklists it on
   these Macs.

An earlier run on the same machine showed the stock integration tree
initializing neither card (BAR 0 reads all-ones; PSP alignment faults).
