/**
 * @file task_monitoring.h
 * @brief Monitoring Task Interface
 * @author Jewel Nath
 * @date 2025-11-30
 */

#ifndef TASK_MONITORING_H
#define TASK_MONITORING_H

#include <stdint.h>

/* Per-task alive counter IDs */
#define ALIVE_TASK_CONTROL      0
#define ALIVE_TASK_IMU          1
#define ALIVE_TASK_COMM         2
#define ALIVE_TASK_COUNT        3

/**
 * @brief Increment alive counter for the calling task.
 *        Call once per iteration from each critical task.
 */
void task_alive_kick(uint8_t task_id);

void task_monitoring(void *params);

#endif // TASK_MONITORING_H
