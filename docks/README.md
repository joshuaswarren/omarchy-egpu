# Docks, power, and cables

A dock needs a working PCIe tunnel, a powered slot, and the card's auxiliary power. USB-C describes the connector. It does not establish PCIe support.

| Dock or enclosure | Role | What this repo verifies |
|---|---|---|
| OwlTree M.2-to-PCIe x16 dock, ASM2464PD | USB4 bridge plus an external ATX supply and GPU adapter | RX 7600 PCI enumeration on a 14-inch M2 Max MacBook Pro; BAR allocation still fails |
| Maskedfish MK-Q1L | Thunderbolt PCIe dock | No card-specific Linux runtime result published here |
| Sonnet Breakaway Box 850 T5 | Powered Thunderbolt 5 eGPU enclosure | Vendor specifications only; no Linux card runtime result published here |
| ACASIS TB501 Pro | Thunderbolt 5 M.2 NVMe enclosure | Storage enclosure, not a direct x16 GPU slot; any PCIe riser adaptation is unverified here |

## Connect safely

1. Turn the enclosure and PSU off before seating the card or changing power cables. Use only the PSU's matching modular cables.
2. Connect the dock's ATX input and every auxiliary connector required by the exact card. Do not substitute CPU EPS cables for PCIe power cables.
3. Secure the card and adapter. Keep exposed boards clear of metal and provide cooling. Confirm the PSU and slot power ratings against the card's manual.
4. Power the card and dock before attaching the host cable. Use a certified Thunderbolt or USB4 data cable with the required rating. A charging-only cable cannot create a tunnel.
5. Inspect the diagnostic output before starting a compute job. Do not unplug the dock while a process uses its GPU or storage.

No measured board power is available in the current attachment data. PSU capacity and vendor board-power ratings are not measured draw.

## Sonnet specifications

[Sonnet's technical specifications](https://www.sonnettech.com/product/breakaway-box-850t5/techspecs.html) list an 850 W supply, three 8-pin or one 16-pin GPU power connection, and a 0.8 m Thunderbolt 5 cable. The card envelope is 345 x 155 x 70 mm. Check your card's dimensions and connectors before buying or connecting anything.

Sonnet lists RTX 50/40/30 and RX 9000/7000/6000 series, but does not list Arc Pro B60 on that page. Its stated operating-system support does not validate Omarchy. A Thunderbolt 5 enclosure does not upgrade an older host to Thunderbolt 5 speeds.

## ACASIS scope

[ACASIS describes the TB501 Pro as an M.2 NVMe SSD enclosure](https://www.acasis.com/products/acasis-80gbps-m-2-nvme-ssd-enclosure-compatible-with-thunderbolt-5-copy). It supplies neither a direct GPU slot nor verified GPU auxiliary power in this guide. Do not present its advertised 80 Gb/s storage link as an eGPU result.

Stock USB3 mass-storage fallback on an NVMe bridge is not a general GPU connection. This repository does not flash bridge firmware or claim that an untested adapter works.
