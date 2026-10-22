# Benchmark method

How a result gets into this directory. Every file here is either a method
page or a record of a real run on our hardware. We do not publish estimated,
projected, or vendor-quoted numbers as measurements.

## What every record must carry

| Field | Requirement |
|---|---|
| Host | Machine by model, page size (`getconf PAGESIZE`), boot date |
| Kernel | Exact `uname -r` string |
| GPU driver | Kernel driver name and version (for amdgpu: the kernel itself); for Vulkan results, the ICD file used and `vulkaninfo --summary` driver info |
| Link | `LnkCap` and `LnkSta` for the card and its upstream bridges, at idle **and under load**; tunnel speed from `boltctl` where present |
| Power | PSU model, connectors used, and a 1 Hz power and temperature log for the whole run when telemetry exists. If power was not recorded, the record says `not recorded`. A vendor spec sheet never substitutes for a measurement |
| Command | The complete command line, including thread count and repeat count |
| Model | Model, quantization, and the GGUF or weight checksum |
| Conditions | Stock clocks and power limits, recorded and never changed; warm-up runs; no other GPU user (`fuser -v /dev/dri/*` empty); idle gate before each run |

An unknown field stays visibly unknown in the record. It is never filled with
an inference or a spec-sheet value.

## Standard workload

Language-model throughput on Vulkan (any vendor):

```bash
# environment capture first (kernel, driver, link, power setup), then:
llama-bench -m <model>-Q4_K_M.gguf -ngl 99 -p 512,2048 -n 128 -r 5 -t $(nproc)
```

Before each timed run:

```bash
awk '{exit !($1<1.0)}' /proc/loadavg    # idle gate: fails while the host is busy
fuser -v /dev/dri/*                      # must list nothing
```

Three warm-up prompts, five timed repetitions, 60 s idle between runs. Never
merge results from different transports (PCIe tunnel vs USB3 bridge) into one
ranking; label the transport on every row.

## What a row is allowed to claim

- **Enumeration:** the card appears in `lspci` behind the dock. Says nothing
  about the driver.
- **Driver bound:** `lspci -k` shows `Kernel driver in use` and the kernel log
  is clean. Says nothing about throughput.
- **Measured performance:** the workload above completed its repetitions with
  no GPU hang, ring timeout, or error in the kernel log. Only then do numbers
  enter this directory, with every metadata field above.

A failed attach, a driver that never binds, or a wedged host is never
recorded as a benchmark. It is recorded as a blocked status in the card and
host guides.

## Ledger

| File | Card | Type | Status |
|---|---|---|---|
| [2026-10-22-rx7600-14in-m2max-transport.md](2026-10-22-rx7600-14in-m2max-transport.md) | RX 7600 | Transport record (enumeration, BARs, link). Not a performance benchmark | MEASURED |

No performance row exists yet for any card. When one lands, it appears here
with its full environment block.
