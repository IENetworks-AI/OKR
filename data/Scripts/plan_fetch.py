import requests
import os
import json
from dotenv import load_dotenv
import pandas as pd

# Load env variables
load_dotenv()

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")
TENANT_ID = os.getenv("TENANT_ID")

firebase_login_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
plan_tasks_url = "https://test-okr-backend.ienetworks.co/api/v1/plan-tasks"

# Step 1: Login to Firebase
login_payload = {
    "email": EMAIL,
    "password": PASSWORD,
    "returnSecureToken": True
}
firebase_resp = requests.post(firebase_login_url, json=login_payload)
firebase_resp.raise_for_status()
id_token = firebase_resp.json().get("idToken")

if not id_token:
    raise ValueError("❌ Login failed: no token returned.")

# Step 2: Use token to fetch plan tasks
headers = {
    "Authorization": f"Bearer {id_token}",
    "Content-Type": "application/json",
    "tenantId": TENANT_ID
}

response = requests.get(plan_tasks_url, headers=headers)
response.raise_for_status()
tasks = response.json()  # ✅ It’s already a list

# Step 3: Save raw data
with open("plan_tasks_raw.json", "w", encoding="utf-8") as f:
    json.dump(tasks, f, ensure_ascii=False, indent=4)

# Step 4: Save CSV
if tasks:
    df = pd.json_normalize(tasks)
    df.to_csv("plan_tasks_raw.csv", index=False)
    print(f"✅ {len(tasks)} tasks saved to plan_tasks_raw.json and plan_tasks_raw.csv")
else:
    print("⚠️ No tasks found in response.")
