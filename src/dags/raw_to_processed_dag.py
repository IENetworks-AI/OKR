from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable
from datetime import datetime, timedelta
import os
import json

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.db import get_db_connection, get_raw_records, insert_processed_records  # type: ignore
from data.preprocessing import validate_and_clean  # type: ignore


DEFAULT_ARGS = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 0,
}


def process_raw_to_clean(**context):
    conf = context.get('dag_run').conf or {}
    file_id = conf.get('file_id')
    batch_id = conf.get('batch_id')

    cleaned = []
    with get_db_connection("okr_raw") as raw_conn:
        if not file_id:
            # scan by batch_id metadata in payload
            with raw_conn.cursor() as cur:
                cur.execute("""
                    SELECT record_id, file_id, row_num, payload, loaded_at
                    FROM public.records
                    WHERE payload ? '_batch_id' AND payload->>'_batch_id' = %s
                    ORDER BY row_num
                """, (batch_id,))
                rows = cur.fetchall()
                for r in rows:
                    rec = dict(r[3])
                    rec['_row_num'] = r[2]
                    rec['_source_file'] = rec.get('_file_path')
                    c, ok = validate_and_clean(rec)
                    c['_source_file_id'] = str(r[1])
                    cleaned.append(c)
        else:
            # iterate helper for file_id
            for rec in get_raw_records(raw_conn, file_id):
                rec['_source_file'] = rec.get('_file_path')
                c, ok = validate_and_clean(rec)
                c['_source_file_id'] = file_id
                cleaned.append(c)

    # write to processed
    with get_db_connection("okr_processed") as proc_conn:
        insert_processed_records(proc_conn, cleaned)
    context['task_instance'].xcom_push(key='processed_count', value=len(cleaned))
    return f"Processed {len(cleaned)} records into okr_processed.records_clean"


with DAG(
    dag_id='raw_to_processed_dag',
    default_args=DEFAULT_ARGS,
    description='Transform raw records to cleaned records in okr_processed',
    schedule=None,
    catchup=False,
) as dag:
    t_process = PythonOperator(
        task_id='process_raw_to_clean',
        python_callable=process_raw_to_clean,
    )

