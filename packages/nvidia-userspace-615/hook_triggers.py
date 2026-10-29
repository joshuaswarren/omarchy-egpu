#!/usr/bin/env python3
"""hook_triggers.py PKG [--paths FILE] [--hookdir DIR ...] : which pacman hooks would a transaction with this package trigger?

Reads the package's file list (any tar that Python can read) plus optional extra paths (one per line, for example `pacman -Ql` of the version being replaced, because removed files
trigger hooks too) and every `Type = Path` trigger of the hook files in the hook directories (default: /usr/share/libalpm/hooks and /etc/pacman.d/hooks). Prints the file name of every
hook with a matching target, one per line. Targets are matched like pacman does: fnmatch without a leading slash, and `*` also matches `/`.
A hook that watches `usr/lib/firmware/*` is the mkinitcpio hook: it rebuilds the boot images, which a package of this kind must never cause.
Exit 0 always; with --fail-on-match exit 1 when any hook matches (used by the test and the build gate).
"""
import argparse
import fnmatch
import os
import sys
import tarfile

DEFAULT_HOOKDIRS = ["/usr/share/libalpm/hooks", "/etc/pacman.d/hooks"]


def package_paths(path):
    with tarfile.open(path) as t:
        return [m.name for m in t if not m.name.startswith(".") and not m.isdir()]


def path_targets(hook_file):
    """The Target values of every [Trigger] section with Type = Path."""
    triggers, section = [], None
    with open(hook_file) as f:
        for raw in f:
            line = raw.strip()
            if line.startswith("["):
                section = {"type": None, "targets": []} if line == "[Trigger]" else None
                if section is not None:
                    triggers.append(section)
                continue
            if section is None or "=" not in line:
                continue
            key, value = (part.strip() for part in line.split("=", 1))
            if key == "Type":
                section["type"] = value
            elif key == "Target":
                section["targets"].append(value)
    return [t for s in triggers if s["type"] == "Path" for t in s["targets"]]


def matching_hooks(paths, hookdirs):
    found = set()
    for d in hookdirs:
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith(".hook"):
                continue
            targets = path_targets(os.path.join(d, name))
            if any(fnmatch.fnmatchcase(p.lstrip("/"), t) for p in paths for t in targets):
                found.add(name)
    return sorted(found)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pkg")
    ap.add_argument("--paths")
    ap.add_argument("--hookdir", action="append")
    ap.add_argument("--fail-on-match", action="store_true")
    a = ap.parse_args()
    paths = package_paths(a.pkg)
    if a.paths:
        with open(a.paths) as f:
            paths += [line.strip() for line in f if line.strip()]
    hooks = matching_hooks(paths, a.hookdir or DEFAULT_HOOKDIRS)
    for h in hooks:
        print(h)
    return 1 if hooks and a.fail_on_match else 0


if __name__ == "__main__":
    sys.exit(main())
