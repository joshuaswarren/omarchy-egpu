# Measurements

One inference benchmark is recorded: the RX 7600 on a 14-inch M2 Max MacBook Pro ran llama.cpp Vulkan (RADV) with Qwen2.5-7B Q4_K_M at pp512 964.6 t/s and tg128 31.1 t/s on 2026-10-22. It needs local device-tree and kernel changes that are not upstream yet.

- [RX 7600 llama.cpp Vulkan record, 2026-10-22](2026-10-22-rx7600-m2max-llamacpp-vulkan.md): versions, command, and results. Single host, three repetitions; the matched Metal baseline has not run.
- [Current RX 7600 result on the 14-inch M2 Max MacBook Pro](../hosts/m2-max/README.md): driver initialization, the device-tree window fix, and what remains untested.
- [13:10Z RX 7600 transport snapshot](2026-10-22-rx7600-14in-m2max-transport.md): historical PCI enumeration, BAR assignment errors, and idle link readings.
- [Method](method.md): required metadata and commands for future inference measurements.
