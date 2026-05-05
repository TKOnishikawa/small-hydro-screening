"""経済性試算モジュール。

FIT制度（2024年度新規水力）ベースで売電収入・O&M・回収期間・IRRを算出する。

前提:
- FIT単価: 200kW未満=34円/kWh、200-1000kW=29円/kWh、1000-5000kW=27円/kWh、5000kW+=20円/kWh
- FIT期間: 20年
- O&M費用: CAPEX × 2%/年 が標準（業界rule of thumb）
- FIT期間後10年: 売電単価が実質半減と仮定（市場価格相場）

注意:
- 税抜の値で統一
- 実際の事業性は水利権・系統工事費・用地条件等により大きく変動
- ここは「机上スクリーニング」のための比較指標として活用すること
"""

FIT_PRICES_JPY_PER_KWH: dict[float, float] = {
    200.0: 34.0,
    1000.0: 29.0,
    5000.0: 27.0,
    float("inf"): 20.0,
}
DEFAULT_OM_RATE = 0.02
DEFAULT_FIT_YEARS = 20
DEFAULT_POST_FIT_YEARS = 10
DEFAULT_POST_FIT_RATIO = 0.5


def fit_unit_price_jpy(output_kw: float) -> float:
    if output_kw is None or output_kw <= 0:
        return 0.0
    for threshold in sorted(FIT_PRICES_JPY_PER_KWH.keys()):
        if output_kw < threshold:
            return FIT_PRICES_JPY_PER_KWH[threshold]
    return FIT_PRICES_JPY_PER_KWH[float("inf")]


def annual_revenue_jpy(annual_kwh: float, output_kw: float) -> float:
    if annual_kwh is None or annual_kwh <= 0:
        return 0.0
    return annual_kwh * fit_unit_price_jpy(output_kw)


def annual_om_cost_jpy(
    const_cost_mjpy: float, om_rate: float = DEFAULT_OM_RATE
) -> float:
    if const_cost_mjpy is None or const_cost_mjpy <= 0:
        return 0.0
    return const_cost_mjpy * 1_000_000 * om_rate


def annual_net_cashflow_jpy(
    annual_kwh: float,
    output_kw: float,
    const_cost_mjpy: float,
    om_rate: float = DEFAULT_OM_RATE,
) -> float:
    return annual_revenue_jpy(annual_kwh, output_kw) - annual_om_cost_jpy(
        const_cost_mjpy, om_rate
    )


def simple_payback_years(
    annual_kwh: float,
    output_kw: float,
    const_cost_mjpy: float,
    om_rate: float = DEFAULT_OM_RATE,
) -> float | None:
    if (
        annual_kwh is None
        or output_kw is None
        or const_cost_mjpy is None
        or annual_kwh <= 0
        or output_kw <= 0
        or const_cost_mjpy <= 0
    ):
        return None
    cf = annual_net_cashflow_jpy(annual_kwh, output_kw, const_cost_mjpy, om_rate)
    if cf <= 0:
        return None
    capex = const_cost_mjpy * 1_000_000
    return capex / cf


def _newton_irr(
    cashflows: list[float],
    guess: float = 0.05,
    max_iter: int = 200,
    tol: float = 1e-7,
) -> float | None:
    """Newton-Raphson IRR. cashflows[0] が負のCAPEX。"""
    if not cashflows or cashflows[0] >= 0:
        return None
    rate = guess
    for _ in range(max_iter):
        if rate <= -0.99:
            return None
        try:
            npv = sum(cf / (1 + rate) ** i for i, cf in enumerate(cashflows))
            dnpv = sum(
                -i * cf / (1 + rate) ** (i + 1) for i, cf in enumerate(cashflows)
            )
        except OverflowError:
            return None
        if abs(dnpv) < tol:
            return None
        new_rate = rate - npv / dnpv
        if abs(new_rate - rate) < tol:
            return new_rate
        rate = new_rate
    return None


def project_irr(
    annual_kwh: float,
    output_kw: float,
    const_cost_mjpy: float,
    fit_years: int = DEFAULT_FIT_YEARS,
    post_fit_years: int = DEFAULT_POST_FIT_YEARS,
    post_fit_ratio: float = DEFAULT_POST_FIT_RATIO,
    om_rate: float = DEFAULT_OM_RATE,
) -> float | None:
    """FIT 20年 + post-FIT 10年（売電単価ratio倍）でのIRR。"""
    if (
        annual_kwh is None
        or output_kw is None
        or const_cost_mjpy is None
        or annual_kwh <= 0
        or output_kw <= 0
        or const_cost_mjpy <= 0
    ):
        return None
    capex = const_cost_mjpy * 1_000_000
    rev = annual_revenue_jpy(annual_kwh, output_kw)
    om = annual_om_cost_jpy(const_cost_mjpy, om_rate)

    cf = [-capex]
    cf.extend([rev - om] * fit_years)
    cf.extend([rev * post_fit_ratio - om] * post_fit_years)
    return _newton_irr(cf)


SCENARIO_RATES_MJPY_PER_KW: dict[str, float | None] = {
    "optimistic": 1.5,
    "standard": 2.5,
    "repos": None,
}
SCENARIO_LABELS: dict[str, str] = {
    "optimistic": "楽観",
    "standard": "標準",
    "repos": "REPOS悲観",
}


def cost_for_scenario(
    scenario: str,
    output_kw: float,
    repos_cost_mjpy: float,
    near_weir: bool = False,
) -> float | None:
    """シナリオ別の建設費を算出。

    - optimistic: 1.5百万/kW（既存堰活用想定の業界下限）
    - standard:   2.5百万/kW（NEF実例平均）。near_weir なら 0.85 倍
    - repos:      REPOSのCONST_COSTそのまま（保守的悲観値）
    """
    if output_kw is None or output_kw <= 0:
        return None
    if scenario == "repos":
        return repos_cost_mjpy if (repos_cost_mjpy and repos_cost_mjpy > 0) else None
    rate = SCENARIO_RATES_MJPY_PER_KW.get(scenario)
    if rate is None:
        return None
    if scenario == "standard" and near_weir:
        rate *= 0.85
    return output_kw * rate


def compute_economics_scenarios(
    annual_kwh: float,
    output_kw: float,
    repos_cost_mjpy: float,
    near_weir: bool = False,
    om_rate: float = DEFAULT_OM_RATE,
) -> dict[str, dict]:
    """3シナリオ（楽観/標準/REPOS悲観）の経済性指標を返す。"""
    result: dict[str, dict] = {}
    for scenario in SCENARIO_RATES_MJPY_PER_KW:
        cost = cost_for_scenario(scenario, output_kw, repos_cost_mjpy, near_weir)
        if cost is None or cost <= 0:
            result[scenario] = {
                "label": SCENARIO_LABELS[scenario],
                "cost_mjpy": None,
                "cost_per_kw": None,
                "annual_revenue_jpy": None,
                "annual_om_jpy": None,
                "annual_cf_jpy": None,
                "payback_years": None,
                "irr": None,
                "fit_unit_jpy": None,
            }
            continue
        econ = compute_economics(annual_kwh, output_kw, cost, om_rate=om_rate)
        result[scenario] = {
            "label": SCENARIO_LABELS[scenario],
            "cost_mjpy": cost,
            "cost_per_kw": cost / output_kw if output_kw > 0 else None,
            **econ,
        }
    return result


def compute_economics(
    annual_kwh: float,
    output_kw: float,
    const_cost_mjpy: float,
    om_rate: float = DEFAULT_OM_RATE,
) -> dict:
    """全指標を一気に返す。NaN安全。"""
    return {
        "fit_unit_jpy": fit_unit_price_jpy(output_kw),
        "annual_revenue_jpy": annual_revenue_jpy(annual_kwh, output_kw),
        "annual_om_jpy": annual_om_cost_jpy(const_cost_mjpy, om_rate),
        "annual_cf_jpy": annual_net_cashflow_jpy(
            annual_kwh, output_kw, const_cost_mjpy, om_rate
        ),
        "payback_years": simple_payback_years(
            annual_kwh, output_kw, const_cost_mjpy, om_rate
        ),
        "irr": project_irr(annual_kwh, output_kw, const_cost_mjpy, om_rate=om_rate),
    }
