ROOT_PATH = poetry_python_template/src
format:
	@echo "formating"
	poetry run ruff format $(ROOT_PATH)

type:
	@echo "check typing"
	poetry run mypy $(ROOT_PATH)

lint:
	@echo "check PEP8"
	poetry run ruff check .

run:
	@echo "start prod server"
	fastapi run $(ROOT_PATH)/main.py

dev:
	@echo "start dev server"
	fastapi dev $(ROOT_PATH)/main.py

ddev:
	@echo "start docker dev containers"
	docker compose -f docker/docker-compose.test.yml up

dprod:
	@echo "start docker prod containers"
	docker compose -f docker/docker-compose.prod.yml up

mkmigrate:
	@echo "create alembic migrations $(if $(BRANCH),with label $(BRANCH),without branch label)"
	cd $(ROOT_PATH) && python3 create_migrations.py $(if $(BRANCH),--branch-label $(BRANCH))

migrate:
	@echo "perform alembic migrations"
	cd $(ROOT_PATH) && alembic upgrade heads

mrmigrate:
	@echo "Merge alembic heads"
	cd $(ROOT_PATH) && alembic merge heads

itest:
	@echo "run integrational tests"
	pytest poetry_python_template/integrational_tests --junitxml=integration-test-results.xml

utest:
	@echo "run unit test"
	pytest poetry_python_template/tests --junitxml=unit-test-results.xml
