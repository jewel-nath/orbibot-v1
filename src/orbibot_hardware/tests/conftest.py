"""
Shared fixtures for the orbibot_hardware host-side tests.

## The hazard these exist for

`test_hardware_node_unit.py` tests `hardware_node.py` without ROS 2 installed in
the test process. It does that by installing stub modules into `sys.modules` —
`rclpy`, `sensor_msgs`, `orbibot_msgs`, and a MagicMock for
`orbibot_hardware.rosmaster_driver` — and it never removes them.

`sys.modules` is process-global, and pytest imports every test module during
collection before running anything. So those stubs are live for the whole
session, and any later test that wants the *real* module silently gets the stub.

The symptom is nasty: every file passes on its own, and 35 tests fail only when
the directory is run as a whole. Measured 2026-08-04, before the fix:

    per file      81 passed, 1 failed
    directory     46 passed, 35 failed

Both fixes below are about getting the real module back, not about the stubs
being wrong — the stubs are the right approach for that one file.
"""

import sys
import types

import pytest

# Everything test_hardware_node_unit.py may have replaced with a stub.
_STUBBED_PREFIXES = (
    'rclpy',
    'rcl_interfaces',
    'sensor_msgs',
    'geometry_msgs',
    'nav_msgs',
    'std_msgs',
    'diagnostic_msgs',
    'orbibot_msgs',
    'orbibot_hardware.rosmaster_driver',
)


def _is_stub(mod) -> bool:
    """True if this looks like an injected stub rather than a real import.

    A real installed module has a __file__. The stubs here are either bare
    types.ModuleType instances built in-process, or MagicMocks.
    """
    if isinstance(mod, types.ModuleType):
        return getattr(mod, '__file__', None) is None
    return True  # MagicMock or anything else that is not a module at all


@pytest.fixture
def real_ros_modules():
    """Evict stubbed ROS modules so the test body imports the real ones.

    Use in any test that needs genuine `rclpy`, `launch_ros` or the real
    `rosmaster_driver`. Restores whatever was there afterwards, so the module
    that owns the stubs keeps working.
    """
    removed = {}
    for name in list(sys.modules):
        if name.startswith(_STUBBED_PREFIXES) and _is_stub(sys.modules[name]):
            removed[name] = sys.modules.pop(name)
    try:
        yield
    finally:
        # Put the stubs back only where nothing real took their place, so a
        # genuine import performed by the test is not thrown away.
        for name, mod in removed.items():
            sys.modules.setdefault(name, mod)
