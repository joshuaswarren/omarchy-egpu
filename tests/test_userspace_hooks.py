#!/usr/bin/env python3
"""Behavioral tests: the userspace-615 package must not contain a path that a boot-image pacman hook watches.

Background: a package file under usr/lib/firmware made the mkinitcpio hook rebuild a boot image and rewrite limine.conf during the first install on a MacBook Pro.
Two groups: (1) hook_triggers.py on synthetic hook files; (2) the file list that the real PKGBUILD's package() produces, built from empty stand-in inputs, checked against the
path targets of the Arch mkinitcpio hook. Run: python3 -m unittest discover -s tests
"""

import fnmatch
import importlib.util
import io
import os
import pathlib
import shutil
import subprocess
import tarfile
import tempfile
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1] / "packages" / "nvidia-userspace-615"
PKGBUILD = pathlib.Path(os.environ.get("PKGBUILD_UNDER_TEST", PKG_DIR / "PKGBUILD"))
_spec = importlib.util.spec_from_file_location("hook_triggers_under_test", PKG_DIR / "hook_triggers.py")
hook_triggers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook_triggers)

# Path targets of Arch's mkinitcpio hooks and of the Omarchy boot-image hook (a hook that rebuilds the boot images).
BOOT_IMAGE_HOOK_TARGETS = [
    "usr/lib/firmware/*",
    "usr/lib/initcpio/*",
    "usr/bin/cryptsetup",
    "usr/bin/lvm",
    "usr/lib/modules/*/extramodules/",
    "usr/lib/modules/*/pkgbase",
    "usr/lib/modules/*/vmlinuz",
]
V = "615.78.08"
LIBS = [
    f"{n}.so.{V}"
    for n in "libGLX_nvidia libcuda libnvidia-ml libnvidia-glcore libnvidia-glsi libnvidia-glvkspirv libnvidia-gpucomp libnvidia-nvvm "
    "libnvidia-ptxjitcompiler libnvidia-eglcore libnvidia-allocator libnvidia-tls libnvidia-rtcore libEGL_nvidia libnvidia-rmapi-tegra".split()
] + ["libnvidia-nvvm70.so.4"]


def write_hook(directory, name, trigger_type, targets):
    body = "[Trigger]\nOperation = Install\nOperation = Upgrade\nOperation = Remove\nType = %s\n" % trigger_type
    body += "".join(f"Target = {t}\n" for t in targets)
    body += "\n[Action]\nDescription = test\nWhen = PostTransaction\nExec = /usr/bin/true\n"
    (directory / name).write_text(body)


def make_tar(path, names):
    with tarfile.open(path, "w") as t:
        for n in names:
            info = tarfile.TarInfo(n)
            t.addfile(info, io.BytesIO(b""))


class HookTriggersTest(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.hooks = self.tmp / "hooks"
        self.hooks.mkdir()
        write_hook(self.hooks, "90-initcpio.hook", "Path", ["usr/lib/firmware/*", "usr/bin/lvm"])
        write_hook(self.hooks, "30-other.hook", "Path", ["usr/share/icons/*"])
        write_hook(self.hooks, "50-package.hook", "Package", ["usr/lib/firmware/*"])

    def run_hooks(self, names, paths=None):
        pkg = self.tmp / "p.tar"
        make_tar(pkg, [".PKGINFO"] + names)
        return hook_triggers.matching_hooks(hook_triggers.package_paths(pkg) + (paths or []), [str(self.hooks)])

    def test_firmware_path_matches_the_path_hook_only(self):
        self.assertEqual(self.run_hooks(["usr/lib/firmware/nvidia/x.bin"]), ["90-initcpio.hook"])

    def test_profile_tree_paths_match_no_hook(self):
        self.assertEqual(self.run_hooks(["usr/lib/nvidia-egpu-615.78.08/firmware/x.bin", "usr/lib/nvidia-egpu-615.78.08/lib/a.so"]), [])

    def test_paths_of_the_version_being_replaced_count(self):
        self.assertEqual(self.run_hooks(["usr/lib/nvidia-egpu-615.78.08/lib/a.so"], ["/usr/lib/firmware/nvidia/615.78.08/old.bin"]), ["90-initcpio.hook"])


class PackageLayoutTest(unittest.TestCase):
    def build_file_list(self):
        tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        start, src, pkgdir = tmp / "start", tmp / "src", tmp / "pkg"
        x = src / "x"
        (x / "firmware").mkdir(parents=True)
        start.mkdir()
        pkgdir.mkdir()
        for name in LIBS + ["nvidia-smi", "nvidia-modprobe", "LICENSE"]:
            (x / name).write_text("x")
        (x / "nvidia_icd.json").write_text('{"ICD": {"library_path": "libGLX_nvidia.so.0"}}')
        for fw in ("gsp_ga10x", "gsp_tu10x", "ucodes_ga10x", "ucodes_tu10x"):
            (x / "firmware" / f"{fw}.bin").write_text("x")
        for name in ("10_nvidia.json", "vulkan-env.sh"):
            shutil.copy(PKG_DIR / name, start / name)
        (start / "check-egl-profile.sh").write_text("#!/bin/bash\nexit 0\n")
        (start / "check-egl-profile.sh").chmod(0o755)
        script = f'source "{PKGBUILD}"; startdir="{start}"; srcdir="{src}"; pkgdir="{pkgdir}"; package'
        r = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return sorted(str(p.relative_to(pkgdir)) for p in pkgdir.rglob("*") if not p.is_dir())

    def test_no_package_path_is_watched_by_a_boot_image_hook(self):
        files = self.build_file_list()
        self.assertGreater(len(files), 20)
        hits = [f for f in files for t in BOOT_IMAGE_HOOK_TARGETS if fnmatch.fnmatchcase(f, t)]
        self.assertEqual(hits, [], "package paths that a boot-image hook watches: %s" % hits)

    def test_firmware_is_in_the_profile_tree(self):
        files = self.build_file_list()
        self.assertIn(f"usr/lib/nvidia-egpu-{V}/firmware/gsp_ga10x.bin", files)


class InstallScriptTest(unittest.TestCase):
    """The install script links /usr/lib/firmware/nvidia/VERSION to the firmware in the profile tree (run here against a temporary root)."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        text = (PKG_DIR / "omarchy-nvidia-egpu-userspace-615.install").read_text().replace("/usr/lib", str(self.tmp / "usr/lib"))
        self.script = self.tmp / "install.sh"
        self.script.write_text(text)
        self.target = self.tmp / f"usr/lib/nvidia-egpu-{V}/firmware"
        self.target.mkdir(parents=True)
        (self.target / "gsp.bin").write_text("fw")
        self.fw = self.tmp / f"usr/lib/firmware/nvidia/{V}"

    def call(self, function):
        return subprocess.run(["bash", "-c", f'source "{self.script}"; {function}'], capture_output=True, text=True, check=False)

    def test_fresh_install_links_the_firmware_directory(self):
        r = self.call("post_install")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.fw.is_symlink())
        self.assertEqual((self.fw / "gsp.bin").read_text(), "fw")

    def test_empty_directory_from_a_hand_staged_tree_is_replaced(self):
        self.fw.mkdir(parents=True)
        self.assertEqual(self.call("post_install").returncode, 0)
        self.assertTrue(self.fw.is_symlink())

    def test_directory_with_files_is_left_alone_with_a_warning(self):
        self.fw.mkdir(parents=True)
        (self.fw / "mine.bin").write_text("keep")
        r = self.call("post_upgrade")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("warning", r.stderr)
        self.assertFalse(self.fw.is_symlink())
        self.assertEqual((self.fw / "mine.bin").read_text(), "keep")

    def test_remove_deletes_only_its_own_link(self):
        self.call("post_install")
        self.assertEqual(self.call("pre_remove").returncode, 0)
        self.assertFalse(self.fw.exists() or self.fw.is_symlink())
        self.fw.parent.mkdir(parents=True, exist_ok=True)
        self.fw.symlink_to("../elsewhere")
        self.assertEqual(self.call("pre_remove").returncode, 0)
        self.assertTrue(self.fw.is_symlink())


if __name__ == "__main__":
    unittest.main()
