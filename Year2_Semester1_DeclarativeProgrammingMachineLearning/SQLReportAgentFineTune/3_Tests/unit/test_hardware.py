"""Unit tests for Apple Silicon and MLX hardware profiling."""

from app.utils.hardware import HardwareInfo, get_hardware_info


def test_hardware_detection():
    hw = get_hardware_info()
    assert isinstance(hw, HardwareInfo)
    assert hw.cpu_cores > 0
    assert hw.total_ram_gb > 0
    assert hw.platform != ""
    assert isinstance(hw.is_apple_silicon, bool)
    assert isinstance(hw.mlx_available, bool)
