.PHONY: test compile demo download airflow-up terraform-fmt

PYTHON ?= python3

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

compile:
	PYTHONPATH=src $(PYTHON) -m compileall -q src dags scripts tests

demo:
	PYTHONPATH=src $(PYTHON) -m finpulse run --output data/demo

download:
	PYTHONPATH=src $(PYTHON) scripts/download_b2b_dataset.py

airflow-up:
	docker compose -f docker-compose.airflow.yml up

terraform-fmt:
	terraform -chdir=terraform/envs/dev fmt -recursive
	terraform -chdir=terraform/envs/prod fmt -recursive
