#!/usr/bin/env bash
# Offline package check, no hardware. Usage: check-egl-profile.sh ROOT VERSION
# ROOT is a package tree (or overlay merged on a package tree) containing usr/lib/nvidia-egpu-VERSION.
# Fails when the profile's glvnd EGL manifest is missing, names a library that is not in the profile,
# escapes the profile with '..', resolves through an absolute or second link (host filesystem), or names a
# library built for another driver version (the 595-under-615 mismatch that broke Vulkan on the 5060 Ti).
# The manifest must hold exactly one "library_path" with its value on the same line.
# Only the libnvidia-glsi NEEDED entry is compared; a new NEEDED libnvidia-* would not be caught.
set -euo pipefail
ROOT=${1:?package root}
V=${2:?driver version}
P=$ROOT/usr/lib/nvidia-egpu-$V
J=$P/share/glvnd/egl_vendor.d/10_nvidia.json
fail() { echo "FAIL: $*" >&2; exit 1; }
[ ! -L "$P" ] || fail "profile directory must not be a link"
for c in "$ROOT/usr" "$ROOT/usr/lib" "$P/share" "$P/share/glvnd" "$P/share/glvnd/egl_vendor.d" "$J"; do [ ! -L "$c" ] || fail "path component is a link: $c"; done
[ -f "$J" ] || fail "profile glvnd manifest missing: $J"
[ "$(grep -o '"library_path"' "$J" | wc -l)" = 1 ] || fail "manifest must hold exactly one library_path"
LIB=$(sed -n 's/.*"library_path"[^"]*"\([^"]*\)".*/\1/p' "$J")
[ -n "$LIB" ] || fail "manifest has no library_path"
case $LIB in /usr/lib/nvidia-egpu-"$V"/lib/*) ;; *) fail "manifest names a library outside the $V profile: $LIB" ;; esac
case $LIB in /usr/lib/nvidia-egpu-"$V"/lib/*/*) fail "manifest library must sit directly in the profile lib directory: $LIB" ;; esac
[ ! -L "$P/lib" ] || fail "profile lib directory must not be a link"
F=$ROOT$LIB
LINK=$(readlink "$F" || true)
case $LINK in */*) fail "library link must be a bare file name: $LINK" ;; esac
REAL=$F
[ -z "$LINK" ] || REAL=$(dirname "$F")/$LINK
[ ! -L "$REAL" ] || fail "library link must point at a real file, not another link: $LIB"
[ -f "$REAL" ] || fail "manifest library is missing or not a regular file in the package: $LIB"
case $(basename "$REAL") in libEGL_nvidia.so."$V") ;; *) fail "manifest library is not libEGL_nvidia.so.$V: $(basename "$REAL")" ;; esac
NEED=$(aarch64-linux-gnu-readelf -d "$REAL" | sed -n 's/.*NEEDED.*\[\(libnvidia-glsi[^]]*\)\].*/\1/p')
[ "$NEED" = "libnvidia-glsi.so.$V" ] || fail "EGL library needs '$NEED', expected libnvidia-glsi.so.$V"
[ -e "$P/lib/libnvidia-glsi.so.$V" ] || echo "NOTE: glsi not in this tree (overlay only); the base package supplies it"
echo "PASS: $LIB -> $(basename "$REAL")"
