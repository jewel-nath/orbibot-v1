/**
 * @file robot_error.h
 * @brief Firmware-wide error codes
 *
 * Unified error type for all modules. Generic naming so this firmware
 * can be reused on any Yahboom ROSMaster V3.0 expansion board.
 */

#ifndef ROBOT_ERROR_H
#define ROBOT_ERROR_H

typedef enum {
    ROBOT_OK          =  0,
    ROBOT_ERR_PARAM   = -1,
    ROBOT_ERR_TIMEOUT = -2,
    ROBOT_ERR_HW      = -3,
    ROBOT_ERR_CHECKSUM = -4,
    ROBOT_ERR_BUSY    = -5,
} robot_err_t;

#endif // ROBOT_ERROR_H
