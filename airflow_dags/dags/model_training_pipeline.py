
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import os,yaml,pandas as pd,joblib
from sklearn.linear_model import LinearRegression
def train():
    db=yaml.safe_load(open('configs/db_config.yaml'))
    os.makedirs(db['registry_dir'],exist_ok=True)
    f=os.path.join(db['processed_dir'],'features.csv')
    if not os.path.exists(f):
        pd.DataFrame({'stat':[0.1,0.2,0.3],'timestamp':[1,2,3]}).to_csv(f,index=False)
    df=pd.read_csv(f)
    X=df[['timestamp']].values
    y=df['stat'].values
    m=LinearRegression().fit(X,y)
    joblib.dump(m,os.path.join(db['registry_dir'],'model.pkl'))
    return 'ok'
with DAG('model_training_pipeline',start_date=datetime(2025,1,1),schedule='@daily',catchup=False) as dag:
    t=PythonOperator(task_id='train',python_callable=train)
