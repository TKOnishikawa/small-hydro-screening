.PHONY: setup fetch screen map test lint clean

setup:
	python -m pip install -e ".[dev,scrape]" || pip install -r requirements.txt

fetch:
	python -m small_hydro.cli fetch --source=repos

screen:
	python -m small_hydro.cli screen

map:
	python -m small_hydro.cli export --format=geojson

test:
	pytest tests/ -v

lint:
	ruff check src/ tests/

clean:
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in [pathlib.Path('data/interim'), pathlib.Path('data/processed')]]"
	python -c "import pathlib; [pathlib.Path(d).mkdir(exist_ok=True) for d in ['data/interim', 'data/processed']]"
