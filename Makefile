install:
	pip install flake8 mypy flameprof

.venv:
	python -m venv .venv

venv_bash: .venv
	bash --init-file <(echo ". ~/.bashrc; export TERM=xterm-256color; . .venv/bin/activate")

run-prof:
	python -m cProfile -o out.prof __main__.py
	flameprof out.prof > prof.svg

run:

clean:

lint:
	flake8 .
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	bash -c "flake8 . --extend-exclude .venv; mypy . --strict"

profile:
	python -m cProfile -o out.prof __main__.py

.PHONY: install venv  run clean lint lint-strict profile
