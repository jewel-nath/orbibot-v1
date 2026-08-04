#!/bin/bash
# OrbiBot stop - shut the robot stack down and prove that it stopped
#
# Ctrl+C in a real terminal already works and is the operator's normal path.
# This script exists for the case that does NOT work: a launch started without
# a controlling terminal — from a script, a systemd unit, an ssh command, or an
# agent session. There, stopping the launch orphans every node it started; they
# keep running under PID 1, keep publishing, and keep holding the serial ports.
# See src/orbibot_bringup/bringup-issue.md, BRINGUP-1.
#
# Usage:
#   .claude/scripts/stop.sh          # stop everything, verify, report
#   .claude/scripts/stop.sh --check  # report only, change nothing

set -uo pipefail

CHECK_ONLY=0
[ "${1:-}" = "--check" ] && CHECK_ONLY=1

# Node processes started by this project's launches. Matches the executables,
# never a `ros2 launch` wrapper and never this script.
NODE_RE='rplidar_composition|robot_state_publisher|ekf_node|imu_filter_madgwick_node'
NODE_RE="$NODE_RE"'|orbibot_[a-z_]*/lib/orbibot_|slam_toolbox|controller_server|planner_server'
NODE_RE="$NODE_RE"'|bt_navigator|behavior_server|velocity_smoother|collision_monitor|twist_mux'
NODE_RE="$NODE_RE"'|map_server|amcl|realsense2_camera_node|rosbridge'
LAUNCH_RE='ros2 launch orbibot'

# `pgrep -f` matches the whole command line, so any shell that merely *mentions*
# a node name — this script's own wrapper, an ssh command, an agent's `bash -c`
# — matches too. Killing those kills the caller. Keep only processes whose
# argv[0] is an actual executable rather than a shell.
only_real() {
    local p argv0
    while read -r p; do
        [ -z "$p" ] && continue
        [ "$p" = "$$" ] || [ "$p" = "$PPID" ] && continue
        argv0="$(tr '\0' '\n' < "/proc/$p/cmdline" 2>/dev/null | head -1)"
        case "${argv0##*/}" in
            bash|sh|dash|zsh|pgrep|ps|grep) continue ;;
        esac
        echo "$p"
    done
}

pids_nodes()    { pgrep -f "$NODE_RE"   2>/dev/null | only_real | tr '\n' ' '; }
pids_launches() { pgrep -f "$LAUNCH_RE" 2>/dev/null | only_real | tr '\n' ' '; }
# Unquoted on purpose: word splitting collapses the whitespace, so "nothing
# running" is the empty string rather than a lone space that tests as non-empty.
all_pids()      { echo $(pids_launches) $(pids_nodes); }

show() {
    local p
    for p in $(all_pids); do
        ps -o pid=,ppid=,args= -p "$p" 2>/dev/null | cut -c1-100 | sed 's/^/    /'
    done
}

# Which processes hold the two serial devices. This is the question that
# actually matters: a node still holding /dev/lidar keeps the motor spinning,
# and makes the next launch fail to open the port.
device_holders() {
    local dev target p
    for dev in /dev/lidar /dev/motordriver; do
        [ -e "$dev" ] || continue
        target="$(readlink -f "$dev")"
        for p in /proc/[0-9]*; do
            if ls -l "$p/fd" 2>/dev/null | grep -q "$target"; then
                echo "    $dev held by pid $(basename "$p") ($(cat "$p/comm" 2>/dev/null))"
            fi
        done
    done
}

echo "OrbiBot Stop"
echo "============"

if [ -z "$(all_pids)" ]; then
    echo "  Nothing running."
    holders="$(device_holders)"
    [ -n "$holders" ] && { echo "  But the serial devices are still held:"; echo "$holders"; exit 1; }
    echo "  [OK] serial devices free"
    exit 0
fi

echo ""
echo "[Running]"
show

if [ "$CHECK_ONLY" = "1" ]; then
    echo ""
    echo "  --check: nothing was stopped."
    device_holders
    exit 0
fi

# Escalate. SIGINT lets rclcpp/rclpy run their shutdown handlers and release the
# serial ports cleanly; only fall through to SIGKILL for what refuses to go.
# Launch processes go first so they cannot respawn a node we are about to kill.
for sig in INT TERM KILL; do
    targets="$(all_pids)"
    [ -z "${targets// /}" ] && break
    echo ""
    echo "[SIG$sig] -> $targets"
    for p in $(pids_launches); do kill -"$sig" "$p" 2>/dev/null; done
    sleep 1
    for p in $(pids_nodes); do kill -"$sig" "$p" 2>/dev/null; done
    for _ in $(seq 12); do
        [ -z "$(all_pids)" ] && break
        sleep 0.5
    done
done

sleep 1
echo ""
echo "[Result]"
left="$(all_pids)"
holders="$(device_holders)"

if [ -z "${left// /}" ] && [ -z "$holders" ]; then
    echo "  [OK] stack stopped, serial devices free"
    exit 0
fi

[ -n "${left// /}" ] && { echo "  [FAIL] still running:"; show; }
[ -n "$holders" ] && { echo "  [FAIL] serial devices still held:"; echo "$holders"; }
exit 1
