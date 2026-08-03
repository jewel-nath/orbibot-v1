#!/bin/bash
#
# OrbiBot — onboard computer setup
#
# Brings a fresh Ubuntu 24.04 install up to a working OrbiBot workstation:
# ROS 2 Jazzy, the workspace dependencies, device rules and the toolchains.
#
# Procedure, rationale and the power-wiring stages this script does NOT do:
#   docs/operations/computer-setup.md
#
# Usage:
#   ./scripts/setup_computer.sh            # everything, in order
#   ./scripts/setup_computer.sh ros        # one stage
#   ./scripts/setup_computer.sh verify     # check what is present
#
# Every stage is idempotent — re-running is safe and is the intended way to
# resume after a failure.

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

WS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROS_DISTRO_NAME="jazzy"

info()  { echo -e "${BLUE}==>${NC} $*"; }
ok()    { echo -e "${GREEN}  ok${NC} $*"; }
warn()  { echo -e "${YELLOW}  !!${NC} $*"; }
fail()  { echo -e "${RED}  ✗${NC} $*"; }

require_not_root() {
    if [[ $EUID -eq 0 ]]; then
        fail "Do not run this as root. It calls sudo where it needs to."
        exit 1
    fi
}

check_arch() {
    local arch; arch="$(uname -m)"
    if [[ "$arch" != "x86_64" ]]; then
        warn "Architecture is $arch, not x86_64."
        warn "This script targets the Beelink. On other hardware, check"
        warn "docs/operations/computer-setup.md before continuing."
    fi
}

# ---------------------------------------------------------------- stage: base

stage_base() {
    info "Base system packages"
    sudo apt-get update
    sudo apt-get upgrade -y
    sudo apt-get install -y \
        build-essential cmake git curl wget gnupg lsb-release \
        python3-pip python3-venv python3-dev \
        python3-serial python3-numpy \
        v4l-utils usbutils net-tools htop lm-sensors
    ok "base packages installed"
}

# ----------------------------------------------------------------- stage: ros

stage_ros() {
    info "ROS 2 ${ROS_DISTRO_NAME}"

    if [[ -f "/opt/ros/${ROS_DISTRO_NAME}/setup.bash" ]]; then
        ok "ROS 2 ${ROS_DISTRO_NAME} already present, skipping apt source setup"
    else
        sudo add-apt-repository -y universe
        sudo apt-get update

        # The ros2-apt-source .deb carries the signing key and the source list.
        # It replaces the older raw apt-key + sources.list.d recipe.
        local ver
        ver="$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest \
               | grep -F '"tag_name"' | awk -F\" '{print $4}')"
        if [[ -z "$ver" ]]; then
            fail "Could not resolve the latest ros-apt-source release."
            fail "Check network access to api.github.com, then re-run."
            exit 1
        fi
        info "ros-apt-source ${ver}"

        local codename; codename="$(. /etc/os-release && echo "$VERSION_CODENAME")"
        curl -fL -o /tmp/ros2-apt-source.deb \
            "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ver}/ros2-apt-source_${ver}.${codename}_all.deb"
        sudo apt-get install -y /tmp/ros2-apt-source.deb
        rm -f /tmp/ros2-apt-source.deb
        sudo apt-get update
    fi

    # ros-base, not ros-desktop: the robot is headless. RViz runs on the
    # operator's laptop.
    sudo apt-get install -y "ros-${ROS_DISTRO_NAME}-ros-base" ros-dev-tools
    ok "ROS 2 ${ROS_DISTRO_NAME} core installed"

    info "Packages this workspace depends on"
    sudo apt-get install -y \
        "ros-${ROS_DISTRO_NAME}-robot-localization" \
        "ros-${ROS_DISTRO_NAME}-imu-filter-madgwick" \
        "ros-${ROS_DISTRO_NAME}-slam-toolbox" \
        "ros-${ROS_DISTRO_NAME}-navigation2" \
        "ros-${ROS_DISTRO_NAME}-nav2-bringup" \
        "ros-${ROS_DISTRO_NAME}-rplidar-ros" \
        "ros-${ROS_DISTRO_NAME}-rosbridge-suite" \
        "ros-${ROS_DISTRO_NAME}-robot-state-publisher" \
        "ros-${ROS_DISTRO_NAME}-joint-state-publisher" \
        "ros-${ROS_DISTRO_NAME}-xacro" \
        "ros-${ROS_DISTRO_NAME}-tf-transformations" \
        "ros-${ROS_DISTRO_NAME}-twist-mux"

    # twist-mux is on that list deliberately. It was never installed on the Pi,
    # which is why four nodes publish /cmd_vel with nothing arbitrating between
    # them — see docs/architecture/command-pipeline.md.
    #
    # ros-jazzy-joy is deliberately NOT installed. Teleop is web-only and
    # orbibot_teleop stays dormant.
    ok "workspace dependencies installed"
}

# ----------------------------------------------------------- stage: realsense

stage_realsense() {
    info "RealSense D435 — depth enabled by decision, 2026-08-03"
    sudo apt-get install -y \
        "ros-${ROS_DISTRO_NAME}-librealsense2" \
        "ros-${ROS_DISTRO_NAME}-realsense2-camera"
    ok "librealsense + realsense2_camera installed"
    warn "Depth needs a 5000 Mbps link. Check with 'verify' once the camera is"
    warn "plugged into a blue USB 3 port with a USB 3-rated cable."
}

# --------------------------------------------------------------- stage: build

stage_build() {
    info "Workspace dependencies and build"

    if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
        sudo rosdep init
    fi
    rosdep update

    # ROS setup.bash reads unset variables (AMENT_TRACE_SETUP_FILES and
    # friends) by design, so it cannot be sourced under `set -u` — it aborts on
    # the first one. Drop nounset across the source only.
    set +u
    # shellcheck disable=SC1090
    source "/opt/ros/${ROS_DISTRO_NAME}/setup.bash"
    set -u

    cd "$WS_DIR"

    # Three keys are skipped deliberately:
    #
    #   joy              orbibot_teleop declares it, but teleop is web-only by
    #                    decision and that package is dormant. Letting rosdep
    #                    pull joy in would quietly undo the decision recorded in
    #                    docs/architecture/command-pipeline.md.
    #
    #   python3-anthropic
    #   python3-mcp      Not packaged in Ubuntu 24.04 at all. rosdep cannot
    #                    resolve them; they come from pip below.
    rosdep install --from-paths src --ignore-src -r -y \
        --skip-keys "joy python3-anthropic python3-mcp"

    colcon build --symlink-install
    ok "workspace built"
}

# ------------------------------------------------------- stage: pip (agent)

stage_pip() {
    info "Python packages the agent needs that apt does not carry"

    # Ubuntu 24.04 marks the system Python externally-managed (PEP 668), so a
    # plain pip install refuses. --user keeps this out of /usr and confines it
    # to ~/.local, which is already on sys.path for ROS nodes run as this user;
    # --break-system-packages is what satisfies PEP 668 for that.
    python3 -m pip install --user --break-system-packages anthropic mcp
    ok "anthropic + mcp installed to ~/.local"
}

# ------------------------------------------------------------- stage: devices

stage_devices() {
    info "Device rules and group membership"
    # Deliberately NOT via sudo. The script calls sudo itself where it needs
    # to, refuses to run as root, and reads $USER to pick the account to add
    # to dialout/plugdev/video — under sudo that would resolve to root.
    "$WS_DIR/src/orbibot_hardware/scripts/setup_permissions.sh"
    ok "udev rules installed"
    warn "Log out and back in for the dialout/plugdev/video groups to apply."
}

# ----------------------------------------------------------------- stage: pio

stage_pio() {
    info "PlatformIO — STM32 firmware toolchain"
    if [[ ! -x "$HOME/.platformio-venv/bin/pio" ]]; then
        python3 -m venv "$HOME/.platformio-venv"
        "$HOME/.platformio-venv/bin/pip" install --upgrade pip platformio
    fi
    ok "pio at $HOME/.platformio-venv/bin/pio"
    warn "Put this path into CLAUDE.md and the firmware README, replacing <pio>."
}

# ---------------------------------------------------------------- stage: node

stage_node() {
    info "Node.js — dashboard frontend build"
    if ! command -v node >/dev/null; then
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
        sudo apt-get install -y nodejs
    fi
    ok "node $(node --version), npm $(npm --version)"
}

# ------------------------------------------------------------- stage: bashrc

stage_bashrc() {
    info "Shell environment"
    local marker="# --- OrbiBot ROS 2 environment ---"
    if grep -qF "$marker" "$HOME/.bashrc"; then
        ok ".bashrc already configured"
        return
    fi
    cat >> "$HOME/.bashrc" <<EOF

$marker
source /opt/ros/${ROS_DISTRO_NAME}/setup.bash
[ -f "$WS_DIR/install/setup.bash" ] && source "$WS_DIR/install/setup.bash"
export ROS_DOMAIN_ID=42
EOF
    ok "appended to ~/.bashrc (ROS_DOMAIN_ID=42)"
    warn "Use the same ROS_DOMAIN_ID on the laptop, or RViz will not see the robot."
}

# -------------------------------------------------------------- stage: verify

stage_verify() {
    info "Verification"
    local failures=0

    _check() {
        local label="$1"; shift
        if "$@" >/dev/null 2>&1; then ok "$label"; else fail "$label"; failures=$((failures+1)); fi
    }

    _check "ROS 2 ${ROS_DISTRO_NAME} present" test -f "/opt/ros/${ROS_DISTRO_NAME}/setup.bash"
    _check "colcon"   command -v colcon
    _check "rosdep"   command -v rosdep
    _check "gcc"      command -v gcc
    _check "cmake"    command -v cmake
    _check "node"     command -v node
    _check "pio"      test -x "$HOME/.platformio-venv/bin/pio"
    _check "udev rules" test -f /etc/udev/rules.d/99-orbibot.rules
    _check "workspace built" test -f "$WS_DIR/install/setup.bash"
    _check "python: anthropic" python3 -c "import anthropic"
    _check "python: mcp"       python3 -c "import mcp"

    # joy must NOT be installed — teleop is web-only by decision.
    if [[ -d "/opt/ros/${ROS_DISTRO_NAME}/share/joy" ]]; then
        warn "ros-${ROS_DISTRO_NAME}-joy is installed; teleop is web-only by decision"
    else
        ok "joy absent, as intended"
    fi

    echo
    info "Hardware (absent is expected until it is wired up)"
    for dev in /dev/motordriver /dev/lidar; do
        if [[ -e "$dev" ]]; then ok "$dev"; else warn "$dev not present"; fi
    done

    local rs_speed
    rs_speed="$(for d in /sys/bus/usb/devices/*/; do
        [ -f "$d/product" ] && grep -qi realsense "$d/product" 2>/dev/null && cat "$d/speed"
    done | head -1)"
    if [[ -z "$rs_speed" ]]; then
        warn "RealSense not connected"
    elif [[ "$rs_speed" == "5000" ]]; then
        ok "RealSense at 5000 Mbps — depth + colour viable"
    else
        fail "RealSense at ${rs_speed} Mbps — needs 5000. Blue port, USB 3 cable."
        failures=$((failures+1))
    fi

    echo
    if [[ $failures -eq 0 ]]; then
        ok "software side complete"
        echo
        warn "Software is only part of Phase 0. Still required before the robot"
        warn "drives on battery — see docs/operations/computer-setup.md:"
        warn "  - adapter label read, converter output set with a multimeter"
        warn "  - P-1..P-5 power measurements (sag, thermals, brown-out)"
        warn "  - robot re-weighed after mounting"
        warn "  - CPU baseline recorded"
    else
        fail "$failures check(s) failed"
        return 1
    fi
}

# ----------------------------------------------------------------------- main

require_not_root
check_arch

STAGE="${1:-all}"

case "$STAGE" in
    base)      stage_base ;;
    ros)       stage_ros ;;
    realsense) stage_realsense ;;
    build)     stage_build ;;
    devices)   stage_devices ;;
    pip)       stage_pip ;;
    pio)       stage_pio ;;
    node)      stage_node ;;
    bashrc)    stage_bashrc ;;
    verify)    stage_verify ;;
    all)
        stage_base
        stage_ros
        stage_realsense
        stage_devices
        stage_bashrc
        stage_build
        stage_pip
        stage_pio
        stage_node
        echo
        stage_verify
        ;;
    *)
        echo "Usage: $0 [base|ros|realsense|build|devices|pip|pio|node|bashrc|verify|all]"
        exit 1
        ;;
esac
