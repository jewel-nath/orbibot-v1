"""Load environment variables from .env.local.

Keeps API keys out of the repo. Tries multiple locations so it works regardless
of how the process is launched (terminal, IDE, ros2 launch).
"""

import os
import logging

logger = logging.getLogger(__name__)

_ENV_LOCAL_LOADED = False


def _candidate_paths():
    """Paths to check for .env.local (first existing one is used)."""
    home = os.path.expanduser('~')
    cwd = os.getcwd()
    candidates = []

    # 1) ~/.orbibot/.env.local - always works, no workspace dependency
    candidates.append(os.path.join(home, '.orbibot', '.env.local'))

    # 2) ~/orbibot_ws/src/orbibot_agent/.env.local - common workspace layout
    candidates.append(os.path.join(home, 'orbibot_ws', 'src', 'orbibot_agent', '.env.local'))

    # 3) ORBIBOT_WS (when passed to child process)
    ws = os.environ.get('ORBIBOT_WS', '').strip()
    if ws:
        ws = os.path.expanduser(ws)
        candidates.append(os.path.join(ws, 'src', 'orbibot_agent', '.env.local'))

    # 4) Package root (when running from source/build)
    this_dir = os.path.dirname(os.path.abspath(__file__))
    pkg_root = os.path.dirname(this_dir)
    candidates.append(os.path.join(pkg_root, '.env.local'))

    # 5) CWD-based
    candidates.append(os.path.join(cwd, '.env.local'))
    candidates.append(os.path.join(cwd, 'src', 'orbibot_agent', '.env.local'))

    return candidates


def _parse_env_line(line: str) -> tuple:
    """Parse KEY=value or KEY="value", return (key, value) or (None, None)."""
    line = line.strip()
    if not line or line.startswith('#'):
        return (None, None)
    if '=' not in line:
        return (None, None)
    key, _, rest = line.partition('=')
    key = key.strip()
    if not key:
        return (None, None)
    value = rest.strip()
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        value = value[1:-1]
    return (key, value)


def load_dotenv_local() -> bool:
    """Load KEY=value from .env.local into os.environ (only if not already set).

    Looks for .env.local in: ORBIBOT_WS/src/orbibot_agent/, package root, cwd.
    Returns True if a file was loaded.
    """
    global _ENV_LOCAL_LOADED
    if _ENV_LOCAL_LOADED:
        return True
    for path in _candidate_paths():
        if path and os.path.isfile(path):
            try:
                with open(path, 'r') as f:
                    for line in f:
                        key, value = _parse_env_line(line)
                        if key and key not in os.environ:
                            os.environ[key] = value
                logger.info(f'Loaded env from {path}')
                _ENV_LOCAL_LOADED = True
                return True
            except OSError as e:
                logger.warning(f'Could not read {path}: {e}')
    return False
