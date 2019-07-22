import os
from typing import Tuple, Optional

# This table is a simplified version of https://github.com/NVIDIA/nvidia-docker/wiki/CUDA
# To interpret this data, cuda version 10.0 requires driver > 410.58
# We simplify the logic so that ANY supported card will work with the version we require
# e.g., if two cards are supported with different minimum versions, we only support the highest minimum
# At time of edit, we have explicitly tested through version 430
# Note that we don't support CUDA 8, but we don't disable it (yet)
CUDA_DRIVER_VERSION_LOOKUP = {8: {0: (375, 51)},
                              9: {0: (384, 81),
                                  1: (387, 26),
                                  2: (396, 26)},
                              10: {0: (410, 58),
                                   1: (418, 39)}}


def _parse_version_str(version: Optional[str]) -> Optional[Tuple[int, int]]:
    result = None
    if version:
        version_nums = version.strip().split('.')
        if len(version_nums) == 2:
            try:
                result = (int(version_nums[0]), int(version_nums[1]))
            except ValueError:
                # Split two values, but they aren't convertible to ints
                pass
    return result


def should_launch_with_cuda_support(cuda_version: Optional[str]) -> Tuple[bool, str]:
    """Method to test whether the host has NVIDIA drivers, the Project is CUDA enabled, and the two are compatible.

        Args:
            cuda_version(str): Version of CUDA in the Project container, e.g. 9.2, 10.0

        Returns:
            bool
    """
    host_driver_version = os.environ.get('NVIDIA_DRIVER_VERSION')
    host_driver_version_nums = _parse_version_str(host_driver_version)
    reason = "Host does not have NVIDIA drivers configured"
    launch_with_cuda = False
    if host_driver_version_nums:
        reason = "Project is not GPU enabled"
        if cuda_version:
            # host has NVIDIA drivers installed
            cuda_version_nums = _parse_version_str(cuda_version)
            reason = "Failed to parse required CUDA version from Project configuration"
            if cuda_version_nums:
                # project has properly configured CUDA requirement
                driver_lookup = CUDA_DRIVER_VERSION_LOOKUP.get(cuda_version_nums[0])
                reason = f"Project CUDA version ({cuda_version}) not supported"
                if driver_lookup:
                    # Provided major version is supported
                    min_driver = driver_lookup.get(cuda_version_nums[1])
                    reason = f"Project CUDA version ({cuda_version}) not supported"
                    if min_driver:
                        project_major = min_driver[0]
                        project_minor = min_driver[1]
                        host_major = host_driver_version_nums[0]
                        host_minor = host_driver_version_nums[1]
                        reason = f"Project CUDA version ({cuda_version}) is not compatible with host" \
                            f" driver version ({host_driver_version})"
                        if host_major > project_major or (host_major == project_major and host_minor >= project_minor):
                            launch_with_cuda = True
                            reason = f"Project CUDA version ({cuda_version}) is compatible with host" \
                                f" driver version ({host_driver_version})"

    return launch_with_cuda, reason
