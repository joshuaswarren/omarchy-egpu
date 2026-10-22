#!/usr/bin/env python3
"""Behavioral tests for egpu_doctor.py against synthetic sysfs fixtures.

Fixtures prove the tool's decisions, not that any real host works. Run:

    python3 -m unittest discover -s tests
"""

import contextlib
import importlib.util
import io
import os
import pathlib
import tempfile
import unittest
from unittest import mock

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "egpu_doctor.py"
_spec = importlib.util.spec_from_file_location("egpu_doctor_under_test", SCRIPT)
egpu_doctor = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(egpu_doctor)

# BAR0+BAR1 assigned; rows 2-5 unimplemented (no flags, as firmware leaves them).
GOOD_RESOURCE = "\n".join(
    [
        "0x0000000080000000 0x000000008fffffff 0x0000000000040200",
        "0x0000000090000000 0x00000000901fffff 0x0000000000040200",
        "0x0000000000000000 0x0000000000000000 0x0000000000000000",
        "0x0000000000000000 0x0000000000000000 0x0000000000000000",
        "0x0000000000000000 0x0000000000000000 0x0000000000000000",
        "0x0000000000000000 0x0000000000000000 0x0000000000000000",
    ]
) + "\n"

# Regression: BAR0 with a nonzero end but zero start is NOT assigned.
ZERO_START_BAR0 = "\n".join(
    [
        "0x0000000000000000 0x000000008fffffff 0x0000000000040200",
        "0x0000000090000000 0x00000000901fffff 0x0000000000040200",
    ]
) + "\n" + "0x0000000000000000 0x0000000000000000 0x0000000000000000\n" * 4

# Regression: memory-flagged BAR5 unassigned while BAR0/BAR1 look fine.
PARTIAL_BAR5 = GOOD_RESOURCE.splitlines()[0] + "\n" + GOOD_RESOURCE.splitlines()[1] + "\n" + \
    "0x0000000000000000 0x0000000000000000 0x0000000000000000\n" * 3 + \
    "0x0000000000000000 0x00000000fbc00000 0x0000000000040200\n"

EMPTY_RESOURCE = "0x0000000000000000 0x0000000000000000 0x0000000000000000\n" * 6

GARBAGE_RESOURCE = "this is not a resource table\n"

# printf is a shell builtin: the fake works with PATH holding only the fixture bin.
VULKAN_MATCH = (
    "printf 'Devices:\\nGPU0:\\n\\tdeviceName = AMD Radeon RX 7600 (RADV NAVI33)"
    "\\n\\tdeviceType = DISCRETE_GPU (0x2)\\n\\tvendorID = 0x1002"
    "\\n\\tdeviceID = 0x7480\\n'\n"
)
VULKAN_LLVMLPIPE = (
    "printf 'Devices:\\nGPU0:\\n\\tdeviceName = llvmpipe (LLVM 17.0.6, 256 bits)"
    "\\n\\tdeviceType = CPU (0x1)\\n\\tvendorID = 0x1005\\n\\tdeviceID = 0x1005\\n'\n"
)


def build_sysfs(top):
    root = pathlib.Path(top)
    (root / "bus/pci/devices").mkdir(parents=True)
    (root / "bus/thunderbolt/devices").mkdir(parents=True)
    return root


def add_tunnel(root, name="0-1", authorized="1"):
    d = root / "bus/thunderbolt/devices" / name
    d.mkdir(parents=True)
    (d / "authorized").write_text(authorized + "\n")
    (d / "vendor_name").write_text("ASRock\n")
    (d / "device_name").write_text("AMD Graphics Enclosure\n")
    (d / "generation").write_text("4\n")


def add_gpu(
    root,
    name="0000:06:00.0",
    boot_vga="0",
    driver="amdgpu",
    resource=GOOD_RESOURCE,
    vendor="0x1002",
    device="0x7480",
    external="1",
):
    d = root / "bus/pci/devices" / name
    d.mkdir(parents=True)
    (d / "class").write_text("0x030000\n")
    (d / "vendor").write_text(vendor + "\n")
    (d / "device").write_text(device + "\n")
    (d / "boot_vga").write_text(boot_vga + "\n")
    if resource is not None:
        (d / "resource").write_text(resource)
    (d / "current_link_speed").write_text("16.0 GT/s PCIe\n")
    (d / "current_link_width").write_text("4\n")
    (d / "max_link_speed").write_text("16.0 GT/s PCIe\n")
    (d / "max_link_width").write_text("16\n")
    if external is not None:
        (d / "external_facing").write_text(external + "\n")
    if driver is not None:
        os.symlink(f"../drivers/{driver}", d / "driver")


def add_vulkaninfo(bindir, body):
    exe = bindir / "vulkaninfo"
    exe.write_text("#!/bin/sh\n" + body)
    exe.chmod(0o755)


class EgpuDoctorTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = build_sysfs(tmp.name)
        self.bindir = pathlib.Path(tmp.name) / "bin"
        self.bindir.mkdir()  # empty: no vulkaninfo on PATH unless a test adds one

    def doctor(self, extra=()):
        out = io.StringIO()
        with mock.patch.dict(os.environ, {"PATH": str(self.bindir)}):
            with contextlib.redirect_stdout(out):
                code = egpu_doctor.main(["--sysfs-root", str(self.root), *extra])
        return code, out.getvalue()

    def doctor_raises(self, extra):
        with self.assertRaises(SystemExit) as caught:
            self.doctor(extra)
        return caught.exception.code

    def full_fixture(self, authorized="1", external="1", resource=GOOD_RESOURCE,
                     driver="amdgpu", vulkan=VULKAN_MATCH):
        add_tunnel(self.root, authorized=authorized)
        add_gpu(self.root, external=external, resource=resource, driver=driver)
        if vulkan:
            add_vulkaninfo(self.bindir, vulkan)

    # --- core verdicts ---

    def test_host_without_egpu_is_incomplete_never_pass(self):
        add_gpu(self.root, name="0000:00:02.0", boot_vga="1", external=None)
        code, out = self.doctor()
        self.assertEqual(code, egpu_doctor.EXIT_INCOMPLETE)
        self.assertNotIn("result: PASS", out)
        self.assertIn("no Thunderbolt/USB4 devices are visible", out)
        self.assertIn("boot_vga=1", out)
        self.assertIn("external topology unverified", out)

    def test_matching_real_gpu_passes_end_to_end(self):
        self.full_fixture()
        code, out = self.doctor()
        self.assertEqual(code, egpu_doctor.EXIT_PASS)
        self.assertIn("result: PASS", out)
        self.assertIn("matches 0000:06:00.0", out)
        self.assertIn("external topology measured", out)

    # --- BAR regressions ---

    def test_all_bars_empty_fails(self):
        self.full_fixture(resource=EMPTY_RESOURCE)
        code, out = self.doctor()
        self.assertEqual(code, egpu_doctor.EXIT_FAILURE)
        self.assertIn("no PCI BARs assigned", out)

    def test_zero_start_nonzero_end_bar_is_unassigned(self):
        self.full_fixture(resource=ZERO_START_BAR0)
        code, out = self.doctor()
        self.assertEqual(code, egpu_doctor.EXIT_FAILURE)
        self.assertIn("BAR0", out)

    def test_partially_unassigned_mem_bar_fails(self):
        self.full_fixture(resource=PARTIAL_BAR5)
        code, out = self.doctor()
        self.assertEqual(code, egpu_doctor.EXIT_FAILURE)
        self.assertIn("BAR5", out)

    def test_unimplemented_bars_do_not_fail_a_healthy_gpu(self):
        self.full_fixture()  # rows 2-5 are flagless zero rows by design
        code, out = self.doctor()
        self.assertEqual(code, egpu_doctor.EXIT_PASS)

    def test_unreadable_bars_block_pass(self):
        self.full_fixture(resource=GARBAGE_RESOURCE)
        code, out = self.doctor()
        self.assertEqual(code, egpu_doctor.EXIT_INCOMPLETE)
        self.assertNotIn("result: PASS", out)
        self.assertIn("unreadable", out)

    # --- driver and Vulkan regressions ---

    def test_missing_driver_fails(self):
        self.full_fixture(driver=None)
        code, out = self.doctor()
        self.assertEqual(code, egpu_doctor.EXIT_FAILURE)
        self.assertIn("no kernel driver bound", out)

    def test_llvmpipe_only_is_failure_not_match(self):
        self.full_fixture(vulkan=VULKAN_LLVMLPIPE)
        code, out = self.doctor()
        self.assertEqual(code, egpu_doctor.EXIT_FAILURE)
        self.assertIn("software renderer", out)
        self.assertIn("only software renderers", out)

    def test_missing_vulkaninfo_downgrades_to_incomplete(self):
        self.full_fixture(vulkan=None)
        code, out = self.doctor()
        self.assertEqual(code, egpu_doctor.EXIT_INCOMPLETE)
        self.assertNotIn("result: PASS", out)
        self.assertIn("vulkaninfo", out)

    # --- topology regressions ---

    def test_topology_unverified_blocks_pass_even_with_healthy_chain(self):
        # Authorized dock + healthy internal dGPU + matching Vulkan must NOT pass.
        self.full_fixture(external=None)
        code, out = self.doctor()
        self.assertEqual(code, egpu_doctor.EXIT_INCOMPLETE)
        self.assertNotIn("result: PASS", out)
        self.assertNotIn("failure:", out)
        self.assertIn("external topology unverified", out)

    def test_device_flag_asserts_topology_and_passes_labelled(self):
        self.full_fixture(external=None)
        code, out = self.doctor(extra=("--device", "0000:06:00.0"))
        self.assertEqual(code, egpu_doctor.EXIT_PASS)
        self.assertIn("user-asserted", out)

    def test_device_flag_rejects_unknown_and_malformed_bdf(self):
        self.full_fixture()
        self.assertEqual(
            self.doctor_raises(("--device", "0000:99:00.7")), egpu_doctor.EXIT_USAGE
        )
        self.assertEqual(
            self.doctor_raises(("--device", "../../etc/passwd")), egpu_doctor.EXIT_USAGE
        )

    # --- tunnel regressions ---

    def test_unauthorized_tunnel_fails(self):
        self.full_fixture(authorized="0")
        code, out = self.doctor()
        self.assertEqual(code, egpu_doctor.EXIT_FAILURE)
        self.assertIn("not authorized", out)

    def test_usb_only_tunnel_is_not_success(self):
        self.full_fixture(authorized="3")
        code, out = self.doctor()
        self.assertEqual(code, egpu_doctor.EXIT_INCOMPLETE)
        self.assertNotIn("result: PASS", out)
        self.assertIn("USB only", out)

    def test_unknown_authorized_state_is_not_success(self):
        self.full_fixture(authorized="7")
        code, out = self.doctor()
        self.assertEqual(code, egpu_doctor.EXIT_INCOMPLETE)
        self.assertNotIn("result: PASS", out)
        self.assertIn("unknown authorization state", out)

    # --- usage errors ---

    def test_timeout_rejects_nan_inf_and_nonpositive(self):
        self.full_fixture()
        self.assertEqual(self.doctor_raises(("--timeout", "nan")), egpu_doctor.EXIT_USAGE)
        self.assertEqual(self.doctor_raises(("--timeout", "inf")), egpu_doctor.EXIT_USAGE)
        self.assertEqual(self.doctor_raises(("--timeout", "0")), egpu_doctor.EXIT_USAGE)


if __name__ == "__main__":
    unittest.main()
