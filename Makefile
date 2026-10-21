.PHONY: test unit-test integration-test compile demo download airflow-up sqlserver-up terraform-fmt lint validate-env

PYTHON ?= python3

# Developer shortcut: python -m pytest tests/ -v
test:
	PYTHONPATH=. $(PYTHON) -m pytest tests/ -v

unit-test:
	PYTHONPATH=. $(PYTHON) -m pytest tests/unit/ -v

integration-test:
	PYTHONPATH=. $(PYTHON) -m pytest tests/integration/ -v

compile:
	PYTHONPATH=. $(PYTHON) -m compileall -q pipeline dags scripts

demo:
	PYTHONPATH=. $(PYTHON) -m pipeline run --output data/demo

download:
	PYTHONPATH=. $(PYTHON) scripts/download_b2b_dataset.py

airflow-up:
	docker compose -f docker-compose.airflow.yml up

sqlserver-up:
	docker compose -f docker-compose.airflow.yml up mssql -d

terraform-fmt:
	terraform -chdir=infra/terraform/envs/dev fmt -recursive
	terraform -chdir=infra/terraform/envs/prod fmt -recursive

validate-env:
	bash scripts/validate_env.sh

lint:
	$(PYTHON) -m compileall -q pipeline dags scripts tests
