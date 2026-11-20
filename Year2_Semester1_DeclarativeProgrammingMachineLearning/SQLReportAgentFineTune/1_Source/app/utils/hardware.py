"""Hardware detection and Apple Silicon resource profiling."""

import os
import platform
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class HardwareInfo:
    """Hardware capabilities summary."""
    platform: str
    machine: str
    chip: str
    total_ram_gb: float
    cpu_cores: int
    is_apple_silicon: bool
    mlx_available: bool
    mlx_device: str
    metal_gpu_enabled: bool


def get_hardware_info() -> HardwareInfo:
    """Inspects local system and returns hardware specs."""
    plat = platform.platform()
    machine = platform.machine()
    is_apple_silicon = platform.system() == "Darwin" and machine in ("arm64", "aarch64")

    # Detect CPU Chip
    chip = "Unknown"
    if is_apple_silicon:
        try:
            res = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                chip = res.stdout.strip()
        except Exception:
            chip = "Apple Silicon"

    # Detect RAM
    total_ram_gb = 0.0
    if platform.system() == "Darwin":
        try:
            res = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                total_ram_gb = round(int(res.stdout.strip()) / (1024**3), 2)
        except Exception:
            total_ram_gb = 16.0
    else:
        total_ram_gb = 16.0

    cpu_cores = os.cpu_count() or 4

    # MLX & Metal Support
    mlx_available = False
    mlx_device = "none"
    metal_gpu_enabled = False
    try:
        import mlx.core as mx
        mlx_available = True
        dev = mx.default_device()
        mlx_device = str(dev)
        metal_gpu_enabled = "gpu" in mlx_device.lower()
    except ImportError:
        pass

    return HardwareInfo(
        platform=plat,
        machine=machine,
        chip=chip,
        total_ram_gb=total_ram_gb,
        cpu_cores=cpu_cores,
        is_apple_silicon=is_apple_silicon,
        mlx_available=mlx_available,
        mlx_device=mlx_device,
        metal_gpu_enabled=metal_gpu_enabled,
    )
