
#!/usr/bin/env bash
set -e
export AIRFLOW_HOME=/home/ubuntu/airflow
mkdir -p "$AIRFLOW_HOME/dags"
airflow db init
cp -r airflow_dags/dags/* "$AIRFLOW_HOME/dags/"
