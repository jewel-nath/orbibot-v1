# T2: Launch test — verify hardware launch description builds.

import pytest
from launch import LaunchDescription
import os


def test_launch_module_importable(real_ros_modules):
    """Ensure hardware.launch can be loaded (no syntax/import errors).

    Needs `real_ros_modules`: the launch file imports launch_ros.actions.Node,
    which imports rclpy. Another test module stubs rclpy in sys.modules, so
    without the fixture this passes alone and fails in a directory run. See
    conftest.py.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "hardware_launch",
        os.path.join(os.path.dirname(__file__), '..', 'launch', 'hardware.launch.py')
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ld = mod.generate_launch_description()
    assert isinstance(ld, LaunchDescription)
