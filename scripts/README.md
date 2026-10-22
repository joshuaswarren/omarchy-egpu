# egpu-doctor

Read-only diagnostic for eGPU setups on Omarchy Linux. One script, stdlib only:

```sh
python3 scripts/egpu_doctor.py --help
python3 scripts/egpu_doctor.py
python3 scripts/egpu_doctor.py --device 0000:06:00.0   # you assert this is the eGPU
```

## What it checks

1. **Tunnel:** devices under `/sys/bus/thunderbolt/devices` and their
   `authorized` state. States 1 and 2 satisfy this helper's authorization check.
   Authorization alone does not prove working PCIe traffic. State 0 is a failure; state 3
   is USB-only and never a pass; any other value is reported as unknown and
   keeps the result incomplete.
2. **GPUs:** every display-class PCI device (`class 0x03` prefix), with
   `vendor`, `device`, `class`, and `boot_vga` shown as raw evidence.
   `boot_vga` is not treated as an internal/external verdict.
3. **Per GPU:** memory BAR assignment from the first six `resource` rows
   (BAR0-5): a memory-flagged row (`IORESOURCE_MEM`, bit 0x200) with
   `start == 0` is unassigned even when its end is nonzero; flagless zero
   rows are unimplemented slots and ROM is optional, so they are ignored.
   Plus the bound kernel driver (symlink) and PCIe link speed/width.
4. **External topology:** the device or one of its PCI ancestors must carry
   `external_facing=1` or `removable=removable`. Without that evidence the
   result stays incomplete, so an internal dGPU behind an unrelated authorized
   dock can never produce a pass. With `--device BDF` the measured check is
   replaced by your assertion, labelled `user-asserted` in the output. It is
   a claim, not proof.
5. **Vulkan:** runs `vulkaninfo --summary` and requires a real device whose
   `vendorID`/`deviceID` equal a topology-proven GPU's PCI IDs. Software
   renderers (llvmpipe, lavapipe, SwiftShader) are reported but never count
   as a match.

## Exit codes

| Code | Meaning |
| ---- | ------- |
| `0` | **pass:** the checked prerequisites pass; external topology may be user-asserted with `--device`; this is not a compute benchmark |
| `1` | **incomplete:** a prerequisite is unverified, such as the tunnel, topology, BAR evidence, or Vulkan |
| `2` | **failure:** an observed prerequisite failed, such as authorization, memory BAR assignment, driver binding, or a Vulkan device match |
| `64` | usage error (unknown flag, non-finite/non-positive `--timeout`, malformed or non-display `--device`) |

## Guarantees and limits

- **Read-only.** Sysfs reads plus one `vulkaninfo --summary` call with a hard
  timeout (`--timeout SECONDS`, finite and positive, default 10). No writes,
  no installs, no root, no fixes. It labels state and stops.
- A host with no eGPU gets **incomplete** with the missing links listed.
  PASS requires an authorized device and external topology evidence, or a
  labelled `--device` assertion. Device-ID matching cannot distinguish two
  identical GPUs. Confirm the selected card in the application log before measuring compute.
- vulkaninfo is optional; without it the result degrades to incomplete,
  never to pass. On Arch it ships in `vulkan-tools`.
- `--sysfs-root PATH` reads a fixture tree instead of the live sysfs
  (default `/sys`). The unit tests use it; a fixture result is not evidence
  about any real host.

## Tests

```sh
python3 -m unittest discover -s tests
```

The suite pins the failure modes that matter: unassigned memory BARs
(including zero-start rows and a partially unassigned BAR5), missing driver,
llvmpipe-only Vulkan, unauthorized/USB-only/unknown tunnel states, missing
vulkaninfo, unreadable BARs, unverified topology with and without
`--device`, and the no-eGPU host that must report incomplete rather than
pass.
