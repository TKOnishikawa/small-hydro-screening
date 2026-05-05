import pytest

from small_hydro.compute.economics import (
    annual_om_cost_jpy,
    annual_revenue_jpy,
    compute_economics,
    fit_unit_price_jpy,
    project_irr,
    simple_payback_years,
)


def test_fit_unit_price_bands():
    assert fit_unit_price_jpy(50) == 34
    assert fit_unit_price_jpy(199) == 34
    assert fit_unit_price_jpy(200) == 29
    assert fit_unit_price_jpy(999) == 29
    assert fit_unit_price_jpy(1000) == 27
    assert fit_unit_price_jpy(5000) == 20


def test_revenue_basic():
    rev = annual_revenue_jpy(500_000, 100)
    assert rev == 500_000 * 34


def test_revenue_zero():
    assert annual_revenue_jpy(0, 100) == 0
    assert annual_revenue_jpy(500_000, 0) == 0


def test_om_cost():
    assert annual_om_cost_jpy(500) == 500 * 1_000_000 * 0.02
    assert annual_om_cost_jpy(0) == 0


def test_simple_payback():
    # 500,000 kWh × 34円 = 1,700万円/年, O&M=400万/年 → CF=1,300万/年
    # CAPEX=200百万円 / CF=1,300万円 = 約15.4年
    payback = simple_payback_years(500_000, 100, 200)
    assert payback is not None
    assert 14 < payback < 17


def test_payback_unprofitable():
    assert simple_payback_years(100, 1, 10000) is None


def test_irr_positive():
    irr = project_irr(500_000, 100, 200)
    assert irr is not None
    assert 0.0 < irr < 0.10  # 約3.7%程度の見込み


def test_compute_economics_full():
    e = compute_economics(500_000, 100, 200)
    assert e["fit_unit_jpy"] == 34
    assert e["annual_revenue_jpy"] > 0
    assert e["annual_om_jpy"] > 0
    assert e["annual_cf_jpy"] > 0
    assert e["payback_years"] is not None
    assert e["irr"] is not None
