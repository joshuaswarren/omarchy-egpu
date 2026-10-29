#!/usr/bin/env python3
"""inventory.py PKG TREE_TXT : collision inventory of the userspace-615 package against the host's hand-staged tree (read-only, no host access).

PKG is the built .pkg.tar.xz. TREE_TXT is the output of host-inventory.sh (F/L/D lines for /usr/lib/nvidia-egpu-615.78.08, then the firmware sha256 lines).
Prints one class per package path: SAME (same bytes/target already on the host: safe to move aside and replace), DIFF (host file differs: needs a human look),
NEW (not on the host), and then HOST-ONLY (on the host, not in the package). Exit 1 if any DIFF or HOST-ONLY file exists.
"""
import hashlib
import sys
import tarfile

ROOT = "usr/lib/nvidia-egpu-615.78.08/"
FW = "usr/lib/firmware/nvidia/615.78.08/"


def host_inventory(path):
    host = {}
    in_fw = False
    for line in open(path):
        line = line.rstrip("\n")
        if line.startswith("== firmware"):
            in_fw = True
        if in_fw and line[:64].isalnum() and len(line) > 66 and line[64:66] == "  ":
            host[FW + line.rsplit("/", 1)[1]] = ("F", line[:64])
        elif line.startswith("F "):
            _, p, _mode, _size, sha = line.split()
            host[ROOT + p[2:]] = ("F", sha)
        elif line.startswith("L "):
            p, target = line[2:].split(" -> ")
            host[ROOT + p[2:]] = ("L", target)
    return host


def package_inventory(path):
    pkg = {}
    with tarfile.open(path) as t:
        for m in t:
            if m.name.startswith(".") or m.isdir():
                continue
            if m.issym():
                pkg[m.name] = ("L", m.linkname)
            elif m.isfile():
                h = hashlib.sha256()
                f = t.extractfile(m)
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
                pkg[m.name] = ("F", h.hexdigest())
    return pkg


def main():
    pkg = package_inventory(sys.argv[1])
    host = host_inventory(sys.argv[2])
    bad = 0
    for p in sorted(pkg):
        h = host.get(p)
        cls = "NEW" if h is None else "SAME" if h == pkg[p] else "DIFF"
        bad += cls == "DIFF"
        print(f"{cls:5} {p}" + (f"  pkg={pkg[p][1][:16]} host={h[1][:16]}" if cls == "DIFF" else ""))
    only = sorted(set(host) - set(pkg))
    for p in only:
        print(f"HOST-ONLY {p}")
    counts = {c: sum(1 for p in pkg if (host.get(p) is None and c == "NEW") or (host.get(p) == pkg[p] and c == "SAME")) for c in ("SAME", "NEW")}
    print(f"summary: package files {len(pkg)}, SAME {counts['SAME']}, NEW {counts['NEW']}, DIFF {bad}, HOST-ONLY {len(only)}")
    return 1 if bad or only else 0


if __name__ == "__main__":
    sys.exit(main())
