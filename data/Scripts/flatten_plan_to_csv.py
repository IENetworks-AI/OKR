import json
import pandas as pd

# Load JSON file with UTF-8 encoding to avoid Unicode errors
with open("plan_tasks_raw.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Prepare a list to hold flattened rows
flattened_rows = []

# Iterate over each weekly plan (top-level list)
for weekly_plan in data:
    weekly_plan_id = weekly_plan.get("id")
    weekly_plan_desc = weekly_plan.get("description")

    for weekly_task in weekly_plan.get("tasks", []):
        weekly_task_id = weekly_task.get("id")
        weekly_task_name = weekly_task.get("task")
        weekly_task_weight = weekly_task.get("weight")
        weekly_task_priority = weekly_task.get("priority")

        # If there are daily tasks under planTask
        for daily_task in weekly_task.get("planTask", []):
            daily_task_id = daily_task.get("id")
            daily_task_name = daily_task.get("task")
            daily_task_weight = daily_task.get("weight")
            daily_task_priority = daily_task.get("priority")

            flattened_rows.append(
                {
                    "weekly_plan_id": weekly_plan_id,
                    "weekly_plan_desc": weekly_plan_desc,
                    "weekly_task_id": weekly_task_id,
                    "weekly_task_name": weekly_task_name,
                    "weekly_task_weight": weekly_task_weight,
                    "weekly_task_priority": weekly_task_priority,
                    "daily_task_id": daily_task_id,
                    "daily_task_name": daily_task_name,
                    "daily_task_weight": daily_task_weight,
                    "daily_task_priority": daily_task_priority,
                }
            )

# Convert to DataFrame
df = pd.DataFrame(flattened_rows)

# Save to CSV
df.to_csv("flattened_tasks.csv", index=False, encoding="utf-8")

print("Flattening complete! Saved to flattened_tasks.csv")
