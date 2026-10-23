# Host setup

| Host | Guide | Main constraint |
|---|---|---|
| x86 Omarchy | [x86](x86/) | Host firmware must expose PCIe tunneling and enough BAR space |
| 13-inch M1 MacBook Pro | [Apple Silicon](apple-silicon/) | 16 KiB host pages; limited PCI aperture |
| 16-inch M1 Max MacBook Pro | [Apple Silicon](apple-silicon/) | Shared driver build is not a host runtime test |
| 14-inch M2 Max MacBook Pro | [M2 Max](m2-max/) | RX 7600 runs llama.cpp Vulkan with local device-tree and kernel changes; cable hot-plug untested |
| M6 Mac mini | [M6](m6/) | Host transport support remains in progress |

No universal kernel parameter fixes these cases. Record the existing command line before changing anything:

```bash
cat /proc/cmdline
uname -r
getconf PAGESIZE
lspci -Dnnk
lspci -Dtv
boltctl list
```

A missing `boltctl` command means the `bolt` package is absent, not that the host lacks a tunnel. The diagnostic also reads sysfs. Use your system's authorization policy; this repository never disables IOMMU isolation or Thunderbolt security.
