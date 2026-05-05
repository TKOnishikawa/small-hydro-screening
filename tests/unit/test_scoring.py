import pandas as pd
import pytest

from small_hydro.compute.scoring import score_candidates
from small_hydro.config import Config


@pytest.fixture
def cfg():
    return Config(
        target_bbox=(136.0, 35.0, 138.0, 36.0),
        gsi_api_rate_limit_sec=0.0,
        gsi_api_base_url="http://example.com",
        min_output_kw=10.0,
        min_head_m=2.0,
    )


def test_filter_low_output(cfg):
    df = pd.DataFrame({
        "head_m": [10, 10, 10],
        "output_kw_drought": [5, 50, 100],
        "output_kw_normal": [10, 75, 150],
    })
    result = score_candidates(df, cfg)
    assert len(result) == 2


def test_filter_low_head(cfg):
    df = pd.DataFrame({
        "head_m": [1, 5, 10],
        "output_kw_drought": [50, 50, 50],
        "output_kw_normal": [75, 75, 75],
    })
    result = score_candidates(df, cfg)
    assert len(result) == 2


def test_score_descending(cfg):
    df = pd.DataFrame({
        "head_m": [10, 10, 10],
        "output_kw_drought": [50, 100, 30],
        "output_kw_normal": [75, 150, 45],
    })
    result = score_candidates(df, cfg)
    assert result["score"].is_monotonic_decreasing


def test_grid_factor_optional(cfg):
    df = pd.DataFrame({
        "head_m": [10, 10],
        "output_kw_drought": [50, 100],
        "output_kw_normal": [75, 150],
        "grid_capacity_factor": [1.0, 0.0],
    })
    result = score_candidates(df, cfg)
    assert "score" in result.columns
    assert result.iloc[0]["score"] >= result.iloc[1]["score"]
