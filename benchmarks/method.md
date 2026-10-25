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

## Matched Linux Vulkan and macOS Metal runs

Use the same method for each eGPU once its driver, hardware Vulkan probe and compute test pass. The Linux run uses the external card. The macOS run uses that Mac's own Apple GPU through Metal. Use the same physical Mac for both runs when it supports both operating systems. Record the exact Mac model and external card.

This compares two complete GPU configurations. It does not isolate operating-system overhead. For an integrated-GPU comparison, such as a future M6 run, both backends must use that same integrated GPU. No M6 or eGPU result is implied by this method.

1. Build the same llama.cpp Git revision on both systems. Use the same 7-8B Q4 GGUF file and confirm identical SHA-256 checksums. Record the compiler, build flags, OS, driver, and GPU selected.
2. Keep model offload, prompt/decode lengths, CPU threads, batch sizes, KV-cache types and flash-attention policy identical. Use four CPU threads for this baseline. Confirm full model-layer offload to the selected GPU; exclude CPU fallback and split-device runs.
3. Use a scheduled measurement window with no other GPU workload. Record power mode, thermals, power telemetry where available, and the Linux tunnel/link readings. The integrated Metal GPU has no external PCIe link; record that field as not applicable.
4. Run three warm-up repetitions, then allow the same 60-second idle interval on both systems. Run five timed repetitions with llama-bench's built-in warm-up still enabled. Retain the raw JSON samples and stderr.
5. Report prefill at 512 and 2048 tokens and decode at 128 tokens separately. Publish the mean, standard deviation, sample count and raw samples. Calculate a Linux-Vulkan/macOS-Metal ratio only for matched rows.

From the same source revision, build Linux Vulkan with:

```bash
cmake -S . -B build-vulkan -DCMAKE_BUILD_TYPE=Release -DGGML_VULKAN=1
cmake --build build-vulkan --config Release -j 4
./build-vulkan/bin/llama-bench --list-devices
```

Build macOS Metal with:

```bash
cmake -S . -B build-metal -DCMAKE_BUILD_TYPE=Release -DGGML_METAL=ON -DGGML_VULKAN=OFF
cmake --build build-metal --config Release -j 4
./build-metal/bin/llama-bench --list-devices
```

On each system, set `BENCH` to its built llama-bench executable, `MODEL` to the matching GGUF file, and `DEVICE` to the exact name from that build's device list. Do not assume the external card is Vulkan device zero. Use the same command parameters:

```bash
"$BENCH" -m "$MODEL" --device "$DEVICE" -sm none -ngl 99 \
  -p 512,2048 -n 128 -t 4 -b 2048 -ub 512 -ctk f16 -ctv f16 -fa off \
  -r 3 -o json > warmup.json 2> warmup.log
# Wait the matched 60-second idle interval before the timed command.
"$BENCH" -m "$MODEL" --device "$DEVICE" -sm none -ngl 99 \
  -p 512,2048 -n 128 -t 4 -b 2048 -ub 512 -ctk f16 -ctv f16 -fa off \
  -r 5 -o json > timed.json 2> timed.log
```

Run the commands in a new result directory on each system so they do not overwrite an earlier run. If the model, memory settings or backend fails, retain that failure. Do not silently reduce offload or change the paired workload.

The [upstream build guide](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md) defines the backend flags. The [llama-bench guide](https://github.com/ggml-org/llama.cpp/blob/master/tools/llama-bench/README.md) defines the options and JSON sample fields. These commands describe a future run; they have not produced a benchmark result in this repository.

## What a row is allowed to claim

- Enumeration means the card appears in `lspci` behind the dock. Says nothing
  about the driver.
- Driver bound means `lspci -k` shows `Kernel driver in use` and the kernel log
  is clean. Says nothing about throughput.
- Measured performance means the workload above completed its repetitions with
  no GPU hang, ring timeout, or error in the kernel log. Only then do numbers
  enter this directory, with every metadata field above.

A failed attach, a driver that never binds, or a wedged host is never
recorded as a benchmark. It is recorded as a blocked status in the card and
host guides.

## Card vs built-in GPU on Linux (2026-10-23 runs)

This is not the matched Metal comparison above; it has not been run. Both sides
here are Linux Vulkan on the same Mac: the integrated Apple GPU through Mesa
Honeykrisp, and the external card through its tunnel. Same llama.cpp commit
(`65840ed53`), same models. On the 14-inch M2 Max, the RX 7600 was about 3.5 to
4.1 times faster at prompt processing and tied on decode. On the 16-inch M1
Max, the Arc Pro B60 was about 5.7 to 7.4 times faster at prompt processing
and about 1.9 to 2.1 times faster at decode.

| Mac and card | Model | Built-in GPU on Linux, pp512 / tg128 | Card over USB4, pp512 / tg128 |
|---|---|---|---|
| 14-inch M2 Max, RX 7600 | Llama-2-7B Q4_0, fa0 | 293.96 / 38.64 | 1024.5 to 1025.1 / 38.15 to 38.18 |
| 14-inch M2 Max, RX 7600 | Llama-2-7B Q4_0, fa1 | 304.05 / 40.44 | 1242.3 to 1259.4 / 40.95 to 41.07 |
| 14-inch M2 Max, RX 7600 | Qwen2.5-7B Q4_K_M, fa0 | 245.74 / 29.82 | 945.81 / 28.93 (repeats 29.57, 29.49) |
| 14-inch M2 Max, RX 7600 | Qwen2.5-7B Q4_K_M, fa1 | 240.91 / 30.35 | 967.59 / 28.90 (repeats 31.86, 31.39) |
| 16-inch M1 Max, Arc Pro B60 | Llama-2-7B Q4_0, fa0 | 233.76 / 33.16 | 1330.26 / 63.80 |
| 16-inch M1 Max, Arc Pro B60 | Llama-2-7B Q4_0, fa1 | 240.08 / 34.28 | 1418.34 / 65.96 |
| 16-inch M1 Max, Arc Pro B60 | Qwen2.5-7B Q4_K_M, fa0 | 194.36 / 26.10 | 1429.87 / 55.78 |
| 16-inch M1 Max, Arc Pro B60 | Qwen2.5-7B Q4_K_M, fa1 | 197.54 / 26.34 | 1439.92 / 55.88 |

The built-in rows are five repetitions each, from llama.cpp commit `65840ed53`
with Mesa 26.2.4, run on the 14-inch machine with the same kernel as its card
runs, and on the 16-inch machine with its stock kernel while the B60 runs used
the patched kernel. Each Mac built its own ggml libraries from that commit,
and the two Macs use different builds of the same Mesa version, so the two
built-in sets are not strictly comparable with each other. The card rows are
three repetitions: RX 7600 with Mesa 26.2.5 RADV, and B60 with a private Mesa
26.2.4 build and the private driver patches described in the
[B60 record](2026-10-23-b60-m1max-llamacpp-vulkan.md). The B60 Qwen2.5 rows
match the built-in file by name and size only. The Llama-2 rows use the
`dmashaders` setting from the [headline
record](2026-10-22-rx7600-m2max-llamacpp-vulkan.md). The Qwen2.5 card rows are
the 12-CPU rerun, first run of each setting, with the later repeats in
brackets. Decode on that model moved between 28.9 and 31.9 t/s from run to
run, so it overlaps the built-in 29.8 to 30.4. The Qwen2.5 file name is the
same on both. The Llama-2 file was staged at SHA-256 `78b8f977...` for the
card runs and the built-in run used that same hash, though the card run logs
do not repeat it.

For reference, the public llama.cpp
[Apple Silicon thread](https://github.com/ggml-org/llama.cpp/discussions/4167)
lists Metal values for the same Llama-2-7B Q4_0 of pp512 537.60 and tg128
60.99 on an M2 Max with 30 GPU cores, and 671.31 and 65.95 with 38 cores. For
the M1 Max: 400.26 and 54.61 with 24 cores, and 530.06 and 61.19 with 32
cores. Those values are well above the Linux built-in runs (for example 61.19
against 34.28 tg128 on the M1 Max). Against Metal, which is what a Mac user
gets on macOS, the B60 decodes only about 4 to 21 percent faster than the
thread's M1 Max rows, and the RX 7600 decodes well below the thread's M2 Max
rows. The B60 decode uses private driver patches that are not upstream. Our
machines' core counts were not recorded, so both thread values are shown. The
thread used a different llama.cpp commit, did not state a flash-attention
setting for these rows, and did not run on our machines. Larger models are
where a 24 GiB card should matter most; there is no built-in-GPU number for
those either.

## Ledger

| File | Card | Type | Status |
|---|---|---|---|
| [2026-10-22-rx7600-14in-m2max-transport.md](2026-10-22-rx7600-14in-m2max-transport.md) | RX 7600 | Transport record (enumeration, BARs, link). Not a performance benchmark | MEASURED |
| [2026-10-22-rx7600-m2max-llamacpp-vulkan.md](2026-10-22-rx7600-m2max-llamacpp-vulkan.md) | RX 7600 | llama.cpp Vulkan inference, single-host (3 repetitions; alternating A/B tests; matched Metal baseline not run) | MEASURED |
| [2026-10-23-rx7600-m2max-model-sweep.md](2026-10-23-rx7600-m2max-model-sweep.md) | RX 7600 | Model sweeps plus a dispatch-latency probe. The first sweeps ran under co-running load; the dmashaders sweep ran at load 0.3 or below. Not a power-matched comparison | MEASURED |
| [2026-10-23-b60-m1max-llamacpp-vulkan.md](2026-10-23-b60-m1max-llamacpp-vulkan.md) | Arc Pro B60 | llama.cpp Vulkan via ANV, single-host, 3 repetitions; the first run on one CPU, later runs on 10 CPUs; the buffer-placement results need private patches | MEASURED |

The working RX 7600 run is documented in the [host guide](../hosts/m2-max/README.md) and its [benchmark record](2026-10-22-rx7600-m2max-llamacpp-vulkan.md); it depends on unpublished kernel and device-tree changes.
