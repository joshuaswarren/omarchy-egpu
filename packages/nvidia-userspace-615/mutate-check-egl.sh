#!/usr/bin/env bash
# Mutation run for check-egl-profile.sh: delete each check in a temp copy, the test must then fail.
set -uo pipefail
cd "$(dirname "$0")" || exit 9
T=$(mktemp -d)
trap 'chmod -R u+w "$T"; find "$T" -delete' EXIT
base=$(bash test-check-egl.sh | grep -c '^ok')
echo "baseline ok=$base"
mutate() { # name sed-expression
    mkdir -p "$T/$1"
    cp -a test-check-egl.sh "$T/$1/"
    chmod -R u+w "$T/$1"
    sed "$2" check-egl-profile.sh >"$T/$1/check-egl-profile.sh"
    ok=$(bash "$T/$1/test-check-egl.sh" 2>&1 | grep -c '^ok')
    failed=$(bash "$T/$1/test-check-egl.sh" 2>&1 | grep '^FAIL' | cut -c1-80 | tr '\n' ';')
    echo "mutant $1: ok=$ok (killed: ${failed:-NO})"
}
mutate no-manifest-check '/profile glvnd manifest missing/d'
mutate no-prefix-check '/outside the \$V profile/d'
mutate no-regular-check '/missing or not a regular file/d'
mutate no-name-check '/is not libEGL_nvidia.so/d'
mutate no-needed-check '/EGL library needs/d'
mutate no-twohop-check '/not another link/d'
mutate no-libdir-link-check '/lib directory must not be a link/d'
mutate no-profiledir-link-check '/profile directory must not be a link/d'
mutate no-single-entry-check '/exactly one library_path/d'
mutate no-component-link-check '/path component is a link/d'
mutate no-subpath-check '/must sit directly in the profile lib directory/d'
mutate no-bare-link-check '/must be a bare file name/d'
