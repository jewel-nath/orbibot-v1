"""PlatformIO pre-build script: inject git commit hash and branch into build flags."""

import subprocess
Import("env")


def get_git_info(cmd):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"


commit = get_git_info(["git", "rev-parse", "--short", "HEAD"])
branch = get_git_info(["git", "rev-parse", "--abbrev-ref", "HEAD"])

env.Append(CPPDEFINES=[
    ("GIT_COMMIT_HASH", env.StringifyMacro(commit)),
    ("GIT_BRANCH", env.StringifyMacro(branch)),
])
