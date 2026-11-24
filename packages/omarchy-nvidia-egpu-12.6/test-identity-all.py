#!/usr/bin/env python3
"""Fixture test for identity-all.py. No root, no hardware: feeds synthetic
DT "ranges" blobs for every jw16 USB-C port and stubs lspci/setpci to check
the upper dwords the script would write. Run: python3 test-identity-all.py"""
import importlib.util
import struct
import sys
import tempfile
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "identity_all", Path(__file__).with_name("identity-all.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

PASS = FAIL = 0


def ok(name):
    global PASS
    PASS += 1
    print(f"  ok   {name}")


def bad(name, detail):
    global FAIL
    FAIL += 1
    print(f"  FAIL {name}: {detail}")


def ranges_blob(cpu_hi, pci_hi=0x8):
    # non-pref 32-bit record first, then the 64-bit pref record (flags 0x43000000)
    return (struct.pack(">7I", 0x02000000, 0x0, 0x00400000, 0x0, 0xe0400000, 0x0, 0x00400000)
            + struct.pack(">7I", 0x43000000, pci_hi, 0x0, cpu_hi, 0x0, 0x0, 0x43800000))


# jw16 (t6001) USB-C port -> pcie@ node -> CPU upper dword (t600x-pciec.dtsi)
PORTS = {
    "USB-C Left Back  (pcie@730000000)": 0x8,
    "USB-C Left Front (pcie@b30000000)": 0xc,
    "USB-C Right      (pcie@f30000000)": 0x10,
}

for port, cpu_hi in PORTS.items():
    name = f"ranges parse {port}"
    with tempfile.NamedTemporaryFile() as f:
        f.write(ranges_blob(cpu_hi))
        f.flush()
        try:
            got = m.root_pref64_dwords(f.name)
        except Exception as e:
            bad(name, e)
            continue
    ok(name) if got == (0x8, cpu_hi) else bad(name, f"got {got}")


def run_main(cpu_hi):
    """Run main() with fakes; return the setpci arg tuples it issued."""
    writes = []
    regs = {
        ("0001:04:01.0", "HEADER_TYPE.b"): 0x1,
        ("0001:05:00.0", "HEADER_TYPE.b"): 0x0,
        ("0001:04:01.0", "COMMAND.w"): 0x406,
        ("0001:05:00.0", "COMMAND.w"): 0x406,
        (m.ROOT, "COMMAND.w"): 0x406,
        (m.ROOT, "HEADER_TYPE.b"): 0x1,
        (m.ROOT, "PREF_MEMORY_BASE.w"): 0x0001,
        (m.ROOT, "PREF_MEMORY_LIMIT.w"): 0xfff1,
        (m.ROOT, "PREF_BASE_UPPER32"): 0x8,
        (m.ROOT, "PREF_LIMIT_UPPER32"): 0x8,
        ("0001:04:01.0", "PREF_MEMORY_BASE.w"): 0x0001,
        ("0001:04:01.0", "PREF_MEMORY_LIMIT.w"): 0xfff1,
        ("0001:04:01.0", "PREF_BASE_UPPER32"): 0x8,
        ("0001:04:01.0", "PREF_LIMIT_UPPER32"): 0x8,
        ("0001:05:00.0", "BASE_ADDRESS_0"): 0x0000000c,
        ("0001:05:00.0", "BASE_ADDRESS_1"): 0x8,
        ("0001:05:00.0", "BASE_ADDRESS_2"): 0,
        ("0001:05:00.0", "BASE_ADDRESS_3"): 0,
        ("0001:05:00.0", "BASE_ADDRESS_4"): 0,
        ("0001:05:00.0", "BASE_ADDRESS_5"): 0,
    }
    m.root_pref64_dwords = lambda rp=None: (0x8, cpu_hi)
    m.run = lambda *a: ("0001:00:00.0\n0001:04:01.0\n0001:05:00.0"
                        if a == ("lspci", "-D") else "")
    m.getpci = lambda dev, reg: regs.get((dev, reg), 0)
    m.setpci = lambda dev, *args: writes.append((dev,) + args)
    m.main()
    return writes


for port, cpu_hi in PORTS.items():
    name = f"writes on {port}"
    w = run_main(cpu_hi)
    if cpu_hi == 0x8:
        ok(name) if not w else bad(name, f"identity port wrote {w}")
        continue
    ups = {a for wr in w for a in wr if a.startswith("PREF_BASE_UPPER32=")}
    bars = {a for wr in w for a in wr if a == f"BASE_ADDRESS_1={cpu_hi:#x}"}
    if ups == {f"PREF_BASE_UPPER32={cpu_hi:#x}"} and bars:
        ok(name)
    else:
        bad(name, f"writes={w}")

print(f"{PASS} pass, {FAIL} fail")
sys.exit(1 if FAIL else 0)
