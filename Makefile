install:
	pip install poetry
	poetry install

.venv:
	python -m venv .venv

venv_bash: .venv
	bash --init-file <(echo ". ~/.bashrc; export TERM=xterm-256color; . .venv/bin/activate")

run-prof:
	poetry run python -m cProfile -o out.prof a_maze_ing.py
	flameprof out.prof > prof.svg

run:
	poetry run python a_maze_ing.py

build:
	poetry build -o .

clean:

lint:
	poetry run flake8 .
	poetry run mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	poetry run flake8 . --extend-exclude .venv
	poetry run mypy . --strict

profile:
	python -m cProfile -o out.prof __main__.py

.PHONY: install venv  run clean lint lint-strict profile package
