# 06 - Actions

**Long-running tasks with feedback**

---

## 🎯 Learning Objectives

- Understand when to use actions
- Create action servers and clients
- Handle goals, feedback, and results

---

## 🎭 What are Actions?

**Actions** are for long-running tasks with progress updates.

### Analogy: Navigation

```
Goal: "Go to the kitchen"
├── Feedback: "Walking... 50% there"
├── Feedback: "Walking... 90% there"  
└── Result: "Arrived!" or "Blocked!"

Can cancel mid-way: "Stop, I changed my mind!"
```

### Actions vs Services

| Feature | Service | Action |
|---------|---------|--------|
| Duration | Short | Long |
| Feedback | ❌ No | ✅ Yes |
| Cancel | ❌ No | ✅ Yes |
| Use for | Enable motors | Navigate to goal |

---

## 📝 Action Structure

```
# Navigate.action
geometry_msgs/Pose goal    # Goal
---
bool success               # Result
string message             # Result
---
float32 percent_complete   # Feedback
```

---

## 🎯 OrbiBot Example

Navigation uses actions:

```python
# Send navigation goal
goal = NavigateToPose.Goal()
goal.pose = target_pose

action_client.send_goal_async(goal, feedback_callback)
```

---

## 🎯 Key Takeaways

1. **Actions** = Long tasks with feedback
2. **Goal** → **Feedback** → **Result**
3. **Can cancel** during execution
4. Use for **navigation**, **arm movement**

---

## 📖 Next Steps

**→ Continue to:** [07-parameters.md](07-parameters.md)

---

*Last Updated: March 2026*