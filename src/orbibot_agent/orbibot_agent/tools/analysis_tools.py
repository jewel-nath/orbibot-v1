"""Analysis tool definitions — compare_values, compute_statistics."""

import logging
import math
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def register(registry, ros_bridge, safety_manager) -> None:
    """Register analysis tools on the given registry."""

    # -- compare_values --

    def _handle_compare_values(
        before: Dict[str, Any],
        after: Dict[str, Any],
        tolerance_pct: float = 10.0,
    ) -> Dict:
        """Compare two dicts field-by-field, computing deltas and pass/fail."""
        tolerance_pct = max(0.0, float(tolerance_pct))

        def _flatten(d: Dict, prefix: str = '') -> Dict[str, float]:
            """Flatten nested dict to dotted keys, keeping only numeric values."""
            result = {}
            for k, v in d.items():
                key = f'{prefix}.{k}' if prefix else k
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    result[key] = float(v)
                elif isinstance(v, dict):
                    result.update(_flatten(v, key))
            return result

        flat_before = _flatten(before)
        flat_after = _flatten(after)

        # Only compare keys present in both
        common_keys = set(flat_before) & set(flat_after)
        fields: Dict[str, Dict] = {}

        for key in sorted(common_keys):
            b = flat_before[key]
            a = flat_after[key]
            delta = a - b
            change_pct = abs(delta) / max(abs(b), 1e-9) * 100.0
            passed = change_pct <= tolerance_pct
            fields[key] = {
                'before': round(b, 4),
                'after': round(a, 4),
                'delta': round(delta, 4),
                'change_pct': round(change_pct, 2),
                'pass': passed,
            }

        all_pass = all(f['pass'] for f in fields.values()) if fields else True
        only_in_before = sorted(set(flat_before) - set(flat_after))
        only_in_after = sorted(set(flat_after) - set(flat_before))

        return {
            'fields': fields,
            'all_pass': all_pass,
            'tolerance_pct': tolerance_pct,
            'only_in_before': only_in_before,
            'only_in_after': only_in_after,
        }

    registry.register_tool(
        name='compare_values',
        description=(
            'Compare two data snapshots field-by-field (e.g. encoder counts before and after movement). '
            'Computes delta and percentage change per numeric field. '
            'Returns pass/fail based on tolerance_pct threshold. '
            'Useful for before/after analysis of any robot state.'
        ),
        parameters={
            'type': 'object',
            'properties': {
                'before': {
                    'type': 'object',
                    'description': 'Data snapshot before the operation (e.g. encoder counts).',
                },
                'after': {
                    'type': 'object',
                    'description': 'Data snapshot after the operation.',
                },
                'tolerance_pct': {
                    'type': 'number',
                    'description': 'Maximum allowed percentage change to PASS (default 10.0).',
                },
            },
            'required': ['before', 'after'],
        },
        handler=_handle_compare_values,
    )

    # -- compute_statistics --

    def _handle_compute_statistics(
        values: List[float],
        expected: Optional[float] = None,
        field_name: Optional[str] = None,
    ) -> Dict:
        """Compute descriptive statistics on a numeric array."""
        if not values:
            return {'error': 'Empty values list'}

        vals = [float(v) for v in values]
        n = len(vals)
        mean = sum(vals) / n
        variance = sum((v - mean) ** 2 for v in vals) / n
        std = math.sqrt(variance)
        minimum = min(vals)
        maximum = max(vals)
        range_val = maximum - minimum

        # Percentiles via linear interpolation
        sorted_vals = sorted(vals)

        def _percentile(p: float) -> float:
            idx = (n - 1) * p / 100.0
            lo = int(idx)
            hi = min(lo + 1, n - 1)
            return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (idx - lo)

        result: Dict[str, Any] = {
            'count': n,
            'mean': round(mean, 5),
            'std': round(std, 5),
            'min': round(minimum, 5),
            'max': round(maximum, 5),
            'range': round(range_val, 5),
            'percentiles': {
                'p25': round(_percentile(25), 5),
                'p50': round(_percentile(50), 5),
                'p75': round(_percentile(75), 5),
            },
        }

        if field_name:
            result['field'] = field_name

        if expected is not None:
            exp = float(expected)
            errs = [abs(v - exp) for v in vals]
            mae = sum(errs) / n
            max_err = max(errs)
            result['expected'] = exp
            result['mae'] = round(mae, 5)
            result['max_error'] = round(max_err, 5)
            result['bias'] = round(mean - exp, 5)

        return result

    registry.register_tool(
        name='compute_statistics',
        description=(
            'Compute descriptive statistics on a list of numeric values. '
            'Returns count, mean, std, min, max, range, and percentiles. '
            'If expected is provided, also computes MAE, max error, and bias. '
            'Useful for analyzing repeated sensor measurements (IMU bias, voltage stability, etc.).'
        ),
        parameters={
            'type': 'object',
            'properties': {
                'values': {
                    'type': 'array',
                    'items': {'type': 'number'},
                    'description': 'List of numeric values to analyze.',
                },
                'expected': {
                    'type': 'number',
                    'description': 'Optional expected/target value for error metrics.',
                },
                'field_name': {
                    'type': 'string',
                    'description': 'Optional label for the data (e.g. "gyro_z_rad_s").',
                },
            },
            'required': ['values'],
        },
        handler=_handle_compute_statistics,
    )
