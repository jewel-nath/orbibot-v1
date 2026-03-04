/**
 * @file firmware_version.h
 * @brief Firmware version information
 * @author Jewel Nath
 * @date 2025-11-27
 */

#ifndef FIRMWARE_VERSION_H
#define FIRMWARE_VERSION_H

// Firmware version (Semantic Versioning: MAJOR.MINOR.PATCH)
#define FIRMWARE_VERSION_MAJOR      2
#define FIRMWARE_VERSION_MINOR      0
#define FIRMWARE_VERSION_PATCH      0

// Build metadata
#define FIRMWARE_NAME               "OrbiBot ROSMaster Firmware"
#define FIRMWARE_TARGET             "STM32F103RCT6"
#define FIRMWARE_BOARD              "ROSMaster V3.0"

// Compile-time build info
#define BUILD_DATE                  __DATE__
#define BUILD_TIME                  __TIME__

// Git information (populated by build system)
#ifndef GIT_COMMIT_HASH
#define GIT_COMMIT_HASH             "unknown"
#endif

#ifndef GIT_BRANCH
#define GIT_BRANCH                  "unknown"
#endif

// Macro stringification helpers
#define _FW_STRINGIFY(x)    #x
#define _FW_TOSTRING(x)     _FW_STRINGIFY(x)

/**
 * @brief Version string auto-generated from MAJOR.MINOR.PATCH
 */
#define FIRMWARE_VERSION_STRING \
    "v" _FW_TOSTRING(FIRMWARE_VERSION_MAJOR) "." \
        _FW_TOSTRING(FIRMWARE_VERSION_MINOR) "." \
        _FW_TOSTRING(FIRMWARE_VERSION_PATCH)

/**
 * @brief Get full version info
 * @return Full version with build info
 */
#define FIRMWARE_FULL_INFO          \
    FIRMWARE_NAME " " FIRMWARE_VERSION_STRING \
    " (" BUILD_DATE " " BUILD_TIME ")"

#endif // FIRMWARE_VERSION_H
