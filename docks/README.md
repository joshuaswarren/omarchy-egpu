# Docks, power, and cables

A dock needs a working PCIe tunnel, a powered slot, and the card's auxiliary power. USB-C describes the connector. It does not establish PCIe support.

| Dock or enclosure | Availability | Role | What this repo verifies |
|---|---|---|---|
| OwlTree M.2-to-PCIe x16 dock with Rosewill ASM2464PD enclosure | Used in the measured RX 7600 probes | USB4 bridge, GPU adapter, and external ATX supply | RX 7600 driver initialization and a llama.cpp Vulkan run on a 14-inch M2 Max MacBook Pro, card attached at boot; hot-plug untested |
| Maskedfish MK-Q1L | Previously available | Thunderbolt PCIe dock | No card-specific Linux runtime result published here |
| Sonnet Breakaway Box 850 T5 | Arrival reported on 2026-10-22; used in the measured Arc Pro B60 run | Thunderbolt 5 eGPU enclosure with its own 850 W supply | Arc Pro B60 Vulkan inference on a 16-inch M1 Max MacBook Pro, behind unpublished kernel changes |
| ACASIS TB501 Pro | Not confirmed in this update | Thunderbolt 5 M.2 NVMe enclosure | No direct x16 GPU slot; any PCIe riser adaptation is unverified here |
| ADT-Link UT3G | Arrival reported on 2026-10-22; RM750x PSU reported available | USB4/Thunderbolt PCIe adapter with an external ATX supply | No card runtime result or tinygrad USB3 compatibility established here |

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

## UT3G transport boundary

The [UT3G vendor specification](https://www.adt.link/product/UT3G.html) requires a Thunderbolt 3/4 or USB4 host. Its Q&A explicitly excludes USB 2.0 and USB 3.0/3.1/3.2. Receipt of the board does not establish a tinygrad USB3 path. The exact board revision, bridge firmware, and tinygrad compatibility still need verification.

The UT3G uses external ATX power. The Sonnet has its own supply. Do not treat their power wiring as interchangeable. This repository does not authorize or perform a bridge firmware flash.


## ACASIS scope

[ACASIS describes the TB501 Pro as an M.2 NVMe SSD enclosure](https://www.acasis.com/products/acasis-80gbps-m-2-nvme-ssd-enclosure-compatible-with-thunderbolt-5-copy). It supplies neither a direct GPU slot nor verified GPU auxiliary power in this guide. Do not present its advertised 80 Gb/s storage link as an eGPU result.

Stock USB3 mass-storage fallback on an NVMe bridge is not a general GPU connection. This repository does not flash bridge firmware or claim that an untested adapter works.
