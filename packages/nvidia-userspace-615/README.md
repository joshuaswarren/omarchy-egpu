# nvidia-userspace-615

Pacman package source for the NVIDIA 615.78.08 aarch64 userspace that the Thunderbolt eGPU profile uses on an Apple Silicon MacBook Pro running Omarchy.
The package name is `omarchy-nvidia-egpu-userspace-615`. It installs a profile-private tree and does not touch the system NVIDIA driver.

Status: source only. This directory has been built into a package. It has not been installed on a host by this repository, and the hardware compute proof that decides an install is a separate step.

## What the package installs

| Path | Content |
|---|---|
| `/usr/lib/nvidia-egpu-615.78.08/lib` | the 615.78.08 libraries (`libGLX_nvidia`, `libEGL_nvidia`, `libcuda`, `libnvidia-*`), with relative symlinks |
| `/usr/lib/nvidia-egpu-615.78.08/bin` | `nvidia-smi`, `nvidia-modprobe` |
| `/usr/lib/nvidia-egpu-615.78.08/share/vulkan/icd.d/nvidia_icd.json` | the Vulkan ICD file; `library_path` is the absolute path of the profile's `libGLX_nvidia.so.0` |
| `/usr/lib/nvidia-egpu-615.78.08/share/glvnd/egl_vendor.d/10_nvidia.json` | a profile-private glvnd EGL manifest (not the system one) |
| `/usr/lib/nvidia-egpu-615.78.08/vulkan-env.sh` | sourceable file that sets `LD_LIBRARY_PATH`, `VK_DRIVER_FILES` and `__EGL_VENDOR_LIBRARY_FILENAMES` for one run |
| `/usr/lib/firmware/nvidia/615.78.08/` | `gsp_ga10x.bin`, `gsp_tu10x.bin`, `ucodes_ga10x.bin`, `ucodes_tu10x.bin` |

Nothing goes under `/etc` or `/usr/share/glvnd`. A process uses the tree only when it sources `vulkan-env.sh`.

## Why the ICD path is absolute

The `.run` file writes `libGLX_nvidia.so.0` as a bare name. A bare name resolves to the system library when `LD_LIBRARY_PATH` is not set, so a Vulkan run can load a 595 library under a 615 driver. The `PKGBUILD` rewrites the name to the profile path.

## Build

The source is the official NVIDIA `.run` file, pinned by sha256 in the `PKGBUILD`. `makepkg` checks the hash. The `PKGBUILD` extracts the `.run` with `-x` and never runs it as an installer.

1. Put `NVIDIA-Linux-aarch64-615.78.08.run` next to the `PKGBUILD`.
2. Run `makepkg -C -f --nodeps` on an aarch64 Arch system. `readelf` must be available as `aarch64-linux-gnu-readelf`; on an aarch64 host a symlink to `readelf` is enough.
3. The build gate `check-egl-profile.sh` runs at the end of `package()` on the finished tree. A package whose EGL manifest does not name the profile's own `libEGL_nvidia` for this version does not build.

The package hash changes with each build because the build date and file times are in the metadata. The file contents do not change.
The `PKGBUILD` sets `PKGEXT='.pkg.tar.xz'`, so the package is an xz tarball that `inventory.py` (Python `tarfile`) and `migrate.sh` (`tar`) both read.

## Migration of a hand-staged tree

Hosts that already hold a hand-copied tree need a migration, because pacman refuses to overwrite unowned files.

- `host-inventory.sh` writes a read-only inventory of the host tree (type, mode, size, sha256).
- `inventory.py PKG INVENTORY` compares that inventory with the package. A file is `SAME`, `NEW`, `DIFF` or `HOST-ONLY`. The script exits 1 on any `DIFF` or `HOST-ONLY` file.
- `migrate.sh PKG` prints the plan and changes nothing. It stops (exit 3) when a package file exists on the host with other bytes, when a host file belongs to another package, when `lsof` is missing, or when `check-egl-profile.sh` is missing next to it. `--apply` runs the same checks before any change.
- `migrate.sh PKG --apply` needs root and the file `/root/userspace615.GO`. It writes a tar backup of both trees, extracts that tar again and checks it against a sha256 manifest, moves the identical unowned files aside (it deletes nothing), runs `pacman -U` without `--overwrite`, compares every file with the package, and runs `check-egl-profile.sh` on the live tree.

## Tests

- `python3 -m unittest discover -s tests` runs the inventory and migration-plan tests. They use temporary roots and a stub `pacman`; they do not migrate a host.
- `bash test-check-egl.sh` and `bash mutate-check-egl.sh` test the gate. They build a stub library at test time, so no NVIDIA file is stored here. They need `aarch64-linux-gnu-gcc` and `aarch64-linux-gnu-readelf` (Debian and Ubuntu: `gcc-aarch64-linux-gnu`, `binutils-aarch64-linux-gnu`, `libc6-dev-arm64-cross`) and exit 9 without them.
