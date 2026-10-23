# Measurements

Inference benchmarks are recorded for two cards on two Apple Silicon hosts, both with llama.cpp Vulkan: the RX 7600 on a 14-inch M2 Max MacBook Pro (RADV) and the Arc Pro B60 on a 16-inch M1 Max MacBook Pro (ANV). Both need local device-tree and kernel changes that are not upstream yet. The fastest numbers also need a driver-side buffer-placement change: an environment setting for RADV, and private patches for ANV.

- [RX 7600 llama.cpp Vulkan record, 2026-10-22](2026-10-22-rx7600-m2max-llamacpp-vulkan.md): versions, command, and results, including the 12-CPU rerun, the native comparison, the refuted causes, the dmashaders result and the window l measurements (alternating A/B, buffer placement, patched build). Single host, three repetitions; the matched Metal baseline has not run.
- [RX 7600 model sweep and dispatch-latency probe, 2026-10-23](2026-10-23-rx7600-m2max-model-sweep.md): four models with flash attention on and off, a direct VRAM-versus-GTT latency measurement, and the four-model dmashaders sweep.
- [Arc Pro B60 llama.cpp Vulkan record, 2026-10-23](2026-10-23-b60-m1max-llamacpp-vulkan.md): the Intel result on a 16-inch M1 Max MacBook Pro: the required workarounds, the 10-CPU rerun, the driver-buffer result that needs private patches, and Qwen3.8-27B running fully on the card.
- [Current RX 7600 result on the 14-inch M2 Max MacBook Pro](../hosts/m2-max/README.md): driver initialization, the device-tree window fix, and what remains untested.
- [13:10Z RX 7600 transport snapshot](2026-10-22-rx7600-14in-m2max-transport.md): historical PCI enumeration, BAR assignment errors, and idle link readings.
- [Method](method.md): required metadata and commands for future inference measurements.
