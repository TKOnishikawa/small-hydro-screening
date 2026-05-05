import pytest

from small_hydro.compute.head import compute_head


def test_basic_head():
    assert compute_head(100, 50) == 50


def test_zero_head_raises():
    with pytest.raises(ValueError):
        compute_head(50, 50)


def test_inverted_raises():
    with pytest.raises(ValueError):
        compute_head(50, 100)
