#!/usr/bin/env bash
# Failing-first regression for check-egl-profile.sh. Offline, needs aarch64-linux-gnu-gcc and readelf. One run: eighteen failing cases, one passing.
set -uo pipefail
cd "$(dirname "$0")" || exit 9
V=615.78.08
P=usr/lib/nvidia-egpu-$V
LIB=$P/lib/libEGL_nvidia.so.$V
MAN=$P/share/glvnd/egl_vendor.d/10_nvidia.json
T=$(mktemp -d)
trap 'chmod -R u+w "$T"; find "$T" -delete' EXIT
bad=0

# Fixture generated at test time: a stub shared library that carries only what the checker reads
# (SONAME libEGL_nvidia.so.615.78.08, NEEDED libnvidia-glsi.so.615.78.08). No NVIDIA binary is stored.
O=$T/overlay
G=$T/gen
mkdir -p "$G" "$O/$(dirname "$LIB")" "$O/$(dirname "$MAN")"
printf 'int glsi_stub(void) { return 0; }\n' >"$G/glsi.c"
printf 'int egl_stub(void) { return 0; }\n' >"$G/egl.c"
aarch64-linux-gnu-gcc -shared -o "$G/libnvidia-glsi.so.$V" "-Wl,-soname,libnvidia-glsi.so.$V" "$G/glsi.c" || exit 9
aarch64-linux-gnu-gcc -shared -o "$O/$LIB" "-Wl,-soname,libEGL_nvidia.so.$V" "$G/egl.c" -Wl,--no-as-needed "$G/libnvidia-glsi.so.$V" || exit 9
ln -s "libEGL_nvidia.so.$V" "$O/$P/lib/libEGL_nvidia.so.0"
printf '{"file_format_version":"1.0.0","ICD":{"library_path":"/usr/lib/nvidia-egpu-%s/lib/libEGL_nvidia.so.0"}}\n' "$V" >"$O/$MAN"
expect() { # name want(0|1) root [stderr-pattern]
    err=$(bash check-egl-profile.sh "$3" "$V" 2>&1 >/dev/null)
    got=$?
    if [ "$got" = "$2" ] && { [ -z "${4:-}" ] || printf '%s' "$err" | grep -q "$4"; }; then echo "ok   $1 (rc=$got)"; else echo "FAIL $1: rc=$got want=$2"; bad=1; fi
}
manifest() { # root json-text
    mkdir -p "$1/$(dirname "$MAN")"
    [ ! -e "$1/$MAN" ] || chmod u+w "$1/$MAN"
    printf '%s\n' "$2" >"$1/$MAN"
}

mkdir -p "$T/base/$P/lib"
expect "profile without manifest" 1 "$T/base" "glvnd manifest missing"

manifest "$T/old" '{"ICD":{"library_path":"/usr/lib/nvidia-egpu-595.112.07/lib/libEGL_nvidia.so.0"}}'
expect "manifest names the 595 library (missing)" 1 "$T/old"

mkdir -p "$T/nolib/$P/lib"
cp $O/$MAN "$T/nolib/$MAN" 2>/dev/null || { mkdir -p "$T/nolib/$(dirname "$MAN")"; cp $O/$MAN "$T/nolib/$MAN"; }
expect "manifest right, library missing" 1 "$T/nolib" "missing or not a regular file"

# a library that exists but NEEDS the glsi of another version: the real failure
mkdir -p "$T/glsi595/$P/lib"
cp $O/$MAN "$T/glsi595/$MAN" 2>/dev/null || { mkdir -p "$T/glsi595/$(dirname "$MAN")"; cp $O/$MAN "$T/glsi595/$MAN"; }
cp $O/$LIB "$T/glsi595/$LIB"
sed -i 's/libnvidia-glsi.so.615.78.08/libnvidia-glsi.so.595.78.08/' "$T/glsi595/$LIB"
ln -s "libEGL_nvidia.so.$V" "$T/glsi595/$P/lib/libEGL_nvidia.so.0"
expect "library exists but NEEDS glsi 595" 1 "$T/glsi595"

# manifest names another version's path and that file exists
mkdir -p "$T/otherver/usr/lib/nvidia-egpu-595.112.07/lib"
cp $O/$LIB "$T/otherver/usr/lib/nvidia-egpu-595.112.07/lib/libEGL_nvidia.so.$V"
manifest "$T/otherver" '{"ICD":{"library_path":"/usr/lib/nvidia-egpu-595.112.07/lib/libEGL_nvidia.so.615.78.08"}}'
expect "manifest names an existing library of another version" 1 "$T/otherver"

# path escape through ..
mkdir -p "$T/escape/usr/lib/other" "$T/escape/$P/lib"
cp $O/$LIB "$T/escape/usr/lib/other/"
manifest "$T/escape" '{"ICD":{"library_path":"/usr/lib/nvidia-egpu-615.78.08/lib/../../other/libEGL_nvidia.so.615.78.08"}}'
expect "library path escapes the profile with .." 1 "$T/escape"

# an absolute symlink would resolve against the host, not the package
mkdir -p "$T/abslink/$P/lib"
cp $O/$MAN "$T/abslink/$MAN" 2>/dev/null || { mkdir -p "$T/abslink/$(dirname "$MAN")"; cp $O/$MAN "$T/abslink/$MAN"; }
ln -s "$O/$LIB" "$T/abslink/$P/lib/libEGL_nvidia.so.0"
expect "absolute symlink" 1 "$T/abslink"

# an absolute link whose target also exists under the package would pass a naive join but resolve on the host
mkdir -p "$T/abslink2/$P/lib"
cp $O/$MAN "$T/abslink2/$MAN" 2>/dev/null || { mkdir -p "$T/abslink2/$(dirname "$MAN")"; cp $O/$MAN "$T/abslink2/$MAN"; }
cp $O/$LIB "$T/abslink2/$P/lib/libEGL_nvidia.so.$V"
ln -s "/libEGL_nvidia.so.$V" "$T/abslink2/$P/lib/libEGL_nvidia.so.0"
expect "absolute link with an in-package look-alike" 1 "$T/abslink2"

# manifest names the 615 .so.0 link, which points at a file named for another version
mkdir -p "$T/badname/$P/lib"
cp $O/$MAN "$T/badname/$MAN" 2>/dev/null || { mkdir -p "$T/badname/$(dirname "$MAN")"; cp $O/$MAN "$T/badname/$MAN"; }
cp $O/$LIB "$T/badname/$P/lib/libEGL_nvidia.so.595.112.07"
ln -s libEGL_nvidia.so.595.112.07 "$T/badname/$P/lib/libEGL_nvidia.so.0"
expect "link resolves to a file named for another version" 1 "$T/badname"

# two hops: a relative link to a file that is itself an absolute link out of the package
mkdir -p "$T/twohop/$P/lib"
cp $O/$MAN "$T/twohop/$MAN" 2>/dev/null || { mkdir -p "$T/twohop/$(dirname "$MAN")"; cp $O/$MAN "$T/twohop/$MAN"; }
ln -s "$O/$LIB" "$T/twohop/$P/lib/libEGL_nvidia.so.$V"
ln -s "libEGL_nvidia.so.$V" "$T/twohop/$P/lib/libEGL_nvidia.so.0"
expect "second hop is an absolute link" 1 "$T/twohop" "not another link"

# the profile lib directory is a link to a directory elsewhere
mkdir -p "$T/libdirlink/outside" "$T/libdirlink/$P"
cp $O/$LIB "$T/libdirlink/outside/"
cp $O/$MAN "$T/libdirlink/$MAN" 2>/dev/null || { mkdir -p "$T/libdirlink/$(dirname "$MAN")"; cp $O/$MAN "$T/libdirlink/$MAN"; }
ln -s "$T/libdirlink/outside" "$T/libdirlink/$P/lib"
ln -s "libEGL_nvidia.so.$V" "$T/libdirlink/outside/libEGL_nvidia.so.0"
expect "profile lib directory is a link" 1 "$T/libdirlink" "lib directory must not be a link"

# the profile directory itself is a link
mkdir -p "$T/profilelink/real/lib" "$T/profilelink/usr/lib"
cp $O/$LIB "$T/profilelink/real/lib/"
ln -s "libEGL_nvidia.so.$V" "$T/profilelink/real/lib/libEGL_nvidia.so.0"
mkdir -p "$T/profilelink/real/share/glvnd/egl_vendor.d"
cp $O/$MAN "$T/profilelink/real/share/glvnd/egl_vendor.d/"
ln -s "$T/profilelink/real" "$T/profilelink/$P"
expect "profile directory is a link" 1 "$T/profilelink" "profile directory must not be a link"

# a valid package tree, built in one place, so each case below breaks exactly one path component
full_profile() { # root
    mkdir -p "$1/$P/lib" "$1/$(dirname "$MAN")"
    cp $O/$LIB "$1/$P/lib/"
    ln -s "libEGL_nvidia.so.$V" "$1/$P/lib/libEGL_nvidia.so.0"
    cp $O/$MAN "$1/$MAN"
}

# the manifest file is a link to a manifest outside the package
full_profile "$T/mlink"
cp "$T/mlink/$MAN" "$T/mlink.manifest"
find "$T/mlink/$MAN" -delete
ln -s "$T/mlink.manifest" "$T/mlink/$MAN"
expect "manifest file is a link" 1 "$T/mlink" "path component is a link"

# the egl_vendor.d directory is a link
full_profile "$T/dlink"
mv "$T/dlink/$(dirname "$MAN")" "$T/dlink.vendor"
ln -s "$T/dlink.vendor" "$T/dlink/$(dirname "$MAN")"
expect "egl_vendor.d directory is a link" 1 "$T/dlink" "path component is a link"

# usr above the profile is a link
full_profile "$T/usrreal"
mkdir -p "$T/usrlink"
ln -s "$T/usrreal/usr" "$T/usrlink/usr"
expect "usr is a link" 1 "$T/usrlink" "path component is a link"

# a directory link below the lib directory: manifest path goes through lib/sub
full_profile "$T/subpath"
mkdir -p "$T/subpath.host"
mv "$T/subpath/$LIB" "$T/subpath.host/"
ln -s "$T/subpath.host" "$T/subpath/$P/lib/sub"
manifest "$T/subpath" '{"ICD":{"library_path":"/usr/lib/nvidia-egpu-615.78.08/lib/sub/libEGL_nvidia.so.615.78.08"}}'
expect "manifest path goes through a directory link under lib" 1 "$T/subpath" "directly in the profile lib directory"

# the .so.0 link goes through the same kind of directory link
full_profile "$T/sublink"
mkdir -p "$T/sublink.host"
mv "$T/sublink/$LIB" "$T/sublink.host/"
ln -s "$T/sublink.host" "$T/sublink/$P/lib/sub"
find "$T/sublink/$P/lib/libEGL_nvidia.so.0" -delete
ln -s "sub/libEGL_nvidia.so.$V" "$T/sublink/$P/lib/libEGL_nvidia.so.0"
expect ".so.0 link goes through a directory link under lib" 1 "$T/sublink" "must be a bare file name"

# two library_path entries: refuse instead of letting one win
manifest "$T/twoentries" '{"ICD":{"library_path":"/usr/lib/nvidia-egpu-595.112.07/lib/libEGL_nvidia.so.0","library_path":"/usr/lib/nvidia-egpu-615.78.08/lib/libEGL_nvidia.so.0"}}'
mkdir -p "$T/twoentries/$P/lib"
cp $O/$LIB "$T/twoentries/$P/lib/"
ln -s "libEGL_nvidia.so.$V" "$T/twoentries/$P/lib/libEGL_nvidia.so.0"
expect "two library_path entries" 1 "$T/twoentries" "exactly one library_path"

expect "generated 615 library and manifest" 0 "$O"
exit $bad
