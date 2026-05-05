import shutil
from pathlib import Path

import pytest

from small_hydro.ingest import repos as repos_module
from small_hydro import pipeline as pipeline_module

SAMPLE_CSV = Path(__file__).parent.parent / "fixtures" / "sample_data" / "repos_sample.csv"


@pytest.fixture
def repos_with_sample(tmp_path, monkeypatch):
    shutil.copy(SAMPLE_CSV, tmp_path / "repos.csv")
    monkeypatch.setattr(repos_module, "REPOS_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def env_vars(monkeypatch):
    monkeypatch.setenv("TARGET_BBOX", "136.0,35.0,138.0,36.0")
    monkeypatch.setenv("MIN_OUTPUT_KW", "10")
    monkeypatch.setenv("MIN_HEAD_M", "2")


def test_pipeline_smoke(repos_with_sample, env_vars):
    from small_hydro.pipeline import run_screening

    gdf = run_screening()
    assert len(gdf) == 3
    assert "score" in gdf.columns
    assert gdf["score"].is_monotonic_decreasing


def test_pipeline_export(repos_with_sample, env_vars, tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline_module, "OUTPUT_DIR", tmp_path)

    from small_hydro.pipeline import export_results, run_screening

    gdf = run_screening()
    csv_path = export_results(gdf, "csv")
    geo_path = export_results(gdf, "geojson")

    assert csv_path.exists()
    assert geo_path.exists()
    assert csv_path.stat().st_size > 0
    assert geo_path.stat().st_size > 0


def test_pipeline_filters_low_output(repos_with_sample, env_vars):
    from small_hydro.pipeline import run_screening

    gdf = run_screening()
    assert "小流D" not in gdf["river_name"].values
