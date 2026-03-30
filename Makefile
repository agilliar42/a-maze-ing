install:
	pip install poetry
	python -m poetry install

.venv:
	python -m venv .venv

venv-bash: .venv
	bash --init-file <(echo ". ~/.bashrc; . .venv/bin/activate")

run-prof:
	python -m poetry run python -m cProfile -o out.prof a_maze_ing.py
	python -m flameprof out.prof > prof.svg

run:
	python -m poetry run python a_maze_ing.py minimal_visual.conf

build:
	python -m poetry build -o .

clean:
	# sketchy rf rm
	rm -rf __pycache__ **/__pycache__

lint:
	python -m poetry run flake8 .
	python -m poetry run mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	python -m poetry run flake8 . --extend-exclude .venv
	python -m poetry run mypy . --strict

profile:
	python -m cProfile -o out.prof __main__.py

.PHONY: install venv  run clean lint lint-strict profile build
