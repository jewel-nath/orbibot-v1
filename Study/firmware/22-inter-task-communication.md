# Part 2: Inter-Task Communication

**Duration**: 25 minutes  
**Prerequisites**: [21-tasks-and-scheduler.md](21-tasks-and-scheduler.md)

---

## Learning Objectives

After this lesson, you will understand:
- Why tasks need to communicate
- Queues for data transfer
- Semaphores for signaling
- Mutexes for resource protection
- Critical sections for shared data

---

## Why Communicate Between Tasks?

```
OrbiBot Example:
┌─────────────────┐      Data       ┌─────────────────┐
│  Control Task   │ ←─────────────→ │  Comm Task      │
│  (Motor control)│   target_vel    │  (Serial port)  │
│                 │                 │                 │
│  Reads: target  │                 │  Writes: target │
│  velocity from  │                 │  velocity from  │
│  comm task      │                 │  ROS command    │
└─────────────────┘                 └─────────────────┘

Without communication: Tasks can't coordinate!
```

---

## Method 1: Queues

### What is a Queue?

A queue is a FIFO (First-In-First-Out) buffer for sending data between tasks.

```
Queue = Mailbox between tasks

Task A (Sender)          Queue              Task B (Receiver)
     │                   [   ]                   │
     │──"Hello"──→     [Hello]                  │
     │                   [   ]  ───→ "Hello" ───┤
     │                                          │
```

### Queue Creation

```c
#include "queue.h"

// Global queue handle
QueueHandle_t velocity_queue;

void setup(void)
{
    // Create queue: 10 items, each item is sizeof(float[3])
    velocity_queue = xQueueCreate(10, sizeof(float) * 3);
    
    if (velocity_queue == NULL) {
        // Failed to create queue
    }
}
```

### Sending to Queue

```c
// Task A: Send velocity command
void task_sender(void *params)
{
    float velocity[3] = {0.5, 0.0, 0.0};  // vx, vy, omega
    
    while(1) {
        // Send to queue (wait max 100ms if full)
        if (xQueueSend(velocity_queue, velocity, pdMS_TO_TICKS(100)) == pdPASS) {
            // Success
        } else {
            // Queue full, data lost
        }
        
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}
```

### Receiving from Queue

```c
// Task B: Receive and process
void task_receiver(void *params)
{
    float velocity[3];
    
    while(1) {
        // Receive from queue (wait forever)
        if (xQueueReceive(velocity_queue, velocity, portMAX_DELAY) == pdPASS) {
            // Process velocity
            float vx = velocity[0];
            float vy = velocity[1];
            float omega = velocity[2];
            
            printf("Received: vx=%.2f, vy=%.2f, w=%.2f\n", vx, vy, omega);
        }
    }
}
```

---

## Method 2: Semaphores

### Binary Semaphore (Signaling)

```
Use case: "Hey, something happened!"

Example: Button press detected by ISR, 
         Task processes the button
```

```c
SemaphoreHandle_t button_semaphore;

void setup(void)
{
    // Create binary semaphore
    button_semaphore = xSemaphoreCreateBinary();
}

// ISR: Button pressed
void EXTI0_IRQHandler(void)
{
    BaseType_t higher_priority_woken = pdFALSE;
    
    // Give semaphore from ISR
    xSemaphoreGiveFromISR(button_semaphore, &higher_priority_woken);
    
    portYIELD_FROM_ISR(higher_priority_woken);
}

// Task: Process button
void task_button_handler(void *params)
{
    while(1) {
        // Wait for semaphore (forever)
        if (xSemaphoreTake(button_semaphore, portMAX_DELAY) == pdPASS) {
            printf("Button pressed!\n");
            // Process button press
        }
    }
}
```

### Counting Semaphore

```
Use case: Count available resources
Example: Buffer slots available
```

---

## Method 3: Mutexes

### What is a Mutex?

**Mutex** = Mutual Exclusion = "Only one task at a time"

```
Shared Resource = UART port

Without mutex:
  Task A: "He"          Task B: "Wo"
  Together: "HeWo" (garbled!)

With mutex:
  Task A: [Lock] "Hello" [Unlock]
  Task B:          [Lock] "World" [Unlock]
  Result: "HelloWorld" (clean!)
```

### Mutex Usage

```c
SemaphoreHandle_t uart_mutex;

void setup(void)
{
    // Create mutex
    uart_mutex = xSemaphoreCreateMutex();
}

void task_1(void *params)
{
    while(1) {
        // Lock UART
        if (xSemaphoreTake(uart_mutex, pdMS_TO_TICKS(100)) == pdPASS) {
            printf("Task 1 message\n");
            
            // Unlock when done
            xSemaphoreGive(uart_mutex);
        }
        
        vTaskDelay(pdMS_TO_TICKS(500));
    }
}

void task_2(void *params)
{
    while(1) {
        if (xSemaphoreTake(uart_mutex, pdMS_TO_TICKS(100)) == pdPASS) {
            printf("Task 2 message\n");
            xSemaphoreGive(uart_mutex);
        }
        
        vTaskDelay(pdMS_TO_TICKS(300));
    }
}
```

---

## Method 4: Critical Sections

### For Quick Shared Data Access

```
Use when: Simple data read/write (not complex operations)

How it works: Disable interrupts briefly
```

```c
// Shared variable
volatile float target_velocity = 0.0f;

// Task A: Write
void task_command(void *params)
{
    while(1) {
        float new_vel = receive_from_ros();
        
        // Critical section: disable interrupts
        taskENTER_CRITICAL();
        target_velocity = new_vel;
        taskEXIT_CRITICAL();
        
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

// Task B: Read
void task_control(void *params)
{
    while(1) {
        float vel;
        
        // Critical section for read
        taskENTER_CRITICAL();
        vel = target_velocity;
        taskEXIT_CRITICAL();
        
        // Use vel...
        
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}
```

---

## Comparison: When to Use What?

| Mechanism | Use For | OrbiBot Example |
|-----------|---------|-----------------|
| **Queue** | Transfer data | Velocity commands from Comm to Control |
| **Binary Semaphore** | Signal event | IMU data ready |
| **Counting Semaphore** | Resource count | Buffer slots |
| **Mutex** | Protect resource | Shared UART access |
| **Critical Section** | Quick data access | target_velocity variable |

---

## OrbiBot's Communication Pattern

```
OrbiBot uses Critical Sections for most shared data:

┌─────────────────┐
│  Control Task   │─── target_velocity ───┐
│  (reads)        │                       │
└─────────────────┘                       │
                                          ▼
                                   ┌─────────────┐
                                   │ Shared Var  │ ← Protected by
                                   │ (volatile)  │   Critical Section
                                   └─────────────┘
                                          ▲
┌─────────────────┐                       │
│  Comm Task      │─── target_velocity ───┘
│  (writes)       │
└─────────────────┘

Why? Fast, simple, sufficient for simple data types
```

---

## Summary

- **Queue**: Pass data between tasks (FIFO)
- **Semaphore**: Signal events, count resources
- **Mutex**: Protect shared resources (one at a time)
- **Critical Section**: Quick protected access to variables

---

## Next Lesson

[23-orbibot-task-architecture.md](23-orbibot-task-architecture.md) - OrbiBot's 4 tasks in detail

---

*OrbiBot Firmware Study Guide*  
*Part 2 of 10*