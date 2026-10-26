# RX 9070 on a 14-inch M2 Max MacBook Pro: RADV_PERFTEST and llama.cpp decode, 2026-10-26

MEASURED: `RADV_PERFTEST=dmashaders` raises llama.cpp Vulkan decode on the RX 9070 from about 24.8 to 32.9 tok/s (+32.6 percent) on one boot, in a four-arm design where every arm ran once in every position. The flag pair `nogttspill,dmashaders` measured +28.1 and +27.3 percent on two earlier boots, and +32.6 percent on the third. `nogttspill` adds nothing on top of `dmashaders` here. One card, one model, one quantization, one host. Nothing here says why the flag helps.

All three boots used the same local kernel and amdgpu module, the same llama.cpp build and the same unpatched Mesa package. The module changes memory placement; see [patches.md](../cards/rx-9070/patches.md). This is a result for that stack, not for a stock system.

## Setup

| Item | Value |
|---|---|
| Host | 14-inch M2 Max MacBook Pro (2023), aarch64, Arch Linux ARM, 16 KiB pages |
| Kernel | `7.1.12-2-20261013.18-egpu-ARCH`, local changes as described on the [RX 9070 patches page](../cards/rx-9070/patches.md) |
| amdgpu module | SHA-256 `1388ccacb751cb680608b517d8f3e0d62551a9d454c5f5e4ad08709b39e3eb3e`, loaded with no parameters; all four local parameters at their defaults |
| GPU | RX 9070 (Navi 48, `1002:7550`), 16304 MiB VRAM |
| Mesa | Arch Linux ARM `vulkan-radeon` 26.2.5-arch1.1, `libvulkan_radeon.so` SHA-256 `e4acbd79bac75cdbc7a0bf33a2b49324217abd420b72e1ec55d5dc7e356947a6`, byte-identical to the file inside the package |
| llama.cpp | build 11449, commit `65840ed53`, Vulkan backend |
| Model | Qwen2.5-7B-Instruct Q4_K_M, two GGUF parts, part 1 SHA-256 `dfce12e3862a5283ccfb88221b48480e58745165de856439950d0f22590580db` |
| Measurement | `llama-bench -p 0 -n 128 -r 3 -ngl 99 -fa 1`, test `tg128`; each value below is one `llama-bench` run (its own 3-repeat mean) |
| Arms | A: `RADV_PERFTEST` unset (`env -u`). N: `nogttspill`. D: `dmashaders`. B: `nogttspill,dmashaders` |
| Before timing | Output check: `llama-cli --temp 0 --seed 1 -n 64`, same prompt, text equal across arms (hash `51287c6e…` on all three boots). The flag names must appear in the loaded library. |

## Rule fixed before the split run

For each flag arm X, compared with the default arm A: KEEP only if mean(X) is at least 3 percent above mean(A), the gain is more than 3 times `sd_max`, and X is higher than A in every round. `sd_max` is the largest of every `llama-bench` standard deviation of the compared runs and the sample standard deviation of the four per-round means of each arm. A flag is named as the cause only if it is itself KEEP and within 3 percent of B; a flag more than 3 percent above B would be reported as a negative interaction. The order was balanced: four rounds, every arm once in every position, every ordered neighbour pair once.

## Result 1: two-arm A/B, two boots (A B B A A B)

| Boot | A runs (tok/s) | A mean | B runs | B mean | Gain |
|---|---|---:|---|---:|---:|
| 1 | 25.74, 25.90, 24.75 | 25.46 | 32.60, 32.56, 32.66 | 32.61 | +28.1 percent |
| 2 (14 minutes later) | 25.81, 24.98, 25.81 | 25.53 | 32.56, 32.49, 32.44 | 32.50 | +27.3 percent |

On both boots B was higher than A in every pair, and the gain was more than 3 times the largest standard deviation (4.1 times on boot 1, 5.4 times on boot 2). KEEP both times.

## Result 2: four-arm split, one boot

| Round | Order | A | N | D | B |
|---|---|---:|---:|---:|---:|
| 1 | A N B D | 23.68 | 26.55 | 32.86 | 32.94 |
| 2 | N D A B | 24.45 | 26.48 | 32.88 | 32.94 |
| 3 | D B N A | 24.38 | 26.50 | 32.76 | 32.71 |
| 4 | B A D N | 26.61 | 26.57 | 32.97 | 32.87 |
| Mean | | 24.78 | 26.52 | 32.87 | 32.86 |
| Gain over A | | | +7.0 percent | +32.6 percent | +32.6 percent |

`sd_max` is 1.27 (the sample standard deviation of A's four round means).

- D: KEEP. Higher than that round's A by 9.18, 8.43, 8.38 and 6.36 tok/s.
- B: KEEP. D and B differ by 0.01 tok/s.
- N: DROP, on two parts of the rule. It is not higher than A in round 4 (26.57 against 26.61), and its gain of 1.74 tok/s is under 3 times `sd_max` (3.81). Both failures come from the same A run, the 26.61 in round 4, which also sets `sd_max`.
- Attribution by the rule: only D is within 3 percent of B, and D is KEEP, so `dmashaders` carries the gain.

What the N result does not show: N's four values are flat at about 26.5 and A's first three are about 24.2. Either `nogttspill` alone gives a small gain, or the default arm has a second mode near 26.6. This experiment cannot tell which. The pre-registered verdict stands. The default arm is the unstable one on all three boots (25.46, 25.53, 24.78); the flagged arms are not (32.61, 32.50, 32.86 for B).

## Context logged on the split boot (read-only, identical before and after)

- Card link: 32.0 GT/s x16 (maximum 32.0 GT/s x16). Bridges toward the host: 32.0 GT/s x16, then 5.0 GT/s x4 (maximum 32.0 GT/s x16), 5.0 GT/s x4 (maximum 16.0 GT/s x4), 2.5 GT/s x4 (maximum 2.5 GT/s x4), and a root port at 2.5 GT/s x16. The slowest recorded segment is 2.5 GT/s x4. Which segment is the Thunderbolt tunnel is not established.
- Memory as the kernel reports it: `mem_info_vram_total` 17095983104, **`mem_info_vis_vram_total` 268435456 (256 MiB visible of 16304 MiB)**, `mem_info_gtt_total` 50595495936. The log has `Not enough PCI address space for a large BAR`, `Detected VRAM RAM=16304M, BAR=256M` and `PCIE atomic ops is not supported`.
- Consequence: the proposed Mesa change on the [RX 7600 patches page](../cards/rx-7600/patches.md) switches on a visible VRAM size of zero. This card reports 256 MiB, so that condition would not match here, yet `dmashaders` gives +32.6 percent. Not tested: that change on this card, and whether Mesa's visible-size value equals this sysfs value.
- amdgpu parameters: `egpu_vram_cpu` 0, `egpu_psp_vram` 0, `egpu_gtt_wc` -1, `egpu_vram_map` 0, `rebar` -1. No run varied them. Error-like amdgpu kernel lines: 0 before and after.

## What this does not show

- Why `dmashaders` helps. The 256 MiB visible window and the tunnel are the obvious suspects; no run resized the BAR or changed the link.
- Any other card, model, quantization, prompt-processing speed, context length, batch size or API than llama.cpp Vulkan token generation. Graphics clients on the same card were not tested.
- A stock amdgpu module or a stock kernel; the module here changes memory placement. The result has not been repeated on any other module build.
- Whether Mesa ignores an unknown flag name (not tested). Both names occur once in the loaded library.
- Output quality beyond equal text for a 64-token greedy generation.
- `GGML_VK_DISABLE_MMVQ` and `GGML_VK_ALLOW_GRAPHICS_QUEUE`, which the 7600 page also sets, were not tried on this card.

## Reproduce

Set the variable for the one command, not for the session:

```bash
RADV_PERFTEST=dmashaders GGML_VK_VISIBLE_DEVICES=0 llama-bench \
  -m qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf -p 0 -n 128 -r 3 -ngl 99 -fa 1
```

The runner and decision script that produced the numbers, and the raw result files, are kept by the lab. Hashes of what this page was written from: two-arm runner `94107f3834bb1883bbbcdd3a93cf473c1c6807f23acfeee39335709334da202e`; split runner `6c64781abc60ad37f08a6d54262285223c8e82b3bee44bcbe3a1987a44467f7b`; decision script `a94281d8ef5b7ef3c772b29f6be9529ac77bda5423a5e35f8502df62435a7352`; `results.tsv` of boot 1 `a4ae36a0fa554ff0d916d6ca74ef4431be0a34c56eff8b74b34cbc5831a7cd5d`, of boot 2 `66e8ddbd32cbb206997aec3df6c54b79887cecccecaa4455c9c9cec3c413f0df`, of the split `a83650cdda0bef95d2b207ba618fbc4d4436801061395e32fd426da8a5eda4c0`.
