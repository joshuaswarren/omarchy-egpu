#!/usr/bin/env python3
"""Behavioral tests for packages/nvidia-userspace-615/inventory.py (collision inventory of the package against a host).

Fixtures are a tiny synthetic package tarball and a synthetic host inventory; they prove the classification (SAME, NEW, DIFF, HOST-ONLY)
and the exit code, not that any real host migrates. Run: python3 -m unittest discover -s tests
"""

import contextlib
import hashlib
import importlib.util
import io
import pathlib
import tarfile
import tempfile
import unittest
from unittest import mock

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "packages" / "nvidia-userspace-615" / "inventory.py"
_spec = importlib.util.spec_from_file_location("inventory_under_test", SCRIPT)
inventory = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(inventory)

ROOT = "usr/lib/nvidia-egpu-615.78.08/"
FW = "usr/lib/firmware/nvidia/615.78.08/"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def make_package(path, files, links):
    with tarfile.open(path, "w") as t:
        t.addfile(tarfile.TarInfo(".PKGINFO"), io.BytesIO(b""))
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
        for name, target in links.items():
            info = tarfile.TarInfo(name)
            info.type = tarfile.SYMTYPE
            info.linkname = target
            t.addfile(info)


def host_text(files, links, firmware):
    lines = ["D ./lib 755"]
    for name, data in files.items():
        lines.append(f"F ./{name} 644 {len(data)} {sha(data)}")
    for name, target in links.items():
        lines.append(f"L ./{name} -> {target}")
    lines.append("== firmware")
    for name, data in firmware.items():
        lines.append(f"{sha(data)}  /{FW}{name}")
    return "\n".join(lines) + "\n"


class InventoryTest(unittest.TestCase):
    def run_inventory(self, pkg_files, pkg_links, host_files, host_links, host_fw):
        with tempfile.TemporaryDirectory() as tmp:
            pkg = pathlib.Path(tmp) / "p.tar"
            txt = pathlib.Path(tmp) / "host.txt"
            make_package(pkg, pkg_files, pkg_links)
            txt.write_text(host_text(host_files, host_links, host_fw))
            out = io.StringIO()
            with contextlib.redirect_stdout(out), mock.patch("sys.argv", ["inventory.py", str(pkg), str(txt)]):
                rc = inventory.main()
        return rc, out.getvalue()

    def test_identical_tree_is_all_same_and_exits_zero(self):
        files = {ROOT + "lib/libcuda.so.615.78.08": b"cuda", ROOT + "firmware/gsp.bin": b"fw"}
        links = {ROOT + "lib/libcuda.so.1": "libcuda.so.615.78.08"}
        rc, out = self.run_inventory(
            files, links, {"lib/libcuda.so.615.78.08": b"cuda"}, {"lib/libcuda.so.1": "libcuda.so.615.78.08"}, {"gsp.bin": b"fw"}
        )
        self.assertEqual(rc, 0, out)
        self.assertIn("SAME 3, NEW 0, DIFF 0, HOST-ONLY 0", out)

    def test_new_file_is_reported_new_and_does_not_fail(self):
        files = {ROOT + "lib/libEGL_nvidia.so.615.78.08": b"egl"}
        rc, out = self.run_inventory(files, {}, {}, {}, {})
        self.assertEqual(rc, 0, out)
        self.assertIn("NEW   " + ROOT + "lib/libEGL_nvidia.so.615.78.08", out)

    def test_changed_bytes_are_diff_and_fail(self):
        rc, out = self.run_inventory({ROOT + "lib/a.so": b"new"}, {}, {"lib/a.so": b"old"}, {}, {})
        self.assertEqual(rc, 1, out)
        self.assertIn("DIFF  " + ROOT + "lib/a.so", out)

    def test_changed_link_target_is_diff_and_fail(self):
        rc, out = self.run_inventory({}, {ROOT + "lib/a.so.1": "a.so.2"}, {}, {"lib/a.so.1": "a.so.1.0"}, {})
        self.assertEqual(rc, 1, out)
        self.assertIn("DIFF  " + ROOT + "lib/a.so.1", out)

    def test_host_file_missing_from_package_fails(self):
        rc, out = self.run_inventory({ROOT + "lib/a.so": b"a"}, {}, {"lib/a.so": b"a", "lib/extra.so": b"x"}, {}, {})
        self.assertEqual(rc, 1, out)
        self.assertIn("HOST-ONLY " + ROOT + "lib/extra.so", out)


if __name__ == "__main__":
    unittest.main()
