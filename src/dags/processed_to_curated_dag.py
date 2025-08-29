from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import os

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.db import get_db_connection, insert_curated_documents  # type: ignore
from data.preprocessing import to_model_json, chunk_text  # type: ignore


DEFAULT_ARGS = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 0,
}


def build_documents(**context):
    docs = []
    with get_db_connection("okr_processed") as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT record_id, source_file_id, source_row_num, department, objective, objective_type,
                       priority, quarter, team_size, budget, timeline_days, progress, status,
                       valid, rejected_reason, original_payload
                FROM public.records_clean
                WHERE valid = true
                ORDER BY processed_at DESC
                LIMIT 10000
            """)
            for row in cur.fetchall():
                payload = row[15]
                model_json = to_model_json(payload if isinstance(payload, dict) else {})
                text = model_json.get('text', '')
                chunks = chunk_text(text, max_tokens=400, overlap=80) or [text]
                for ch in chunks:
                    docs.append({
                        'text': ch,
                        'meta': {
                            'source_file': payload.get('_source_file') if isinstance(payload, dict) else None,
                            'row_num': payload.get('_row_num') if isinstance(payload, dict) else None,
                            'labels': model_json.get('labels'),
                        }
                    })

    with get_db_connection("okr_curated") as cconn:
        insert_curated_documents(cconn, docs)
    context['task_instance'].xcom_push(key='doc_count', value=len(docs))
    return f"Inserted {len(docs)} documents into okr_curated.documents"


with DAG(
    dag_id='processed_to_curated_dag',
    default_args=DEFAULT_ARGS,
    description='Build model-ready documents from processed records',
    schedule=None,
    catchup=False,
) as dag:
    t_build = PythonOperator(
        task_id='build_documents',
        python_callable=build_documents,
    )

