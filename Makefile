.PHONY: test lint typecheck quality migrate api-dev web-dev web-verify verify

test:
	python -m pytest

lint:
	python -m ruff check apps packages workers tests

typecheck:
	python -m mypy packages workers apps/api

quality:
	python -m packages.verification.quality

migrate:
	python -m alembic upgrade head

api-dev:
	python -m uvicorn apps.api.main:app --reload

web-dev:
	npm --prefix apps/web run dev

web-verify:
	npm --prefix apps/web run lint
	npm --prefix apps/web run typecheck
	npm --prefix apps/web test
	npm --prefix apps/web run build

verify: lint typecheck test quality web-verify

