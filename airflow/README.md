# Local Airflow

The repository DAG is designed for Apache Airflow and Cloud Composer. For a
local scheduler, use the official Airflow quick-start installation with the
matching constraints file for the Python version. Then:

```bash
export AIRFLOW_HOME="$PWD/.airflow"
export PYTHONPATH="$PWD/src:$PWD"
airflow db migrate
airflow dags list
airflow dags test finance_invoice_to_cash 2026-01-31
```

Set the DAG's `ROOT` to a writable path containing the Kaggle credentials and
the downloaded source files. Do not mount `~/.kaggle/kaggle.json` into a
production worker without using a secret manager.

The final DAG task runs `dbt source freshness` followed by `dbt build`. Set
`GCP_PROJECT_ID` and ensure the worker has BigQuery credentials before running
the task. A local `dags test` run can stop before that task when no GCP project
is configured.
