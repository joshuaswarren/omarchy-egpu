#!/usr/bin/env python3
"""egpu-doctor: read-only eGPU diagnostic for Omarchy Linux.

Verifies the eGPU chain without changing anything:

1. Thunderbolt/USB4 tunnel: devices under /sys/bus/thunderbolt and their
   `authorized` state. Only states 1 (user) and 2 (secure) prove a PCIe
   tunnel; state 3 is USB-only; state 0 (unauthorized) is a failure.
2. PCI display GPUs: discovery, BAR resource assignment (memory BARs only;
   unimplemented and ROM slots are ignored), bound kernel driver, PCIe
   link speed/width. Every display-class device is reported; boot_vga is
   shown as raw evidence, not as an internal/external verdict.
3. External topology: the device or one of its PCI ancestors must carry
   `external_facing=1` or `removable=removable`. Without that evidence the
   result stays incomplete — an internal dGPU behind an unrelated authorized
   dock can never produce a pass. `--device BDF` replaces the measured
   topology with a labelled user assertion.
4. Vulkan: `vulkaninfo --summary` must report a real (non-software) device
   whose PCI vendor/device IDs match a topology-proven GPU. Software
   renderers (llvmpipe, lavapipe, SwiftShader) never count as a match.

Reads sysfs and runs vulkaninfo only. No root required, nothing is
written, installed, enabled, or fixed.

    egpu-doctor.py                  check this machine
    egpu-doctor.py --device BDF     check one device you assert is the eGPU
    egpu-doctor.py --sysfs-root F   read a sysfs fixture tree (tests only)

Exit codes: 0 pass, 1 incomplete, 2 failure, 64 usage error. See README.md.
"""

import argparse
import math
import os
import re
import subprocess
import sys

EXIT_PASS = 0
EXIT_INCOMPLETE = 1
EXIT_FAILURE = 2
EXIT_USAGE = 64
VULKANINFO_TIMEOUT = 10.0
BAR_ROWS = 6
IORESOURCE_MEM = 0x200
BDF_RE = re.compile(r"^[0-9a-fA-F]{4}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-7]$")

SOFTWARE_TYPES = ("CPU", "SOFTWARE")
SOFTWARE_NAME_MARKERS = ("llvmpipe", "lavapipe", "swiftshader")
AUTHORIZED_LABELS = {"1": "authorized", "2": "authorized (secure connect)"}


class UsageErrorParser(argparse.ArgumentParser):
    """Exit 64 on usage errors so they never look like a diagnostic result."""

    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"{self.prog}: error: {message}", file=sys.stderr)
        raise SystemExit(EXIT_USAGE)


def say(level, text):
    print(f"[{level}] {text}")


def read_file(path):
    try:
        with open(path, "r", errors="replace") as fh:
            return fh.read().strip()
    except OSError:
        return None


def read_text(root, rel):
    return read_file(os.path.join(root, rel))


def list_entries(root, rel):
    try:
        return sorted(os.listdir(os.path.join(root, rel)))
    except OSError:
        return None


def readlink_name(root, rel):
    try:
        return os.path.basename(os.readlink(os.path.join(root, rel)))
    except OSError:
        return None


def run_command(cmd, timeout):
    """Run cmd with a hard timeout. Returns (returncode, stdout), or
    (None, None) when the binary is missing, unusable, or too slow."""
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None, None
    return proc.returncode, proc.stdout


def fmt_size(nbytes):
    value = float(nbytes)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.0f}{unit}"
        value /= 1024
    return f"{value:.0f}TiB"


def external_evidence(root, dev_dir):
    """(True, detail) when `external_facing=1` or `removable=removable`
    is found on the device or one of its ancestors inside the sysfs root.
    Docs: Documentation/ABI/testing/sysfs-pci (external_facing),
    Documentation/ABI/testing/sysfs-devices-removable (removable)."""
    top = os.path.realpath(root)
    path = os.path.realpath(os.path.join(root, "bus/pci/devices", dev_dir))
    for _ in range(8):
        if not path.startswith(top + os.sep):
            break
        value = read_file(os.path.join(path, "external_facing"))
        if value == "1":
            return True, "external_facing=1"
        value = read_file(os.path.join(path, "removable"))
        if value == "removable":
            return True, "removable"
        if path == top:
            break
        path = os.path.dirname(path)
    return False, None


def check_tunnel(root, problems, reasons):
    """Print Thunderbolt/USB4 device states. Returns True only when a
    device in authorization state 1 or 2 proves a live PCIe tunnel."""
    entries = list_entries(root, "bus/thunderbolt/devices")
    if entries is None:
        reasons.append(
            "sysfs exposes no thunderbolt bus, so the tunnel could not be verified"
        )
        return False
    if not entries:
        reasons.append(
            "no Thunderbolt/USB4 devices are visible (enclosure unplugged, "
            "unpowered, or the host has no controller)"
        )
        return False
    tunnel_ok = False
    for name in entries:
        base = f"bus/thunderbolt/devices/{name}"
        auth = read_text(root, base + "/authorized")
        model = " ".join(
            part
            for part in (
                read_text(root, base + "/vendor_name"),
                read_text(root, base + "/device_name"),
            )
            if part
        ) or "unknown device"
        generation = read_text(root, base + "/generation")
        suffix = f", gen {generation}" if generation else ""
        if auth in AUTHORIZED_LABELS:
            say("ok", f"{name}: {model}{suffix} ({AUTHORIZED_LABELS[auth]})")
            tunnel_ok = True
        elif auth == "0":
            say(
                "problem",
                f"{name}: {model}{suffix} detected but not authorized; "
                "PCIe tunneling stays off until the device is approved",
            )
            problems.append(f"Thunderbolt/USB4 device {name} is not authorized")
        elif auth == "3":
            say(
                "info",
                f"{name}: {model}{suffix} authorized for USB only (state 3); "
                "no PCIe tunneling",
            )
            reasons.append(f"{name}: tunnel is USB-only, no PCIe")
        else:
            say("info", f"{name}: {model}{suffix} unknown authorization state {auth!r}")
            reasons.append(f"{name}: unknown authorization state {auth!r}")
    if not tunnel_ok:
        reasons.append("no Thunderbolt/USB4 device proves a PCIe tunnel")
    return tunnel_ok


def inspect_bars(root, dev):
    """Parse the first six `resource` rows (BAR0-5).

    Returns None when the file is missing or unparsable, else a dict:
    `assigned` = sizes of memory BARs with start != 0; `unassigned` =
    indices of memory-flagged rows with start == 0 (a nonzero end with a
    zero start is still unassigned - address 0 is never a GPU BAR). Rows
    without the IORESOURCE_MEM bit (0x200) are unimplemented or ROM slots
    and are ignored; empty firmware rows carry no flags.
    """
    text = read_text(root, f"bus/pci/devices/{dev}/resource")
    if text is None:
        return None
    assigned, unassigned = [], []
    for index, row in enumerate(text.splitlines()[:BAR_ROWS]):
        parts = row.split()
        if len(parts) < 3:
            continue
        try:
            start, end, flags = (int(part, 16) for part in parts[:3])
        except ValueError:
            return None
        if not flags & IORESOURCE_MEM:
            continue
        if start:
            assigned.append(end - start + 1)
        else:
            unassigned.append(index)
    return {"assigned": assigned, "unassigned": unassigned}


def check_gpus(root, problems, reasons, only):
    """Print every display-class PCI device (or just `only`). Returns the
    candidates with their topology status: "measured", "asserted"
    (--device), or None (unverified)."""
    entries = [only] if only else list_entries(root, "bus/pci/devices")
    if entries is None:
        reasons.append("sysfs exposes no PCI bus, so no GPU could be discovered")
        return []
    candidates = []
    for name in entries:
        base = f"bus/pci/devices/{name}"
        cls = read_text(root, base + "/class") or ""
        if not cls.startswith("0x03"):
            if only:
                reasons.append(f"{name}: not a display-class device (class {cls or 'unknown'})")
            continue
        vendor = read_text(root, base + "/vendor") or "unknown"
        devid = read_text(root, base + "/device") or "unknown"
        boot_vga = read_text(root, base + "/boot_vga")
        say(
            "ok",
            f"{name}: display GPU; vendor {vendor} device {devid} class {cls} "
            f"boot_vga={boot_vga if boot_vga is not None else 'n/a'} (raw evidence, "
            "not an internal/external verdict)",
        )
        candidate = {"name": name, "vendor": vendor, "devid": devid, "topology": None}
        candidates.append(candidate)
        if only:
            candidate["topology"] = "asserted"
            say("info", f"{name}: topology user-asserted via --device (not measured)")
            continue
        proven, detail = external_evidence(root, name)
        if proven:
            candidate["topology"] = "measured"
            say("ok", f"{name}: external topology measured ({detail})")
        else:
            say(
                "info",
                f"{name}: no external_facing/removable evidence on the device "
                "or its ancestors",
            )
            reasons.append(f"{name}: external topology unverified")
        driver = readlink_name(root, base + "/driver")
        if driver:
            say("ok", f"{name}: kernel driver bound: {driver}")
        else:
            say("problem", f"{name}: no kernel driver bound")
            problems.append(f"{name} has no kernel driver bound")
        bars = inspect_bars(root, name)
        if bars is None:
            say("info", f"{name}: PCI BAR assignment unreadable")
            reasons.append(f"{name}: PCI BAR assignment unreadable")
        elif bars["unassigned"]:
            listed = ", ".join(f"BAR{index}" for index in bars["unassigned"])
            say(
                "problem",
                f"{name}: unassigned memory BAR(s) {listed} (start 0; device not "
                "reachable from the CPU; often a clipped bus window on hot-plugged "
                "tunnels)",
            )
            problems.append(f"{name} has unassigned memory BARs: {listed}")
        elif bars["assigned"]:
            say(
                "ok",
                f"{name}: PCI BARs assigned: "
                + ", ".join(fmt_size(size) for size in bars["assigned"]),
            )
        else:
            say(
                "problem",
                f"{name}: no PCI BARs assigned (device not reachable from the CPU; "
                "often a clipped bus window on hot-plugged tunnels)",
            )
            problems.append(f"{name} has no PCI BARs assigned")
        speed = read_text(root, base + "/current_link_speed")
        width = read_text(root, base + "/current_link_width")
        max_speed = read_text(root, base + "/max_link_speed")
        max_width = read_text(root, base + "/max_link_width")
        link = " and ".join(
            part
            for part in (
                f"current link {speed} x{width}" if speed and width else None,
                f"max {max_speed} x{max_width}" if max_speed and max_width else None,
            )
            if part
        )
        say(
            "ok" if speed else "info",
            f"{name}: {link}" if link else f"{name}: link speed/width not exposed",
        )
    if not candidates:
        reasons.append("no display GPU is visible on PCI")
    return candidates


def parse_vulkan_summary(text):
    devices = []
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        if re.match(r"GPU\d+:", line):
            if current:
                devices.append(current)
            current = {}
            continue
        if current is None:
            continue
        key, sep, value = line.partition("=")
        if sep:
            current[key.strip()] = value.strip()
    if current:
        devices.append(current)
    return devices


def is_software_device(dev):
    dtype = dev.get("deviceType", "").split("(")[0].strip()
    name = dev.get("deviceName", "").lower()
    return dtype in SOFTWARE_TYPES or any(m in name for m in SOFTWARE_NAME_MARKERS)


def ids_match(vulkan_id, pci_id):
    try:
        return int(vulkan_id, 16) == int(pci_id, 16)
    except ValueError:
        return False


def check_vulkan(root, candidates, problems, reasons, timeout):
    """Returns True when a real Vulkan device matches a topology-proven GPU."""
    pool = [c for c in candidates if c["topology"]]
    rc, out = run_command(["vulkaninfo", "--summary"], timeout)
    if rc is None:
        say(
            "info",
            f"vulkaninfo is unavailable (not installed, or timed out after "
            f"{timeout:g}s); the Vulkan match is unverified",
        )
        reasons.append("vulkaninfo unavailable, Vulkan match unverified")
        return False
    devices = parse_vulkan_summary(out or "")
    if not devices:
        say("problem", "vulkaninfo ran but reported no usable device summary")
        problems.append("Vulkan reported no devices")
        return False
    matched = False
    real = 0
    for dev in devices:
        name = dev.get("deviceName", "unknown")
        vid = dev.get("vendorID", "?")
        did = dev.get("deviceID", "?")
        if is_software_device(dev):
            say("info", f"Vulkan software renderer (never counts as a GPU match): {name}")
            continue
        real += 1
        hit = next(
            (
                gpu
                for gpu in pool
                if ids_match(vid, gpu["vendor"]) and ids_match(did, gpu["devid"])
            ),
            None,
        )
        if hit:
            say(
                "ok",
                f"Vulkan device matches {hit['name']}: {name} "
                f"(vendorID {vid} deviceID {did}, {dev.get('deviceType', 'type unknown')})",
            )
            matched = True
        else:
            say(
                "info",
                f"Vulkan device, no topology-proven match yet: {name} "
                f"(vendorID {vid} deviceID {did})",
            )
    if pool and not matched:
        if real:
            say(
                "problem",
                "Vulkan devices exist but none match the topology-proven GPU(s); "
                "the eGPU is not usable from applications",
            )
            problems.append("no Vulkan device matches the topology-proven GPU(s)")
        else:
            say(
                "problem",
                "Vulkan reports only software renderers (llvmpipe and friends); "
                "the eGPU is not usable from applications",
            )
            problems.append("Vulkan only offers software rendering")
    elif not pool and real:
        say("info", "Vulkan devices exist, but no topology-proven eGPU to match against")
    return matched


def main(argv=None):
    parser = UsageErrorParser(
        prog="egpu-doctor",
        description="Read-only eGPU diagnostic: Thunderbolt/USB4 tunnel, PCI GPU "
        "discovery, BAR assignment, bound driver, link, external topology, and "
        "Vulkan match.",
        epilog="exit codes:\n"
        "  0   pass - tunnel, topology, GPU, driver, BARs and Vulkan all verified\n"
        "  1   incomplete - chain not verified end to end, nothing definitely broken\n"
        "  2   failure - a found component is definitely broken\n"
        "  64  usage error",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--sysfs-root",
        metavar="PATH",
        default="/sys",
        help="sysfs root to read (tests and fixtures; default: /sys)",
    )
    parser.add_argument(
        "--device",
        metavar="BDF",
        default=None,
        help="check only this PCI device (e.g. 0000:06:00.0). Its external "
        "status is then YOUR assertion, labelled user-asserted, not measured",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=VULKANINFO_TIMEOUT,
        metavar="SECONDS",
        help=f"vulkaninfo timeout in seconds (default: {VULKANINFO_TIMEOUT:g})",
    )
    args = parser.parse_args(argv)

    if not (args.timeout > 0) or math.isinf(args.timeout):
        parser.exit(
            EXIT_USAGE,
            f"{parser.prog}: error: --timeout must be a finite positive number, "
            f"got {args.timeout!r}\n",
        )
    if args.device and not BDF_RE.match(args.device):
        parser.exit(
            EXIT_USAGE,
            f"{parser.prog}: error: --device expects a PCI BDF like 0000:06:00.0, "
            f"got {args.device!r}\n",
        )
    if args.device:
        cls = read_text(args.sysfs_root, f"bus/pci/devices/{args.device}/class")
        if cls is None:
            parser.exit(
                EXIT_USAGE,
                f"{parser.prog}: error: device {args.device} not found under "
                f"{args.sysfs_root}/bus/pci/devices\n",
            )
        if not cls.startswith("0x03"):
            parser.exit(
                EXIT_USAGE,
                f"{parser.prog}: error: device {args.device} is not display-class "
                f"(class {cls})\n",
            )

    problems, reasons = [], []
    print("== Thunderbolt / USB4 tunnel ==")
    tunnel_ok = check_tunnel(args.sysfs_root, problems, reasons)
    print("== PCI display GPUs ==")
    candidates = check_gpus(args.sysfs_root, problems, reasons, args.device)
    print("== Vulkan ==")
    matched = check_vulkan(args.sysfs_root, candidates, problems, reasons, args.timeout)

    print("== result ==")
    if problems:
        for item in problems:
            print(f"  failure: {item}")
        print("result: FAILURE - something found above is definitely broken")
        return EXIT_FAILURE
    if tunnel_ok and matched and not reasons:
        print(
            "result: PASS - tunnel, topology, GPU discovery, BARs, driver and "
            "Vulkan all verified"
        )
        return EXIT_PASS
    for item in reasons:
        print(f"  incomplete: {item}")
    print("result: INCOMPLETE - the eGPU chain is not verified end to end")
    return EXIT_INCOMPLETE


if __name__ == "__main__":
    sys.exit(main())
