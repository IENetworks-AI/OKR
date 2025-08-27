#!/usr/bin/env python3
import os
import sys
import json
import yaml

def validate_yaml_files(paths):
    ok = True
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, 'r') as f:
                    yaml.safe_load(f)
                print(f"✓ {p} is valid YAML")
            except Exception as e:
                print(f"❌ {p} invalid YAML: {e}")
                ok = False
        else:
            print(f"⚠ {p} not found")
    return ok

def validate_airflow_dags(dags_path):
    try:
        from airflow.models import DagBag
    except Exception as e:
        print(f"⚠ Airflow not available: {e}")
        return True
    bag = DagBag(dags_path)
    if bag.import_errors:
        print("DAG import errors:")
        for fn, err in bag.import_errors.items():
            print(f"{fn}: {err}")
        return False
    print(f"✓ All DAGs imported from {dags_path}")
    return True

def main():
    configs = [
        'configs/db_config.yaml',
        'configs/kafka_config.yaml',
        'configs/model_config.yaml',
    ]
    ok = True
    ok &= validate_yaml_files(configs)
    ok &= validate_airflow_dags('src/dags')
    sys.exit(0 if ok else 1)

if __name__ == '__main__':
    main()

