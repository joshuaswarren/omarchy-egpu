#!/usr/bin/env python3
"""Behavioral tests for packages/nvidia-userspace-615/migrate.sh in plan mode, on a synthetic host root (MIGRATE_ROOT) and a stub pacman.

They prove the plan's stop rules (a differing file, a file another package owns, a missing lsof) and its exit codes, not that any real host migrates.
Run: python3 -m unittest discover -s tests
"""

import io
import os
import pathlib
import shutil
import subprocess
import tarfile
import tempfile
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1] / "packages" / "nvidia-userspace-615"
SCRIPT = pathlib.Path(os.environ.get("MIGRATE_SH", PKG_DIR / "migrate.sh"))
ROOT = "usr/lib/nvidia-egpu-615.78.08/"
FW = "usr/lib/firmware/nvidia/615.78.08/"
TOOLS = ["bash", "tar", "find", "sort", "cmp", "readlink", "date", "mktemp", "wc", "tr", "sed", "grep", "cat", "id", "dirname", "rm", "mkdir", "head", "cut", "xz", "gzip", "ln", "python3", "awk"]


def make_package(path, files):
    with tarfile.open(path, "w:xz") as t:
        t.addfile(tarfile.TarInfo(".PKGINFO"), io.BytesIO(b""))
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))


class MigratePlanTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.host = self.tmp / "host"
        self.pkg = self.tmp / "p.pkg.tar.xz"
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        for tool in TOOLS:
            (self.bin / tool).symlink_to(shutil.which(tool))
        self.owners = self.tmp / "owners"
        self.owners.write_text("")
        (self.bin / "pacman").write_text(
            '#!/bin/bash\n[ "$1" = -Qqo ] || exit 1\ngrep -m1 "^$2 " "$STUB_OWNERS" | cut -d" " -f2-\n'
            "exit 0\n"
        )
        (self.bin / "pacman").chmod(0o755)
        (self.bin / "lsof").write_text("#!/bin/bash\nexit 0\n")
        (self.bin / "lsof").chmod(0o755)
        (self.bin / "readelf").write_text("#!/bin/bash\nexit 0\n")
        (self.bin / "readelf").chmod(0o755)
        make_package(self.pkg, {ROOT + "lib/a.so": b"aaa", ROOT + "lib/b.so": b"bbb"})

    def put_host(self, name, data):
        path = self.host / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def plan(self, hookdirs=""):
        env = {"PATH": str(self.bin), "MIGRATE_ROOT": str(self.host), "STUB_OWNERS": str(self.owners), "MIGRATE_HOOKDIRS": hookdirs}
        return subprocess.run(
            [shutil.which("bash"), str(SCRIPT), str(self.pkg)], env=env, capture_output=True, text=True, check=False
        )

    def test_firmware_in_the_profile_tree_is_compared_with_the_host_firmware_dir(self):
        make_package(self.pkg, {ROOT + "firmware/gsp.bin": b"fw"})
        self.put_host(FW + "gsp.bin", b"fw")
        r = self.plan()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("SAME 1, NEW 0, DIFF 0", r.stdout)
        self.put_host(FW + "gsp.bin", b"other")
        r = self.plan()
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)

    def test_plan_names_the_hooks_that_watch_the_transaction(self):
        hooks = self.tmp / "hooks"
        hooks.mkdir()
        (hooks / "90-initcpio.hook").write_text(
            "[Trigger]\nOperation = Remove\nType = Path\nTarget = usr/lib/firmware/*\n\n[Action]\nWhen = PostTransaction\nExec = /usr/bin/true\n"
        )
        self.put_host(ROOT + "lib/a.so", b"aaa")
        quiet = self.plan(str(hooks))
        self.assertEqual(quiet.returncode, 0, quiet.stdout + quiet.stderr)
        self.assertNotIn("90-initcpio.hook", quiet.stdout)
        # the installed earlier revision keeps its firmware under usr/lib/firmware: removing it would trigger the hook
        (self.bin / "pacman").write_text(
            '#!/bin/bash\n[ "$1" = -Ql ] && { echo "omarchy-nvidia-egpu-userspace-615 /usr/lib/firmware/nvidia/615.78.08/gsp.bin"; exit 0; }\n'
            '[ "$1" = -Qqo ] || exit 1\nexit 0\n'
        )
        r = self.plan(str(hooks))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("apply masks them): 90-initcpio.hook", r.stdout)

    def test_missing_python3_stops_the_plan(self):
        (self.bin / "python3").unlink()
        r = self.plan()
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("python3 is missing", r.stdout)

    def test_clean_host_plans_and_exits_zero(self):
        self.put_host(ROOT + "lib/a.so", b"aaa")
        r = self.plan()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("SAME 1, NEW 1, DIFF 0, owned by another package 0", r.stdout)
        self.assertIn("PLAN only", r.stdout)

    def test_differing_host_file_stops_the_plan(self):
        self.put_host(ROOT + "lib/a.so", b"changed")
        r = self.plan()
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("DIFF  " + ROOT + "lib/a.so", r.stdout)

    def test_file_owned_by_another_package_stops_the_plan(self):
        self.put_host(ROOT + "lib/a.so", b"aaa")
        self.owners.write_text(f"/{ROOT}lib/a.so some-other-package\n")
        r = self.plan()
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("is owned by some-other-package", r.stdout)

    def test_files_owned_by_the_old_addon_are_allowed(self):
        self.put_host(ROOT + "lib/a.so", b"aaa")
        self.owners.write_text(f"/{ROOT}lib/a.so omarchy-nvidia-egpu-vulkan-615\n")
        r = self.plan()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_missing_lsof_stops_the_plan(self):
        (self.bin / "lsof").unlink()
        r = self.plan()
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("lsof is missing", r.stdout)

    def test_missing_readelf_stops_the_plan(self):
        (self.bin / "readelf").unlink()
        r = self.plan()
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("neither aarch64-linux-gnu-readelf nor readelf", r.stdout)

    def test_cross_prefixed_readelf_alone_is_enough(self):
        (self.bin / "readelf").rename(self.bin / "aarch64-linux-gnu-readelf")
        r = self.plan()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_apply_refuses_without_root(self):
        if os.getuid() == 0:
            self.skipTest("running as root")
        env = {"PATH": str(self.bin), "STUB_OWNERS": str(self.owners)}
        r = subprocess.run([shutil.which("bash"), str(SCRIPT), str(self.pkg), "--apply"], env=env, capture_output=True, text=True, check=False)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("needs root", r.stderr)


if __name__ == "__main__":
    unittest.main()
