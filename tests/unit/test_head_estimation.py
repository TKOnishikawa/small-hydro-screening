import math
from unittest.mock import patch

import pytest

from small_hydro.compute.head_estimation import estimate_head_proxy, offset_point
from small_hydro.config import Config


@pytest.fixture
def cfg():
    return Config(
        target_bbox=(135.8, 34.5, 138.3, 36.5),
        gsi_api_rate_limit_sec=0.0,
        gsi_api_base_url="http://example.com",
        min_output_kw=10.0,
        min_head_m=2.0,
    )


def test_offset_north_increases_lat(cfg):
    new_lat, new_lon = offset_point(35.0, 137.0, dlat_m=100, dlon_m=0)
    assert new_lat > 35.0
    assert new_lon == pytest.approx(137.0)


def test_offset_east_increases_lon(cfg):
    new_lat, new_lon = offset_point(35.0, 137.0, dlat_m=0, dlon_m=100)
    assert new_lat == pytest.approx(35.0)
    assert new_lon > 137.0


def test_offset_distance_approximate():
    """100m北に動かすと緯度差は約 100/111000 ≈ 0.0009度。"""
    new_lat, _ = offset_point(35.0, 137.0, dlat_m=100, dlon_m=0)
    expected_dlat = 100 / 111_000
    assert abs((new_lat - 35.0) - expected_dlat) < 1e-5


def test_estimate_head_proxy_basic(cfg):
    fake = [(100.0, "5m（レーザ）"), (95.0, "5m（レーザ）"),
            (98.0, "5m（レーザ）"), (102.0, "5m（レーザ）")]
    with patch(
        "small_hydro.compute.head_estimation.fetch_elevations",
        return_value=fake,
    ):
        head, samples = estimate_head_proxy(35.0, 137.0, cfg)
    assert head == pytest.approx(7.0)  # 102 - 95
    assert len(samples) == 4


def test_estimate_head_proxy_all_none(cfg):
    fake = [(None, None)] * 4
    with patch(
        "small_hydro.compute.head_estimation.fetch_elevations",
        return_value=fake,
    ):
        head, samples = estimate_head_proxy(35.0, 137.0, cfg)
    assert head == 0.0
