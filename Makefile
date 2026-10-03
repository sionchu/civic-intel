.PHONY: test lint typecheck quality architecture migrate api-dev web-dev web-verify worker-verify verify

test:
	python -m pytest

lint:
	python -m ruff check apps packages workers tests

typecheck:
	python -m mypy packages workers apps/api apps/cli

quality:
	python -m packages.verification.quality

architecture:
	python -m packages.verification.architecture

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

worker-verify:
	npm --prefix apps/web run build:worker
	npm --prefix apps/web run check:worker

verify: lint typecheck test quality architecture web-verify worker-verify

