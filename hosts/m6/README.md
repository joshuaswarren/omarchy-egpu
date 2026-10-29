# M6 Mac mini

NOT MEASURED: Thunderbolt host support is still in progress. This repository has no M6-specific Linux eGPU build, card bind, Vulkan probe, or inference measurement.

The M1/M2 shared kernel build does not establish M6 support. Do not install its modules on an M6 or copy its device tree. No kernel parameters or BAR workaround are validated here for the M6.

The card recipes become applicable only after a compatible Linux host kernel establishes the transport, assigns the card's BARs, and binds the correct driver. No firmware or operating-system image is distributed here.
