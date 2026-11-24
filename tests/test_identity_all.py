"""Fixture test for packages/omarchy-nvidia-egpu-12.6/identity-all.py.

No root, no hardware: feeds synthetic DT "ranges" blobs for every jw16
USB-C port and stubs lspci/setpci to check the upper dwords the script
would write on each port.
"""
import importlib.util
import struct
import tempfile
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "packages" / "omarchy-nvidia-egpu-12.6"
spec = importlib.util.spec_from_file_location("identity_all", PKG / "identity-all.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def ranges_blob(cpu_hi, pci_hi=0x8):
    # non-pref 32-bit record first, then the 64-bit pref record (flags 0x43000000)
    return (struct.pack(">7I", 0x02000000, 0x0, 0x00400000, 0x0, 0x0E0400000, 0x0, 0x00400000)
            + struct.pack(">7I", 0x43000000, pci_hi, 0x0, cpu_hi, 0x0, 0x0, 0x43800000))


# jw16 (t6001) USB-C port -> pcie@ node -> CPU upper dword (t600x-pciec.dtsi)
PORTS = {
    "pcie@730000000 (USB-C Left Back)": 0x8,
    "pcie@b30000000 (USB-C Left Front)": 0xc,
    "pcie@f30000000 (USB-C Right)": 0x10,
    "pcie@1330000000": 0x14,
}


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
        (m.ROOT, "PREF_MEMORY_LIMIT.w"): 0xFFF1,
        (m.ROOT, "PREF_BASE_UPPER32"): 0x8,
        (m.ROOT, "PREF_LIMIT_UPPER32"): 0x8,
        ("0001:04:01.0", "PREF_MEMORY_BASE.w"): 0x0001,
        ("0001:04:01.0", "PREF_MEMORY_LIMIT.w"): 0xFFF1,
        ("0001:04:01.0", "PREF_BASE_UPPER32"): 0x8,
        ("0001:04:01.0", "PREF_LIMIT_UPPER32"): 0x8,
        ("0001:05:00.0", "BASE_ADDRESS_0"): 0x0000000C,
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


class TestIdentityAll(unittest.TestCase):
    def test_ranges_parse_each_port(self):
        for port, cpu_hi in PORTS.items():
            with self.subTest(port=port), tempfile.NamedTemporaryFile() as f:
                f.write(ranges_blob(cpu_hi))
                f.flush()
                self.assertEqual(m.root_pref64_dwords(f.name), (0x8, cpu_hi))

    def test_writes_each_port(self):
        for port, cpu_hi in PORTS.items():
            with self.subTest(port=port):
                w = run_main(cpu_hi)
                if cpu_hi == 0x8:
                    self.assertEqual(w, [])
                    continue
                ups = {a for wr in w for a in wr if a.startswith("PREF_BASE_UPPER32=")}
                self.assertEqual(ups, {f"PREF_BASE_UPPER32={cpu_hi:#x}"})
                self.assertIn(f"BASE_ADDRESS_1={cpu_hi:#x}", {a for wr in w for a in wr})


if __name__ == "__main__":
    unittest.main()
