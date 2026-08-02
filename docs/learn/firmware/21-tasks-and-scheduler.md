---
title: "Part 2: Tasks and Scheduler"
type: learn
area: firmware
package: orbibot_rosmaster_firmware
duration: "30 minutes"
tags:
  - learn
  - firmware
---

# Part 2: Tasks and Scheduler

**Duration**: 30 minutes  
**Prerequisites**: [[20-what-is-rtos]]

---

## Learning Objectives

After this lesson, you will understand:
- How to create FreeRTOS tasks
- Task states and lifecycle
- The scheduler and how it works
- Task priorities and preemption
- vTaskDelay vs vTaskDelayUntil

---

## Creating Tasks

### Task Function Structure

Every task is a C function that never returns:

```c
void task_function(void *params)
{
    // 1. Initialization (runs once)
    setup_code();
    
    // 2. Infinite loop (runs forever)
    for (;;)
    {
        // Do work
        do_something();
        
        // Must have a delay!
        vTaskDelay(pdMS_TO_TICKS(100));
    }
    
    // Should never reach here
    // If needed: vTaskDelete(NULL);
}
```

### Task Creation

Use `xTaskCreate()` to create a task:

```c
BaseType_t xTaskCreate(
    TaskFunction_t pvTaskCode,      // Pointer to task function
    const char * const pcName,      // Task name (for debugging)
    configSTACK_DEPTH_TYPE usStackDepth,  // Stack size (in words!)
    void * const pvParameters,      // Parameters to pass
    UBaseType_t uxPriority,         // Priority (0 = lowest)
    TaskHandle_t * const pxCreatedTask  // Handle (optional)
);
```

### Example: Creating Two Tasks

```c
#include "FreeRTOS.h"
#include "task.h"

// Task 1: Blink LED every 500ms
void task_led(void *params)
{
    GPIO_Init(LED_PIN);
    
    while(1) {
        GPIO_Toggle(LED_PIN);
        vTaskDelay(pdMS_TO_TICKS(500));
    }
}

// Task 2: Print message every 1 second
void task_print(void *params)
{
    int count = 0;
    
    while(1) {
        printf("Count: %d\n", count++);
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}

int main(void)
{
    // Create LED task
    xTaskCreate(
        task_led,           // Function
        "LED_Task",         // Name
        128,                // Stack: 128 words = 512 bytes
        NULL,               // No parameters
        1,                  // Priority 1
        NULL                // No handle needed
    );
    
    // Create print task
    xTaskCreate(
        task_print,
        "Print_Task",
        128,
        NULL,
        1,                  // Same priority = time-sliced
        NULL
    );
    
    // Start scheduler (never returns)
    vTaskStartScheduler();
    
    while(1);  // Should never reach here
}
```

---

## Task States

A task can be in one of four states:

```
┌─────────────┐      Create      ┌─────────────┐
│  Non-       │─────────────────→│    Ready    │
│  Existent   │                  │  (Waiting   │
│             │                  │   for CPU)  │
└─────────────┘                  └──────┬──────┘
                                        │
                              Scheduler │
                              selects   │
                              task      │
                                        ↓
                              ┌─────────────────┐
                         Run  │     Running     │
                        ←─────│   (Has CPU)     │
                        │     └─────────────────┘
                        │               │
                   Block/               │ Preempted by
                   Delay/               │ higher priority
                   Suspend              │
                        │               ↓
                        │      ┌─────────────┐
                        └──────│   Ready     │
                               │  (Waiting   │
                               │   for CPU)  │
                               └─────────────┘
                                        │
                                        │ Scheduler
                                        │ selects
                                        ↓
                                  (Continue running)
```

### State Descriptions

| State | Description | How to Enter |
|-------|-------------|--------------|
| **Ready** | Can run, waiting for CPU | Created, or resumed |
| **Running** | Currently executing | Scheduled |
| **Blocked** | Waiting for event/delay | `vTaskDelay()`, waiting for queue/semaphore |
| **Suspended** | Paused indefinitely | `vTaskSuspend()` |

---

## The Scheduler

### What is the Scheduler?

The scheduler decides which task runs and when.

```
Scheduler = Traffic Police

  - Decides who gets CPU
  - Follows priority rules
  - Switches between tasks rapidly
```

### Types of Scheduling

**1. Preemptive (FreeRTOS default)**
- Higher priority task can interrupt lower priority
- Most responsive for real-time systems

```
Time →
     ├───┬───────┬───┬───────┤
High:    ████████     ████████   (runs when needed)
     │
Low : ████         ████          (runs in gaps)
      ↑
      Preempted!
```

**2. Cooperative**
- Tasks must yield CPU voluntarily
- Less common, simpler but less responsive

### Scheduler Configuration

```c
// FreeRTOSConfig.h

#define configUSE_PREEMPTION          1   // 1 = preemptive
#define configUSE_TIME_SLICING        1   // 1 = round-robin for same priority
#define configTICK_RATE_HZ            1000  // 1ms tick
#define configMAX_PRIORITIES          11    // 0-10
```

---

## Task Priorities

### Priority Levels

```
Priority 10: Highest (most urgent)
Priority  9:
Priority  8:
...
Priority  1:
Priority  0: Lowest (idle task)
```

### Priority Rules

1. **Higher number = Higher priority**
2. **Highest priority ready task runs**
3. **Same priority = Time-sliced (round-robin)**
4. **Can change priority at runtime**

### Example: Priority Behavior

```c
void task_high(void *params) {  // Priority 3
    while(1) {
        printf("High\n");      // Runs first
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

void task_low(void *params) {   // Priority 1
    while(1) {
        printf("Low\n");       // Only runs when High delays
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

int main(void) {
    xTaskCreate(task_high, "High", 128, NULL, 3, NULL);
    xTaskCreate(task_low,  "Low",  128, NULL, 1, NULL);
    vTaskStartScheduler();
}
```

**Output**:
```
High
High
High
... (100ms later)
Low
High
High
...
```

---

## Task Delays

### vTaskDelay() - Relative Delay

Delay for a specified time from **now**.

```c
void task_example(void *params)
{
    while(1) {
        do_work();                          // Takes 5ms
        vTaskDelay(pdMS_TO_TICKS(100));     // Wait 100ms
        // Total period = 5ms + 100ms = 105ms (drifts!)
    }
}
```

**Problem**: Period is not exact (work time + delay).

### vTaskDelayUntil() - Absolute Delay

Delay until a specific time (periodic).

```c
void task_periodic(void *params)
{
    TickType_t last_wake = xTaskGetTickCount();
    const TickType_t period = pdMS_TO_TICKS(100);  // 100ms
    
    while(1) {
        do_work();                          // Takes 5ms
        
        // Wait until next period (compensates for work time)
        vTaskDelayUntil(&last_wake, period);
        // Period is exactly 100ms (no drift!)
    }
}
```

### Visual Comparison

```
vTaskDelay (drifts):
Time: 0    105   210   315   420
      |Work|Delay|Work|Delay|Work|
      5ms  100ms 5ms  100ms 5ms

vTaskDelayUntil (exact):
Time: 0    100   200   300   400
      |Work|Wait|Work|Wait|Work|
      5ms  95ms 5ms  95ms  5ms
```

---

## Context Switching

### What is Context Switch?

Saving one task's state and restoring another's.

```
Context Switch Process:
  1. Save current task registers (R0-R12, PC, LR, SP)
  2. Save to task's stack
  3. Select next task (highest priority ready)
  4. Restore next task's registers from its stack
  5. Resume next task

Takes ~10-20 microseconds on STM32F103
```

### When Does Context Switch Happen?

1. **Task yields** (calls vTaskDelay, blocks on queue)
2. **Higher priority task becomes ready** (interrupt)
3. **Time slice expires** (same priority tasks)
4. **Tick interrupt** (every 1ms)

---

## Task Stack

### Stack Size

Specified in words (4 bytes each):

```c
// 128 words = 512 bytes
xTaskCreate(task_func, "Name", 128, NULL, 1, NULL);
```

### What Uses Stack?

- Local variables
- Function call return addresses
- Function parameters
- Interrupt context (if interrupt occurs during task)

### Stack Overflow

```c
// ❌ BAD: Stack overflow
void bad_task(void *params) {
    char huge_buffer[10000];  // 10KB on stack!
    // Stack size was only 512 bytes = CRASH!
}

// ✅ GOOD: Use heap for large buffers
void good_task(void *params) {
    char *buffer = malloc(10000);  // Heap allocation
    // Use buffer...
    free(buffer);
}
```

### Checking Stack Usage

```c
// Get remaining stack space
UBaseType_t stack_free = uxTaskGetStackHighWaterMark(NULL);
printf("Free stack: %u words\n", stack_free);

// Hook called on overflow (enable in config)
void vApplicationStackOverflowHook(TaskHandle_t xTask, 
                                    char *pcTaskName) {
    printf("Stack overflow in task: %s\n", pcTaskName);
    while(1);  // Halt
}
```

---

## Common Mistakes

### Mistake 1: No Delay in Task

```c
// ❌ WRONG: CPU hogging
void task_bad(void *params) {
    while(1) {
        do_work();
        // No delay! Starves lower priority tasks!
    }
}

// ✅ CORRECT: Always delay
void task_good(void *params) {
    while(1) {
        do_work();
        vTaskDelay(pdMS_TO_TICKS(10));  // Give others a chance
    }
}
```

### Mistake 2: Stack Too Small

```c
// ❌ WRONG: Stack overflow likely
xTaskCreate(task_complex, "Task", 64, NULL, 1, NULL);
// 64 words = 256 bytes, too small for complex task

// ✅ CORRECT: Adequate stack
xTaskCreate(task_complex, "Task", 256, NULL, 1, NULL);
// 256 words = 1KB
```

### Mistake 3: Wrong Priority

```c
// ❌ WRONG: Critical task too low priority
xTaskCreate(task_motor_control, "Motor", 256, NULL, 1, NULL);
// Serial task might delay motor control!

// ✅ CORRECT: Motor control highest priority
xTaskCreate(task_motor_control, "Motor", 256, NULL, 10, NULL);
xTaskCreate(task_serial, "Serial", 256, NULL, 5, NULL);
```

---

## Exercise: Create a Periodic Task

**Task**: Create a task that toggles an LED every 200ms exactly.

**Requirements**:
- Use vTaskDelayUntil (no drift)
- Priority 2
- Stack 128 words

**Answer**:

<details>
<summary>Click for answer</summary>

```c
void task_led_toggle(void *params)
{
    // Initialize LED
    GPIO_Init(LED_PIN);
    
    // Setup timing
    TickType_t last_wake = xTaskGetTickCount();
    const TickType_t period = pdMS_TO_TICKS(200);
    
    while(1) {
        // Toggle LED
        GPIO_Toggle(LED_PIN);
        
        // Wait exactly 200ms
        vTaskDelayUntil(&last_wake, period);
    }
}

int main(void)
{
    xTaskCreate(
        task_led_toggle,
        "LED_Toggle",
        128,      // Stack
        NULL,     // No params
        2,        // Priority
        NULL      // No handle
    );
    
    vTaskStartScheduler();
    while(1);
}
```

</details>

---

## Summary

- **Task**: Independent function that runs forever with a delay
- **xTaskCreate()**: Creates a task with function, stack, priority
- **Scheduler**: Decides which task runs (highest priority ready)
- **vTaskDelay()**: Relative delay (simple, but drifts)
- **vTaskDelayUntil()**: Absolute delay (periodic, no drift)
- **Stack**: Must be large enough for local variables and calls
- **Priority**: Higher number = more important

---

## Next Lesson

[[22-inter-task-communication]] - Queues, semaphores, and mutexes

---

*OrbiBot Firmware Study Guide*  
*Part 2 of 10*