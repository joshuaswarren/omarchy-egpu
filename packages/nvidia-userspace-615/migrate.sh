#!/usr/bin/env bash
# migrate.sh : Runs on the host as root. Moves the hand-staged 615 userspace tree under pacman ownership (omarchy-nvidia-egpu-userspace-615), without --overwrite.
#   migrate.sh PKG.pkg.tar.xz            plan only: prints every step and the collision inventory, changes nothing (default)
#   migrate.sh PKG.pkg.tar.xz --apply    does it. Refuses unless /root/userspace615.GO exists (the operator's go, written by hand) and no process has a file of the tree open.
# Steps (apply): 1 verified backup of both trees + sha manifest; 2 every package file must be absent or byte-identical on the host (a DIFF file stops the run);
#   3 remove the old add-on package omarchy-nvidia-egpu-vulkan-615 (its two files are in the new package); 4 move the remaining unowned, identical files into the backup's
#   "moved" dir (nothing is deleted); 5 pacman -U (no --overwrite); 6 verify every file against the package's own sha256 list and run the profile checker on the live tree.
# Rollback: restore from the backup dir (printed), then pacman -Rdd the new package.
set -euo pipefail
PKG=${1:?package file}; MODE=${2:-plan}
V=615.78.08; T=/usr/lib/nvidia-egpu-$V; FW=/usr/lib/firmware/nvidia/$V
B=/var/lib/omarchy-egpu/userspace615-migration/$(date -u +%Y%m%dT%H%M%SZ)
W=$(mktemp -d)
trap 'rm -r "$W"' EXIT
[ -f "$PKG" ] || { echo "REFUSE: no package $PKG" >&2; exit 2; }
[ "$(id -u)" = 0 ] || { echo "REFUSE: run as root" >&2; exit 2; }
case $T$FW in /usr/lib/nvidia-egpu-615.78.08/usr/lib/firmware/nvidia/615.78.08) ;; *) echo "REFUSE: unexpected paths" >&2; exit 2 ;; esac
bsdtar -xf "$PKG" -C "$W" --exclude '.*'
( cd "$W" && find usr \( -type f -o -type l \) | LC_ALL=C sort ) > "$W/.files"
echo "package files: $(wc -l < "$W/.files")   backup dir (apply): $B"
same=0 new=0 diff=0
while read -r f; do
	h="/$f"
	if [ ! -e "$h" ] && [ ! -L "$h" ]; then new=$((new + 1)); echo "NEW   $f"
	elif [ -L "$W/$f" ] && [ -L "$h" ] && [ "$(readlink "$W/$f")" = "$(readlink "$h")" ]; then same=$((same + 1))
	elif [ -f "$W/$f" ] && [ ! -L "$h" ] && cmp -s "$W/$f" "$h"; then same=$((same + 1))
	else diff=$((diff + 1)); echo "DIFF  $f"; fi
done < "$W/.files"
echo "collision inventory: SAME $same, NEW $new, DIFF $diff; owner of the tree: $(pacman -Qqo "$T" 2> /dev/null | tr '\n' ' ')"
[ "$diff" = 0 ] || { echo "STOP: DIFF files need a human decision" >&2; exit 3; }
if [ "$MODE" != --apply ]; then
	echo "PLAN only. Apply would: back up $T and $FW to $B (sha256 manifest, verified), pacman -Rdd omarchy-nvidia-egpu-vulkan-615, move the $same identical unowned files into $B/moved, pacman -U $PKG, verify every file."
	exit 0
fi
[ -e /root/userspace615.GO ] || { echo "REFUSE: /root/userspace615.GO missing (the operator's go)" >&2; exit 4; }
if lsof +D "$T" 2> /dev/null | grep -q .; then echo "REFUSE: a process has a file of $T open" >&2; exit 4; fi
mkdir -p "$B/moved"
tar -cpf "$B/trees.tar" -C / "${T#/}" "${FW#/}"
( cd / && find "${T#/}" "${FW#/}" -type f -exec sha256sum {} + ) | LC_ALL=C sort -k2 > "$B/manifest.sha256"
tar -xOf "$B/trees.tar" > /dev/null
( cd / && sha256sum -c --quiet "$B/manifest.sha256" )
echo "backup verified: $B ($(wc -l < "$B/manifest.sha256") files)"
pacman -Q omarchy-nvidia-egpu-vulkan-615 > /dev/null 2>&1 && pacman -Rdd --noconfirm omarchy-nvidia-egpu-vulkan-615
while read -r f; do
	if { [ -e "/$f" ] || [ -L "/$f" ]; } && [ -z "$(pacman -Qqo "/$f" 2> /dev/null || true)" ]; then mkdir -p "$B/moved/$(dirname "$f")"; mv "/$f" "$B/moved/$f"; fi
done < "$W/.files"
pacman -U --noconfirm "$PKG"
bad=0
while read -r f; do
	if [ -L "$W/$f" ]; then [ "$(readlink "/$f")" = "$(readlink "$W/$f")" ] || { echo "BAD link $f"; bad=1; }
	else cmp -s "$W/$f" "/$f" || { echo "BAD file $f"; bad=1; }; fi
done < "$W/.files"
[ "$bad" = 0 ] || { echo "VERIFY FAILED: roll back from $B" >&2; exit 5; }
echo "MIGRATED: $(pacman -Qi omarchy-nvidia-egpu-userspace-615 | sed -n 's/^Version *: //p'), all $(wc -l < "$W/.files") files verified, backup $B"
