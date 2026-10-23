# Building Mesa NVK userspace for the RTX 5060 Ti on Apple Silicon

How to build Mesa's NVK Vulkan driver from source, natively, on a 16 KiB-page
aarch64 Omarchy host for this card, and how to verify the built ICD without
touching the kernel driver state. The kernel-side route, firmware sets and the
GPU-bind probe live in [setup.md](setup.md); nothing here proves a GPU run.

**Status 2026-10-23:** NVK userspace for the GB206 **BUILT** on a 16-inch M1
Max (Mesa 26.2.4, release build) and the staged ICD passes loader init on the
16 KiB kernel: `vkCreateInstance` returns `VK_SUCCESS`, physical-device
enumeration finds zero GPUs because no nouveau driver is bound yet (expected;
see the last section). No inference number exists for this card on any Apple
Silicon host.

## Why build from source

Arch Linux ARM ships NVK as `vulkan-nouveau` for aarch64, so a package is a
valid path. We build instead because:

- **Version match.** The build pins to the same Mesa release the host already
  runs for its integrated GPU (26.2.4 at the time of writing), so a later
  like-for-like against other Mesa Vulkan drivers (honeykrisp, ANV) is
  userspace-generation-matched.
- **Toolchain proof.** The first NVK build on a 16 KiB-page aarch64 host is
  itself a result; the release notes claim support, nobody had built it here.
- **No system collision.** Everything installs under a stage prefix. The
  system Mesa and the integrated GPU's ICD are never touched.

## Requirements (verified against Mesa 26.2.4)

| Requirement | Version | Notes |
|---|---|---|
| rustc | >= 1.85 | enforced by `meson.build` |
| bindgen | >= 0.71.1 | 0.72.0 is rejected as buggy |
| cbindgen | >= 0.28 | required by `src/nouveau/nil/meson.build`; easy to miss |
| meson, ninja, clang | current | LLVM only for the internal `mesa_clc` tool (`-Dllvm=auto`) |
| libdrm, python-mako, python-yaml | current | normal Omarchy build deps |

No external SPIRV-Tools and no LLVM dependency of NVK itself: the shader
compiler (`nak`) is Rust, and NVK's OpenCL kernels build with Mesa's own
`mesa_clc`.

## A rustc trap on Arch ARM (measured 2026-10-23)

`rust` can be left broken by a partial upgrade: rust 1.98.1 links
`libLLVM.so.22.1` while `llvm-libs` 23.1.1 is installed, so every rustc
invocation dies before compiling anything. The repo database can also list a
rust package the mirrors still 404 (db-ahead-of-mirror skew). The clean fix
needs no system package - a self-contained rustup tree next to the build:

```bash
export RUSTUP_HOME=$HOME/scratch/rustup CARGO_HOME=$HOME/scratch/cargo
export PATH=$CARGO_HOME/bin:$PATH
curl -s -o /tmp/rustup-init \
  https://static.rust-lang.org/rustup/dist/aarch64-unknown-linux-gnu/rustup-init
chmod +x /tmp/rustup-init
/tmp/rustup-init -y --profile minimal --default-toolchain stable --no-modify-path
cargo install --locked cbindgen    # nil needs it; the system may not have it
```

## Build

```bash
MESA=$HOME/scratch/mesa-26.2.4            # https://archive.mesa3d.org/ tarball
BUILD=$HOME/scratch/build-nvk
PREFIX=$HOME/scratch/nvk-prefix
meson setup "$BUILD" "$MESA" \
  -Dvulkan-drivers=nouveau \
  -Dgallium-drivers= \
  -Dplatforms= \
  -Dglx=disabled \
  -Dllvm=auto \
  -Dbuildtype=release \
  -Dprefix="$PREFIX"
ninja -C "$BUILD" -j8
meson install -C "$BUILD"
```

An empty `-Dgallium-drivers=` with `vulkan-drivers=nouveau` gives an
NVK-only build. Keep the staging prefix: replacing the system Mesa or its
ICDs is not a supported state on these hosts.

## Verify without a GPU

Mesa installs the ICD manifest as
`$PREFIX/share/vulkan/icd.d/nouveau_icd.aarch64.json` (arch-suffixed) with an
absolute `library_path` already set. Check the library is AArch64, then point
the loader at that one json and nothing else:

```bash
readelf -h "$PREFIX"/lib/libvulkan_nouveau.so | grep -E 'Class|Machine'
VK_DRIVER_FILES="$PREFIX/share/vulkan/icd.d/nouveau_icd.aarch64.json" \
  vulkaninfo --summary
```

Pass, with no nouveau driver bound to the card:

- the loader finds the ICD and creates the instance, and
- `vkEnumeratePhysicalDevices` fails with `ERROR_INITIALIZATION_FAILED`
  ("Failed to detect any valid GPUs"), `vulkaninfo` exiting 1.

That failure at enumeration - not at instance creation - is the userspace
half working on a 16 KiB arm64 host. A raw `vkCreateInstance` check
(`rc = 0, VK_SUCCESS`) is a cleaner second signal. "Failed to load ICD",
missing-symbol errors or a crash at `vkCreateInstance` are the failure
signals; fix before anything else. For contrast, the proprietary NVIDIA ICD
on these hosts fails earlier, inside `vkCreateInstance` itself.

Measured on a 16-inch M1 Max (10 CPU), 2026-10-23, Mesa 26.2.4 tarball
release build: 1247 ninja targets, toolchain rust 1.99.1 (rustup minimal),
bindgen 0.73.2, cbindgen via cargo, clang 23.1.1, meson 1.12.1, ninja 1.13.2.
The full script - cbindgen install, configure, compile, install - ran in
59 s wall at 8 jobs only because ccache had the shared core objects from
earlier Mesa builds on the host; treat that as a warm-cache number, not a
cold-tree build time. Staged install footprint: 22 MB
`libvulkan_nouveau.so` (sha256 `de2c64cd…40664`), 333 MB build tree,
932 MB total including the rustup/cargo trees. On-disk evidence and the probe
transcripts live in the private lab notebook.

## The rest of the path to a device

The userspace half is the easy half. A real `vulkaninfo` entry for this card
additionally needs, in [setup.md](setup.md)'s terms:

1. a nouveau module whose GSP radix3 firmware page table is correct at
   16 KiB pages (upstream sizes GSP tables in 4 KiB units), plus non-posted
   BAR mappings behind the Apple tunnel;
2. the three GSP-RM 570.144 firmware files under
   `/usr/lib/firmware/nvidia/gb206/gsp/`;
3. `modprobe nouveau` with the NVIDIA-open modules unloaded - one route per
   card - then the `VK_DRIVER_FILES` probe from setup.md, which must show the
   RTX 5060 Ti with clean kernel logs before any inference claim.

Vulkan compute facts relevant to inference on this chip, from the 26.2.4
source: NVK advertises Vulkan 1.4 on Turing and later including consumer
Blackwell; `VK_KHR_cooperative_matrix` is advertised with
`robustBufferAccess = false` (FP16 shapes capped at 16x16x16, and the INT8
8x8x16 shape is disabled on Blackwell); subgroup size is fixed at 32, so a
64-wide-group assumption from the proprietary driver does not transfer.
llama.cpp's Vulkan backend uses plain compute shaders with subgroup
reductions, so it needs none of the capped paths; treat all of the above as
source-reading facts until this card runs. The benchmark recipe is
[recipes/llama-cpp-vulkan.md](../../recipes/llama-cpp-vulkan.md) with
`VK_DRIVER_FILES` pointing at the staged ICD.
