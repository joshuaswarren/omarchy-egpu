#!/usr/bin/env bash
# migrate.sh : Runs on the host. Moves the hand-staged 615 userspace tree under pacman ownership (omarchy-nvidia-egpu-userspace-615), without --overwrite. It also upgrades an installed
# earlier revision of that package (the one that kept the firmware under usr/lib/firmware).
#   migrate.sh PKG                plan only: prints the collision inventory, the pacman hooks this transaction would trigger and every step; changes nothing; needs no root (default)
#   migrate.sh PKG --apply        does it, as root. Refuses unless /root/userspace615.GO exists (the operator's go, written by hand) and no process has a file of the tree open.
# PKG is a package file that tar can read (xz or zstd). Both modes STOP (exit 3) on: a package file that exists on the host with other bytes (DIFF), a host file that another package
# owns (pacman -Qqo), a missing lsof, python3 or readelf (the checker needs it; a plain readelf is linked as aarch64-linux-gnu-readelf), or a missing check-egl-profile.sh or
# hook_triggers.py next to this script. Apply stops before any change when one of those holds, so it cannot end half done.
# Steps (apply): 1 backup of both trees to a tar, extracted again into a scratch dir on the backup disk (not tmpfs) and checked against a sha256 manifest made from the live files;
#   2 remove the old add-on package omarchy-nvidia-egpu-vulkan-615 (its two files are in the new package); 3 move the remaining unowned, identical files into the backup's "moved" dir
#   (nothing is deleted); 4 pacman -U (no --overwrite) with every hook that watches a path of this transaction masked (see below); 5 compare every file with the package's own,
#   check the firmware link, and run check-egl-profile.sh on the live tree.
# Hooks: a pacman hook such as mkinitcpio's watches usr/lib/firmware/*. Installing a package file there once rebuilt a boot image and rewrote limine.conf. The package now keeps the firmware
#   in the profile tree and links it from its install script, but REMOVING the old revision's files under usr/lib/firmware would trigger the hook again. hook_triggers.py lists the hooks
#   that match the new package's paths and the installed packages' paths; apply masks exactly those with same-named links to /dev/null in a --hookdir for the transaction.
# Rollback: restore from the backup dir (printed), then pacman -Rdd the new package.
# MIGRATE_ROOT=DIR reads the host files under DIR instead of /; MIGRATE_HOOKDIRS="DIR ..." replaces the hook directories that are searched (tests; plan mode only).
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
[ -z "$R${MIGRATE_HOOKDIRS:-}" ] || [ "$MODE" = plan ] || { echo "REFUSE: MIGRATE_ROOT and MIGRATE_HOOKDIRS are for plan mode only" >&2; exit 2; }
[ "$MODE" != --apply ] || [ "$(id -u)" = 0 ] || { echo "REFUSE: --apply needs root" >&2; exit 2; }
tar -xf "$PKG" -C "$W"
( cd "$W" && find usr \( -type f -o -type l \) | LC_ALL=C sort ) > "$W/.files"
echo "package files: $(wc -l < "$W/.files")   backup dir (apply): $B"
# where a package file sits on the host: the package keeps the firmware in the profile tree, the host (and the driver) see it under usr/lib/firmware/nvidia/VERSION
hostpath() { case $1 in "${T#/}"/firmware/*) echo "${FW#/}/${1##*/}" ;; *) echo "$1" ;; esac; }
stops=0
command -v lsof > /dev/null || { echo "STOP: lsof is missing, so the open-file guard cannot run (install lsof)"; stops=1; }
command -v python3 > /dev/null || { echo "STOP: python3 is missing, so the hook check cannot run"; stops=1; }
[ -r "$HERE/check-egl-profile.sh" ] || { echo "STOP: check-egl-profile.sh is missing next to this script"; stops=1; }
[ -r "$HERE/hook_triggers.py" ] || { echo "STOP: hook_triggers.py is missing next to this script"; stops=1; }
# the checker calls aarch64-linux-gnu-readelf; a native aarch64 host only has readelf, so the shim is a link to it (inside the scratch dir, gone at exit)
if command -v aarch64-linux-gnu-readelf > /dev/null; then :
elif command -v readelf > /dev/null; then mkdir -p "$W/shim" && ln -s "$(command -v readelf)" "$W/shim/aarch64-linux-gnu-readelf"
else echo "STOP: neither aarch64-linux-gnu-readelf nor readelf is installed (binutils), so the profile checker cannot run"; stops=1; fi
same=0 new=0 diff=0 other=0
while read -r f; do
	hp=$(hostpath "$f")
	h="$R/$hp"
	if [ ! -e "$h" ] && [ ! -L "$h" ]; then new=$((new + 1)); echo "NEW   $f"; continue; fi
	if [ -L "$W/$f" ] && [ -L "$h" ] && [ "$(readlink "$W/$f")" = "$(readlink "$h")" ]; then same=$((same + 1))
	elif [ -f "$W/$f" ] && [ ! -L "$h" ] && cmp -s "$W/$f" "$h"; then same=$((same + 1))
	else diff=$((diff + 1)); echo "DIFF  $f"; fi
	owner=$(pacman -Qqo "/$hp" 2> /dev/null || true)
	if [ -n "$owner" ] && [ "$owner" != "$OLD" ] && [ "$owner" != "$NEW" ]; then other=$((other + 1)); echo "OWNED /$hp is owned by $owner"; fi
done < "$W/.files"
echo "collision inventory: SAME $same, NEW $new, DIFF $diff, owned by another package $other; owner of the tree dir: $(pacman -Qqo "$T" 2> /dev/null | tr '\n' ' ')"
[ "$diff" = 0 ] || { echo "STOP: DIFF files need a human decision"; stops=1; }
[ "$other" = 0 ] || { echo "STOP: files owned by another package: removing the add-on or replacing them would break that package"; stops=1; }
[ "$stops" = 0 ] || exit 3
pacman -Ql "$NEW" "$OLD" 2> /dev/null | awk '{print $2}' > "$W/installed.paths" || true
HD=()
for d in ${MIGRATE_HOOKDIRS:-}; do HD+=(--hookdir "$d"); done
python3 "$HERE/hook_triggers.py" "$PKG" --paths "$W/installed.paths" "${HD[@]}" > "$W/hooks.txt"
HK=()
if [ -s "$W/hooks.txt" ]; then
	mkdir "$W/mask"
	while read -r hk; do ln -s /dev/null "$W/mask/$hk"; done < "$W/hooks.txt"
	HK=(--hookdir "$W/mask")
fi
echo "pacman hooks that watch a path of this transaction (apply masks them): $(tr '\n' ' ' < "$W/hooks.txt")"
if [ "$MODE" != --apply ]; then
	echo "PLAN only. Apply would: back up $T and $FW to $B and check the backup after extracting it, pacman -Rdd $OLD, move the identical unowned files into $B/moved, pacman -U $PKG with the hooks above masked, compare every file, check the firmware link, run check-egl-profile.sh on the live tree."
	exit 0
fi
need=$(du -sb "$T" "$FW" | awk '{n+=$1} END {print n * 3}'); mkdir -p "$(dirname "$B")"
free=$(df --output=avail -B1 "$(dirname "$B")" | tail -1)
[ "$free" -gt "$need" ] || { echo "REFUSE: $(dirname "$B") has $free B free, the backup, its read-back copy and the moved files need about $need B" >&2; exit 4; }
[ -e /root/userspace615.GO ] || { echo "REFUSE: /root/userspace615.GO missing (the operator's go)" >&2; exit 4; }
if lsof +D "$T" 2> /dev/null | grep -q .; then echo "REFUSE: a process has a file of $T open" >&2; exit 4; fi
mkdir -p "$B/moved" "$B/verify"
tar -cpf "$B/trees.tar" -C / "${T#/}" "${FW#/}"
( cd / && find "${T#/}" "${FW#/}" -type f -exec sha256sum {} + ) | LC_ALL=C sort -k2 > "$B/manifest.sha256"
tar -xpf "$B/trees.tar" -C "$B/verify"
( cd "$B/verify" && sha256sum -c --quiet "$B/manifest.sha256" )
rm -r "$B/verify"
echo "backup verified from the extracted tar: $B ($(wc -l < "$B/manifest.sha256") files)"
pacman -Q "$OLD" > /dev/null 2>&1 && pacman -Rdd --noconfirm "${HK[@]}" "$OLD"
while read -r f; do
	hp=$(hostpath "$f")
	if { [ -e "/$hp" ] || [ -L "/$hp" ]; } && [ -z "$(pacman -Qqo "/$hp" 2> /dev/null || true)" ]; then mkdir -p "$B/moved/$(dirname "$hp")"; mv "/$hp" "$B/moved/$hp"; fi
done < "$W/.files"
pacman -U --noconfirm "${HK[@]}" "$PKG"
bad=0
while read -r f; do
	hp=$(hostpath "$f")
	if [ -L "$W/$f" ]; then [ "$(readlink "/$f")" = "$(readlink "$W/$f")" ] || { echo "BAD link $f"; bad=1; }
	else cmp -s "$W/$f" "/$f" || { echo "BAD file $f"; bad=1; }; fi
	[ "$hp" = "$f" ] || [ -L "$W/$f" ] || cmp -s "$W/$f" "/$hp" || { echo "BAD firmware path /$hp (the driver loads this one)"; bad=1; }
done < "$W/.files"
[ "$(readlink "$FW")" = ../../nvidia-egpu-$V/firmware ] || { echo "BAD firmware link $FW -> $(readlink "$FW" || echo none)"; bad=1; }
PATH="$W/shim:$PATH" bash "$HERE/check-egl-profile.sh" / "$V" || bad=1
[ "$bad" = 0 ] || { echo "VERIFY FAILED: roll back from $B" >&2; exit 5; }
echo "MIGRATED: $(pacman -Qi "$NEW" | sed -n 's/^Version *: //p'), all $(wc -l < "$W/.files") files verified, firmware link checked, profile checker passed, backup $B"
