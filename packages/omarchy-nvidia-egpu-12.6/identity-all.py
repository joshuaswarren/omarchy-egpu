#!/usr/bin/env python3
"""Runs ON jw16 (stock-DT boot, egpu kernel). Generalises identity-nowrite.sh to every device under root port 0001:00:00.0.

Bus address upper 32 bits (SRC_HI, usually 0x8) -> the CPU upper dword the
active root port's own DT "ranges" maps PCI pref space to (DST_HI: 0x8,
0xc, 0x10, 0x14, ... per port), on every enabled prefetchable bridge window,
and on every 64-bit prefetchable BAR of every endpoint, so that bus addresses
equal the CPU addresses the Apple root port needs. Endpoint memory decoding
is switched off while the window and BAR registers change and restored
afterwards. Reversible by reboot.

The dwords are read from the root port's own pcie@ DT node, so the same
script is correct no matter which USB-C port the tunnel lands on; the old
hardcoded 0x8 -> 0x10 only matched USB-C Right (pcie@f30000000).

usage: identity-all.py --dry | --go
"""
import glob
import struct
import subprocess
import sys
from pathlib import Path

ROOT = "0001:00:00.0"
GO = "--go" in sys.argv


def parse_ranges(data):
    """Return (pci_hi, cpu_hi) of the 64-bit prefetchable entry in a DT
    "ranges" blob (28-byte records: 3 PCI + 2 CPU + 2 size cells)."""
    for off in range(0, len(data), 28):
        flags, pci_hi, _pci_lo, cpu_hi, _cpu_lo, _sz_hi, _sz_lo = struct.unpack(
            ">7I", data[off:off + 28])
        if flags == 0x43000000:
            return pci_hi, cpu_hi
    raise RuntimeError("no 64-bit pref range in ranges blob")


def root_pref64_dwords(ranges_path=None):
    """Return (pci_hi, cpu_hi) of the 64-bit prefetchable window of the
    pcie@ node that owns ROOT, read from its DT "ranges" property."""
    if ranges_path is None:
        # /sys/bus/pci/devices/0001:00:00.0 -> .../b30000000.pcie/pci0001:00/0001:00:00.0
        rc_dir = Path("/sys/bus/pci/devices", ROOT).resolve().parents[1]
        ranges_path = rc_dir / "of_node" / "ranges"
        if not ranges_path.exists():
            rc_node = "pcie@" + rc_dir.name.split(".")[0]
            hits = glob.glob(f"/proc/device-tree/soc/usb4-pcie-tunnel-*/{rc_node}/ranges")
            if not hits:
                raise RuntimeError(f"no ranges DT node for {rc_dir}")
            ranges_path = Path(hits[0])
    return parse_ranges(Path(ranges_path).read_bytes())


def run(*a):
    return subprocess.run(a, check=True, capture_output=True, text=True).stdout.strip()


def setpci(dev, *args):
    cmd = ["sudo", "-n", "setpci", "-s", dev, *args]
    if GO:
        subprocess.run(cmd, check=True)
    else:
        print("DRY", " ".join(cmd))


def getpci(dev, reg):
    return int(run("sudo", "-n", "setpci", "-s", dev, reg), 16)


def main():
    src_hi, dst_hi = root_pref64_dwords()
    print(f"{ROOT}: 64-bit pref window PCI {src_hi:#x} -> CPU {dst_hi:#x}")
    if src_hi == dst_hi:
        print("already identity-mapped; nothing to write")
        return

    devs = [l.split()[0] for l in run("lspci", "-D").splitlines() if l.startswith("0001:")]
    devs = [d for d in devs if d != ROOT]
    is_bridge = {}
    for d in devs:
        hdr = getpci(d, "HEADER_TYPE.b") & 0x7F
        is_bridge[d] = hdr == 1

    saved = {}
    for d in devs:
        saved[d] = getpci(d, "COMMAND.w")
    for d in devs:
        if saved[d] & 0x2:
            setpci(d, "COMMAND=0x0:0x2")

    for b in [ROOT] + [d for d in devs if is_bridge[d]]:
        base = getpci(b, "PREF_MEMORY_BASE.w")
        limit = getpci(b, "PREF_MEMORY_LIMIT.w")
        if (base & 0xFFF0) > (limit & 0xFFF0):
            continue
        bu = getpci(b, "PREF_BASE_UPPER32")
        lu = getpci(b, "PREF_LIMIT_UPPER32")
        if bu == src_hi and lu == src_hi:
            print(f"bridge {b}: pref window upper {src_hi:#x} -> {dst_hi:#x}")
            setpci(b, f"PREF_BASE_UPPER32={dst_hi:#x}", f"PREF_LIMIT_UPPER32={dst_hi:#x}")
        else:
            print(f"bridge {b}: pref window upper base={bu:#x} limit={lu:#x} (left alone)")

    for d in devs:
        if is_bridge[d]:
            continue
        for i in range(6):
            v = getpci(d, f"BASE_ADDRESS_{i}")
            if (v & 0x1) or (v & 0x6) != 0x4 or not (v & 0x8) or i == 5:
                continue
            up = getpci(d, f"BASE_ADDRESS_{i + 1}")
            if up == src_hi:
                print(f"endpoint {d}: BAR{i} upper {src_hi:#x} -> {dst_hi:#x} (low dword {v:#x})")
                setpci(d, f"BASE_ADDRESS_{i + 1}={dst_hi:#x}")
            else:
                print(f"endpoint {d}: BAR{i} upper {up:#x} (left alone)")

    for d in devs:
        if saved[d] & 0x2:
            setpci(d, f"COMMAND={saved[d] & 0x2:#x}:0x2")
    print("done", "GO" if GO else "DRY")


if __name__ == "__main__":
    main()
