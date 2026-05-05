import pandas as pd
import pytest

from small_hydro.compute.composite_score import (
    capacity_factor_score,
    compute_composite,
    cost_efficiency_score,
    filter_anomalies,
    output_band_score,
    rank_candidates,
)


def test_band_score_priorities():
    assert output_band_score(75) == 1.0      # 50-100kW (最優先)
    assert output_band_score(120) == 0.7     # 100-150kW (次点)
    assert output_band_score(200) == 0.5     # 150-300kW
    assert output_band_score(40) == 0.4      # 30-50kW
    assert output_band_score(20) == 0.2
    assert output_band_score(500) == 0.1
    assert output_band_score(0) == 0.0
    assert output_band_score(float("nan")) == 0.0


def test_cost_efficiency():
    # 5百万円/kW でちょうど 1.0
    assert cost_efficiency_score(500, 100) == 1.0
    # 10百万円/kW で 0.5
    assert cost_efficiency_score(1000, 100) == 0.5
    # 異常値
    assert cost_efficiency_score(0, 100) == 0.0
    assert cost_efficiency_score(500, 0) == 0.0


def test_capacity_factor():
    # cf=0.5 で max
    annual = 0.5 * 100 * 8760
    assert capacity_factor_score(annual, 100) == 1.0
    # cf=0.25 で 0.5
    annual = 0.25 * 100 * 8760
    assert capacity_factor_score(annual, 100) == 0.5
    assert capacity_factor_score(0, 100) == 0.0


def test_compute_composite_basic():
    df = pd.DataFrame({
        "output_kw": [75, 120, 30, 200],
        "const_cost_mjpy": [400, 700, 100, 1500],
        "annual_kwh": [
            0.4 * 75 * 8760,
            0.4 * 120 * 8760,
            0.4 * 30 * 8760,
            0.4 * 200 * 8760,
        ],
        "near_weir": [True, False, False, False],
        "in_protected_area": [False, False, True, False],
    })
    out = compute_composite(df)
    assert "composite_score" in out.columns
    assert out.iloc[2]["composite_score"] == 0.0  # excluded (国立公園内)
    assert out.iloc[0]["composite_score"] > out.iloc[1]["composite_score"]


def test_rank_candidates_drops_excluded():
    df = pd.DataFrame({
        "output_kw": [75, 30],
        "const_cost_mjpy": [400, 100],
        "annual_kwh": [200000, 80000],
        "in_protected_area": [False, True],
    })
    ranked = rank_candidates(df)
    assert len(ranked) == 1
    assert ranked.iloc[0]["rank"] == 1


def test_filter_anomalies():
    df = pd.DataFrame({
        "output_kw": [75, 0, 50],
        "const_cost_mjpy": [400, 200, 0],
        "annual_kwh": [200000, 100000, 50000],
    })
    out = filter_anomalies(df)
    assert len(out) == 1
    assert out.iloc[0]["output_kw"] == 75
