
from datetime import datetime, timedelta
from textwrap import dedent
import os
# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
# Operators; we need this to operate!
from airflow.operators.bash import BashOperator
from airflow.operators.python_operator import PythonOperator



with DAG(
    "scrapignlast_last_100_day_news",
    default_args={
        "depends_on_past": False,
        "email": ["khaldi.yazid@gmail.com"],
        "email_on_failure": False,
        "email_on_retry": False,
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    },
    description="Scraping new articles every day for 5 days continuously",
    schedule="@once",
    start_date=datetime.now(),
    catchup=False,
    tags=["example"],
) as dag:
    t1 = BashOperator(
        task_id="scrapignlast_news",
        bash_command="python /opt/airflow/scraper/main.py"
    )


