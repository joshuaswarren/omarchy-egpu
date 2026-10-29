#!/usr/bin/env bash
# host-inventory.sh: run on the host as root (for example: ssh HOST sudo bash -s < host-inventory.sh). Read-only inventory of the hand-staged 615 userspace tree and its firmware: type, mode, size, sha256, link target.
set -eu
R=/usr/lib/nvidia-egpu-615.78.08
cd "$R"
find . -mindepth 1 \( -type f -o -type l -o -type d \) | LC_ALL=C sort | while read -r p; do
  if [ -L "$p" ]; then echo "L $p -> $(readlink "$p")"
  elif [ -d "$p" ]; then echo "D $p $(stat -c %a "$p")"
  else echo "F $p $(stat -c '%a %s' "$p") $(sha256sum "$p" | cut -c1-64)"; fi
done
echo "== firmware"
ls -la /usr/lib/firmware/nvidia/615.78.08 2>&1
sha256sum /usr/lib/firmware/nvidia/615.78.08/* 2>&1
echo "== owners"
pacman -Qo "$R" 2>&1 | head -2
pacman -Qo /usr/lib/firmware/nvidia/615.78.08 2>&1 | head -2
cat "$R/share/glvnd/egl_vendor.d/10_nvidia.json" 2>&1
cat "$R/share/vulkan/icd.d/nvidia_icd.json" 2>&1
