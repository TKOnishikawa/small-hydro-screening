import shutil
from pathlib import Path

import pytest

from small_hydro.ingest import repos as repos_module
from small_hydro.ingest.repos import load_repos

SAMPLE_CSV = Path(__file__).parent.parent / "fixtures" / "sample_data" / "repos_sample.csv"


def test_load_repos_from_csv(tmp_path, monkeypatch):
    shutil.copy(SAMPLE_CSV, tmp_path / "repos.csv")
    monkeypatch.setattr(repos_module, "REPOS_DIR", tmp_path)

    gdf = load_repos()
    assert len(gdf) == 4
    assert "head_m" in gdf.columns
    assert "flow_m3s" in gdf.columns
    assert "output_kw" in gdf.columns
    assert "river_name" in gdf.columns
    assert gdf.crs.to_string() == "EPSG:4326"


def test_load_repos_missing_dir(tmp_path, monkeypatch):
    nonexistent = tmp_path / "does_not_exist"
    monkeypatch.setattr(repos_module, "REPOS_DIR", nonexistent)

    with pytest.raises(FileNotFoundError):
        load_repos()


def test_load_repos_empty_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(repos_module, "REPOS_DIR", tmp_path)

    with pytest.raises(FileNotFoundError):
        load_repos()


def test_load_repos_geometry_from_intake(tmp_path, monkeypatch):
    shutil.copy(SAMPLE_CSV, tmp_path / "repos.csv")
    monkeypatch.setattr(repos_module, "REPOS_DIR", tmp_path)

    gdf = load_repos()
    assert gdf.geometry.iloc[0].x == pytest.approx(137.0)
    assert gdf.geometry.iloc[0].y == pytest.approx(35.5)
