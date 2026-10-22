# llama.cpp Vulkan on an external GPU

This recipe is conditional. First require assigned memory BARs, a bound GPU driver, clean kernel logs, and the external card in `vulkaninfo --summary`. It is not a measured result for any card in this repo.

## Build with Vulkan enabled

Use your card guide for its firmware and Vulkan ICD. On Omarchy, install the build tools and headers:

```bash
sudo pacman -S --needed base-devel cmake git vulkan-headers vulkan-icd-loader vulkan-tools shaderc spirv-headers
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
git rev-parse HEAD
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DGGML_VULKAN=ON
cmake --build build --config Release -j 4
```

These commands follow the [upstream Vulkan build instructions](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md#vulkan). Record the source commit printed above. Do not assume a distribution's `llama.cpp` binary includes the Vulkan backend.

## Select the external card

```bash
./build/bin/llama-cli --list-devices
./build/bin/llama-bench --help
```

Copy the external GPU's backend device name from that output. Set `GPU_DEVICE` to that exact name. Set `MODEL` to an existing 7-8B Q4 GGUF file you may use, and record its SHA-256. Model weights are not supplied here.

```bash
GPU_DEVICE='Vulkan0'
MODEL="$HOME/models/model-Q4_K_M.gguf"
sha256sum "$MODEL"
./build/bin/llama-bench --device "$GPU_DEVICE" -m "$MODEL" -ngl 99 -p 512 -n 128 -r 3
```

`Vulkan0` is an example device name, not a fixed card selection. Confirm the log names your external card and offloads the model layers to it. A CPU fallback or the integrated GPU does not qualify. If the selected model or context exceeds VRAM, reduce the workload and record that change; do not present partial offload as a full-GPU result.

Report prefill and decode separately, with all repetitions and the exact command. Use the [measurement method](../benchmarks/method.md) for kernel, Mesa, power, link, and model metadata. A successful `vulkaninfo` probe alone is not an inference benchmark.
