#!/usr/bin/env python3
"""
The serial protocol table exists in three hand-maintained copies. This test is
the single source of truth for the fact that they must agree.

    src/orbibot_rosmaster_firmware/include/protocol.h          the firmware
    src/orbibot_hardware/orbibot_hardware/rosmaster_driver.py  the ROS 2 driver
    src/orbibot_rosmaster_firmware/tests/rosmaster_protocol.py the test harness

Merging them into one generated file would be the textbook fix, but the firmware
is C built by PlatformIO and the driver is Python installed by colcon — a shared
generator is a build-system problem in exchange for a naming problem. Asserting
agreement costs nothing and catches the same class of bug, which is drift, not
duplication.

**Why this exists.** On 2026-08-04 the harness had `SET_MOTOR = 0x09` while the
firmware and driver both had `FUNC_RESET_ODOM = 0x09`. The firmware has no
per-motor command at all. `test_motor_direction.py` used it, sent a packet the
firmware rejected on length, then asked a human "Did the wheel spin FORWARD?" —
so the recorded result was an opinion about a wheel that was never commanded.
Nothing caught it because each file was internally consistent.

No hardware required. Run with:

    python3 -m pytest src/orbibot_rosmaster_firmware/tests/test_protocol_table_agreement.py -q
"""

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]

FIRMWARE_H = REPO / 'src/orbibot_rosmaster_firmware/include/protocol.h'
DRIVER_PY = REPO / 'src/orbibot_hardware/orbibot_hardware/rosmaster_driver.py'
HARNESS_PY = REPO / 'src/orbibot_rosmaster_firmware/tests/rosmaster_protocol.py'

# The harness drops the FUNC_ prefix and spells three of them out in full.
# These are naming, not disagreement.
ALIASES = {
    'REPORT_IMU_ATTITUDE': 'REPORT_IMU_ATT',
    'REPORT_IMU_RAW': 'REPORT_ICM_RAW',
}

# Codes the firmware implements that a given consumer legitimately does not
# need. Absence is fine; a *different value* is not.
NOT_REQUIRED = {
    'driver': {'REQUEST_DATA', 'RESET_STATE'},
    'harness': {'RESET_STATE'},
}


def _normalise(name: str) -> str:
    name = name.removeprefix('FUNC_')
    return ALIASES.get(name, name)


def _parse_defines(path: Path) -> dict:
    """FUNC_X 0x12 from C #defines, or FUNC_X = 0x12 from Python."""
    text = path.read_text()
    return {
        _normalise(m.group(1)): int(m.group(2), 16)
        for m in re.finditer(
            r'^\s*(?:#define\s+)?(FUNC_[A-Z0-9_]+)\s*=?\s*\(?(0[xX][0-9a-fA-F]+)\)?',
            text, re.M)
    }


def _parse_funccode_enum(path: Path) -> dict:
    """Members of `class FuncCode(IntEnum)` only — not CarType, not anything else."""
    text = path.read_text()
    body = re.search(r'class\s+FuncCode\b.*?:\n(.*?)(?=\n\S|\nclass\s)', text, re.S)
    assert body, f'no FuncCode enum found in {path}'
    return {
        _normalise(m.group(1)): int(m.group(2), 16)
        for m in re.finditer(r'^\s+([A-Z][A-Z0-9_]*)\s*=\s*(0[xX][0-9a-fA-F]+)',
                             body.group(1), re.M)
    }


@pytest.fixture(scope='module')
def tables():
    t = {
        'firmware': _parse_defines(FIRMWARE_H),
        'driver': _parse_defines(DRIVER_PY),
        'harness': _parse_funccode_enum(HARNESS_PY),
    }
    for name, table in t.items():
        assert table, f'parsed no function codes from the {name} table'
    return t


def test_firmware_table_is_not_empty(tables):
    """Guard the parser itself: a regex that silently matches nothing passes everything."""
    assert len(tables['firmware']) >= 14


@pytest.mark.parametrize('consumer', ['driver', 'harness'])
def test_no_code_means_two_different_things(tables, consumer):
    """The dangerous case: same byte, different meaning."""
    firmware = tables['firmware']
    by_value = {v: k for k, v in firmware.items()}

    conflicts = []
    for name, value in tables[consumer].items():
        fw_name = by_value.get(value)
        if fw_name is not None and fw_name != name:
            conflicts.append(f'0x{value:02X}: firmware={fw_name}, {consumer}={name}')

    assert not conflicts, (
        f'{consumer} disagrees with the firmware about what a byte means:\n  '
        + '\n  '.join(conflicts))


@pytest.mark.parametrize('consumer', ['driver', 'harness'])
def test_no_name_has_two_different_values(tables, consumer):
    """The other direction: same name, different byte."""
    firmware = tables['firmware']
    mismatches = [
        f'{name}: firmware=0x{firmware[name]:02X}, {consumer}=0x{value:02X}'
        for name, value in tables[consumer].items()
        if name in firmware and firmware[name] != value
    ]
    assert not mismatches, (
        f'{consumer} disagrees with the firmware about a value:\n  '
        + '\n  '.join(mismatches))


@pytest.mark.parametrize('consumer', ['driver', 'harness'])
def test_no_invented_codes(tables, consumer):
    """A consumer must not define a code the firmware does not implement.

    This is what let SET_MOTOR = 0x09 survive: it looked like a real command,
    and nothing anywhere claimed otherwise.
    """
    firmware = tables['firmware']
    # The harness also carries display/peripheral codes for hardware this build
    # does not implement. They are inert, but they must not collide — which
    # test_no_code_means_two_different_things already enforces.
    invented = sorted(set(tables[consumer]) - set(firmware))
    known_extra = {'harness': {'SET_RGB', 'SET_PWM_SERVO', 'OLED_SET'}, 'driver': set()}
    unexpected = [n for n in invented if n not in known_extra[consumer]]

    assert not unexpected, (
        f'{consumer} defines codes the firmware does not implement: {unexpected}. '
        'Either the firmware gained them and protocol.h was not updated, or they '
        'are fiction — 0x09 "SET_MOTOR" was fiction for months.')


@pytest.mark.parametrize('consumer', ['driver', 'harness'])
def test_consumer_covers_what_it_needs(tables, consumer):
    """Report anything the consumer is missing, so absence is a decision."""
    missing = sorted(set(tables['firmware']) - set(tables[consumer])
                     - NOT_REQUIRED[consumer])
    assert not missing, (
        f'{consumer} is missing firmware codes: {missing}. If that is deliberate, '
        f'add them to NOT_REQUIRED["{consumer}"] in this file with a reason.')
