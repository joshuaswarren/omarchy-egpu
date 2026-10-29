#!/usr/bin/env bash
# migrate.sh : Runs on the host. Moves the hand-staged 615 userspace tree under pacman ownership (omarchy-nvidia-egpu-userspace-615), without --overwrite.
#   migrate.sh PKG                plan only: prints the collision inventory and every step, changes nothing, needs no root (default)
#   migrate.sh PKG --apply        does it, as root. Refuses unless /root/userspace615.GO exists (the operator's go, written by hand) and no process has a file of the tree open.
# PKG is a package file that tar can read (xz or zstd). Both modes STOP (exit 3) on: a package file that exists on the host with other bytes (DIFF), a host file that another package
# owns (pacman -Qqo), a missing lsof, or a missing check-egl-profile.sh next to this script. Apply stops before any change when one of those holds, so it cannot end half done.
# Steps (apply): 1 backup of both trees to a tar, extracted again into a scratch dir and checked against a sha256 manifest made from the live files; 2 remove the old add-on package
#   omarchy-nvidia-egpu-vulkan-615 (its two files are in the new package); 3 move the remaining unowned, identical files into the backup's "moved" dir (nothing is deleted);
#   4 pacman -U (no --overwrite); 5 compare every file with the package's own and run check-egl-profile.sh on the live tree.
# Rollback: restore from the backup dir (printed), then pacman -Rdd the new package.
# MIGRATE_ROOT=DIR reads the host files under DIR instead of / (tests; plan mode only).
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
PKG=${1:?package file}; MODE=${2:-plan}
R=${MIGRATE_ROOT:-}
V=615.78.08; T=/usr/lib/nvidia-egpu-$V; FW=/usr/lib/firmware/nvidia/$V
OLD=omarchy-nvidia-egpu-vulkan-615; NEW=omarchy-nvidia-egpu-userspace-615
B=/var/lib/omarchy-egpu/userspace615-migration/$(date -u +%Y%m%dT%H%M%SZ)
W=$(mktemp -d)
trap 'rm -r "$W"' EXIT
[ -f "$PKG" ] || { echo "REFUSE: no package $PKG" >&2; exit 2; }
case $MODE in plan | --apply) ;; *) echo "REFUSE: mode must be empty or --apply" >&2; exit 2 ;; esac
[ -z "$R" ] || [ "$MODE" = plan ] || { echo "REFUSE: MIGRATE_ROOT is for plan mode only" >&2; exit 2; }
[ "$MODE" != --apply ] || [ "$(id -u)" = 0 ] || { echo "REFUSE: --apply needs root" >&2; exit 2; }
tar -xf "$PKG" -C "$W"
( cd "$W" && find usr \( -type f -o -type l \) | LC_ALL=C sort ) > "$W/.files"
echo "package files: $(wc -l < "$W/.files")   backup dir (apply): $B"
stops=0
command -v lsof > /dev/null || { echo "STOP: lsof is missing, so the open-file guard cannot run (install lsof)"; stops=1; }
[ -r "$HERE/check-egl-profile.sh" ] || { echo "STOP: check-egl-profile.sh is missing next to this script"; stops=1; }
same=0 new=0 diff=0 other=0
while read -r f; do
	h="$R/$f"
	if [ ! -e "$h" ] && [ ! -L "$h" ]; then new=$((new + 1)); echo "NEW   $f"; continue; fi
	if [ -L "$W/$f" ] && [ -L "$h" ] && [ "$(readlink "$W/$f")" = "$(readlink "$h")" ]; then same=$((same + 1))
	elif [ -f "$W/$f" ] && [ ! -L "$h" ] && cmp -s "$W/$f" "$h"; then same=$((same + 1))
	else diff=$((diff + 1)); echo "DIFF  $f"; fi
	owner=$(pacman -Qqo "/$f" 2> /dev/null || true)
	if [ -n "$owner" ] && [ "$owner" != "$OLD" ] && [ "$owner" != "$NEW" ]; then other=$((other + 1)); echo "OWNED /$f is owned by $owner"; fi
done < "$W/.files"
echo "collision inventory: SAME $same, NEW $new, DIFF $diff, owned by another package $other; owner of the tree dir: $(pacman -Qqo "$T" 2> /dev/null | tr '\n' ' ')"
[ "$diff" = 0 ] || { echo "STOP: DIFF files need a human decision"; stops=1; }
[ "$other" = 0 ] || { echo "STOP: files owned by another package: removing the add-on or replacing them would break that package"; stops=1; }
[ "$stops" = 0 ] || exit 3
if [ "$MODE" != --apply ]; then
	echo "PLAN only. Apply would: back up $T and $FW to $B and check the backup after extracting it, pacman -Rdd $OLD, move the $same identical unowned files into $B/moved, pacman -U $PKG, compare every file, run check-egl-profile.sh on the live tree."
	exit 0
fi
[ -e /root/userspace615.GO ] || { echo "REFUSE: /root/userspace615.GO missing (the operator's go)" >&2; exit 4; }
if lsof +D "$T" 2> /dev/null | grep -q .; then echo "REFUSE: a process has a file of $T open" >&2; exit 4; fi
mkdir -p "$B/moved" "$W/verify"
tar -cpf "$B/trees.tar" -C / "${T#/}" "${FW#/}"
( cd / && find "${T#/}" "${FW#/}" -type f -exec sha256sum {} + ) | LC_ALL=C sort -k2 > "$B/manifest.sha256"
tar -xpf "$B/trees.tar" -C "$W/verify"
( cd "$W/verify" && sha256sum -c --quiet "$B/manifest.sha256" )
echo "backup verified from the extracted tar: $B ($(wc -l < "$B/manifest.sha256") files)"
pacman -Q "$OLD" > /dev/null 2>&1 && pacman -Rdd --noconfirm "$OLD"
while read -r f; do
	if { [ -e "/$f" ] || [ -L "/$f" ]; } && [ -z "$(pacman -Qqo "/$f" 2> /dev/null || true)" ]; then mkdir -p "$B/moved/$(dirname "$f")"; mv "/$f" "$B/moved/$f"; fi
done < "$W/.files"
pacman -U --noconfirm "$PKG"
bad=0
while read -r f; do
	if [ -L "$W/$f" ]; then [ "$(readlink "/$f")" = "$(readlink "$W/$f")" ] || { echo "BAD link $f"; bad=1; }
	else cmp -s "$W/$f" "/$f" || { echo "BAD file $f"; bad=1; }; fi
done < "$W/.files"
bash "$HERE/check-egl-profile.sh" / "$V" || bad=1
[ "$bad" = 0 ] || { echo "VERIFY FAILED: roll back from $B" >&2; exit 5; }
echo "MIGRATED: $(pacman -Qi "$NEW" | sed -n 's/^Version *: //p'), all $(wc -l < "$W/.files") files verified, profile checker passed, backup $B"
