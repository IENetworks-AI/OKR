import os
import sys

def main() -> int:
    expected = [
        'src/dags/csv_ingestion_dag.py',
        'src/dags/api_ingestion_dag.py',
        'src/dags/etl_pipeline.py',
        'apps/api/app.py',
        'docker-compose.yml',
    ]
    missing = [p for p in expected if not os.path.exists(p)]
    if missing:
        print('Missing required components:')
        for p in missing:
            print('-', p)
        return 1
    print('ETL pipeline components validated OK')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

