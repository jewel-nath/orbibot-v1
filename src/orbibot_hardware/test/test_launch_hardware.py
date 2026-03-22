# T2: Launch test — verify hardware launch description builds.

import pytest
from launch import LaunchDescription
import os


def test_launch_module_importable():
    """Ensure hardware.launch can be loaded (no syntax/import errors)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "hardware_launch",
        os.path.join(os.path.dirname(__file__), '..', 'launch', 'hardware.launch.py')
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ld = mod.generate_launch_description()
    assert isinstance(ld, LaunchDescription)
