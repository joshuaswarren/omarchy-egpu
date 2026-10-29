# Source this in a user run (env -i ... bash -c '. vulkan-env.sh; cmd') to use the profile-private 615 userspace. Nothing system-wide reads it.
_p=/usr/lib/nvidia-egpu-615.78.08
export LD_LIBRARY_PATH="$_p/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export VK_DRIVER_FILES="$_p/share/vulkan/icd.d/nvidia_icd.json"
export __EGL_VENDOR_LIBRARY_FILENAMES="$_p/share/glvnd/egl_vendor.d/10_nvidia.json"
unset _p
