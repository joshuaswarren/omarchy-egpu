# Intel compute-runtime (NEO) on aarch64: OpenCL and Level Zero on the B60 (2026-11-02)

First run of Intel's GPU compute stack on aarch64 Linux: an Arc Pro B60 in
a USB4 enclosure on a 16-inch M1 Max (Omarchy, kernel 7.1.12 lab tree) now
enumerates under OpenCL and Level Zero, built entirely from source.

```
$ clinfo
Platform Name   Intel(R) OpenCL Graphics (discrete)
Device Name     Intel(R) Arc(TM) Pro B60 Graphics
Device Version  OpenCL 3.0 NEO    Driver Version 26.45.0
Max compute units 160   Max clock 2400MHz
Global memory   25155756032 (23.43 GiB)
```

Level Zero verifies as well (`zello_world`: driver initialized,
`ZE_DEVICE_TYPE_GPU`, deviceId 0xE211, API 1.18).

## What was built (all native aarch64, prefix install, nothing system-wide)

| Component | Commit | Notes |
|---|---|---|
| gmmlib | 733c91a19 | Upstream has an aarch64 branch; needs `-DCMAKE_C_FLAGS=-Wformat` with GCC 16 and `-DRUN_TEST_SUITE=OFF` (ULT segfaults on aarch64). |
| level-zero loader | 52d92f8b1 | Portable C++; upstream ships arm64 CI. |
| compute-runtime (NEO) | 8730a6c43 | Builds with the three patches below; yields `libigdrcl.so`, `libze_intel_gpu.so.1.18.0`, in-tree `ocloc`. |

## The three port patches

Full diff: [neo-aarch64-port.patch](patches/neo-aarch64-port.patch).

1. **aarch64 build fix (genuine, upstreamable):** `cpuintrinsics.cpp` calls
   `_mm_mfence()` inside `mfence()`; sse2neon does not provide it, so any
   aarch64 build of current master fails to link. Guarded fallback to
   `__sync_synchronize()` under `__ARM_ARCH`.
2. **Small-BAR policy for xe:** upstream `IoctlHelperXe` returns `false`
   from `isSmallBarConfigAllowed()`, aborting runtime init when ReBAR is
   absent. An eGPU on Apple Silicon has no ReBAR firmware control (256 MB
   BAR2 window over 23.4 GB probed); the patch returns `true` like i915.
   Experiment flag: if ReBAR is ever enabled on the host, the patch becomes
   unnecessary.
3. **16 KB GEM alignment:** this lab kernel's xe driver rejects GEM create
   sizes that are not multiples of 16 KB (`EPERM` for 4/8/12 KB probes);
   NEO's 4096-byte tag buffer hit it first. Allocation sizes are aligned up.

## Remaining gap: online kernel compilation (IGC)

NEO `dlopen`s `libigc.so.2`/`libigdfcl.so.2` for online OpenCL C
compilation; Intel ships IGC only as amd64 packages. Offline compilation
works today: compile on an x86 host with amd64 `ocloc`, then
`clCreateProgramWithBinary` on aarch64 (test program staged). A native
aarch64 IGC build is in progress. No aarch64 SYCL/DPC++ compiler exists in
any repo we can reach, so the OpenCL path is the live route for now.

## Reproduce

Build script (all commands): `~/scratch/w88-neo-aarch64/build-stack.sh` on
the host above. Runtime wiring: `OCL_ICD_VENDORS=<prefix>/etc/OpenCL/vendors`
plus the prefix `LD_LIBRARY_PATH`. Device: `0001:05:00.0` bound to `xe`,
render node `/dev/dri/renderD129`.
