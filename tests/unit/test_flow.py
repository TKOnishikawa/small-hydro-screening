import pandas as pd
import pytest

from small_hydro.compute.flow import (
    abundant_flow,
    drought_flow,
    flow_at_exceedance,
    normal_flow,
)


def make_descending_year():
    return pd.Series(list(range(365, 0, -1)))


def test_flow_at_exceedance_355():
    series = make_descending_year()
    assert flow_at_exceedance(series, 355) == 11


def test_too_short_data():
    series = pd.Series([1.0] * 100)
    with pytest.raises(ValueError):
        drought_flow(series)


def test_ordering():
    series = make_descending_year()
    assert abundant_flow(series) >= normal_flow(series) >= drought_flow(series)
