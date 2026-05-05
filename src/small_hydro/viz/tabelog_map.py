"""食べログ風のインタラクティブマップ生成（Leaflet 直叩き）。

サイドバー(リスト) + 地図 のレイアウト。
- 出力帯/ソートのフィルタ
- 「このエリアで再検索」ボタン
- TOP50=赤★ / TOP100=橙★ / その他=出力帯色の円
- 改良ポップアップ（ランクバッジ・スコア棒・○良い点/×弱点）
- URL共有（位置・ズーム・フィルタを #hash に保存）
"""
import json
import math
from datetime import date
from pathlib import Path

import geopandas as gpd
import pandas as pd

DEFAULT_CENTER = [35.18, 136.91]


def _safe_float(v) -> float:
    if v is None:
        return 0.0
    try:
        if pd.isna(v):
            return 0.0
    except (TypeError, ValueError):
        pass
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _safe_str(v) -> str:
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass
    return str(v)


def _safe_bool(v) -> bool:
    if v is None:
        return False
    try:
        if pd.isna(v):
            return False
    except (TypeError, ValueError):
        pass
    return bool(v)


def _slim_scenario(s: dict) -> dict:
    """シナリオ辞書から map に必要な項目だけ抜き出して JSON 軽量化。"""
    return {
        "label": s.get("label"),
        "cost_per_kw": s.get("cost_per_kw"),
        "cost_mjpy": s.get("cost_mjpy"),
        "payback_years": s.get("payback_years"),
        "irr": s.get("irr"),
        "annual_revenue_jpy": s.get("annual_revenue_jpy"),
        "annual_om_jpy": s.get("annual_om_jpy"),
        "annual_cf_jpy": s.get("annual_cf_jpy"),
    }


def _candidate_dict(row: pd.Series) -> dict:
    from small_hydro.compute.economics import compute_economics_scenarios

    output_kw = _safe_float(row.get("output_kw"))
    annual_kwh = _safe_float(row.get("annual_kwh"))
    cost_mjpy = _safe_float(row.get("const_cost_mjpy"))
    near_weir = _safe_bool(row.get("near_weir"))

    scenarios = compute_economics_scenarios(annual_kwh, output_kw, cost_mjpy, near_weir=near_weir)
    standard = scenarios["standard"]

    return {
        "rank": int(row.get("rank", 0)) if pd.notna(row.get("rank", float("nan"))) else None,
        "lat": float(row.geometry.y),
        "lon": float(row.geometry.x),
        "output_kw": output_kw,
        "annual_kwh": annual_kwh,
        "cost_mjpy": cost_mjpy,
        "cost_per_kw": _safe_float(row.get("cost_per_kw_mjpy")),
        "composite": _safe_float(row.get("composite_score")),
        "band_score": _safe_float(row.get("band_score")),
        "cost_score": _safe_float(row.get("cost_score")),
        "cf_score": _safe_float(row.get("cf_score")),
        "weir_bonus": _safe_float(row.get("weir_bonus")),
        "near_weir": near_weir,
        "in_park": _safe_bool(row.get("in_protected_area")),
        "prefecture": _safe_str(row.get("prefecture")),
        "municipality": _safe_str(row.get("municipality")),
        "linkid": _safe_str(row.get("linkid")),
        "scenarios": {
            "optimistic": _slim_scenario(scenarios["optimistic"]),
            "standard": _slim_scenario(standard),
            "repos": _slim_scenario(scenarios["repos"]),
        },
        "payback_years": standard.get("payback_years"),
        "irr": standard.get("irr"),
    }


def generate_tabelog_map(
    gdf: gpd.GeoDataFrame,
    output_path: Path,
    protected_areas: gpd.GeoDataFrame | None = None,
) -> Path:
    if "composite_score" in gdf.columns:
        gdf = gdf.sort_values("composite_score", ascending=False).reset_index(drop=True)
        if "rank" not in gdf.columns:
            gdf["rank"] = gdf.index + 1

    candidates = [_candidate_dict(row) for _, row in gdf.iterrows()]
    candidates_json = json.dumps(candidates, ensure_ascii=False)

    if protected_areas is not None and not protected_areas.empty:
        cols = [c for c in ["geometry", "name", "boundary"] if c in protected_areas.columns]
        parks_geojson = protected_areas[cols].to_json()
    else:
        parks_geojson = '{"type":"FeatureCollection","features":[]}'

    if len(gdf) > 0:
        center = [float(gdf.geometry.y.mean()), float(gdf.geometry.x.mean())]
    else:
        center = DEFAULT_CENTER

    html = _HTML_TEMPLATE \
        .replace("__CSS__", _CSS) \
        .replace("__JS__", _JS) \
        .replace("__CANDIDATES__", candidates_json) \
        .replace("__PROTECTED__", parks_geojson) \
        .replace("__CENTER__", json.dumps(center)) \
        .replace("__TOTAL__", str(len(gdf))) \
        .replace("__UPDATED_AT__", date.today().strftime("%Y-%m-%d"))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path


_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; overflow: hidden; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Hiragino Kaku Gothic ProN",
               "Yu Gothic", "Noto Sans JP", sans-serif;
  color: #1f2937;
  background: #f9fafb;
}
#app { display: flex; height: 100vh; width: 100vw; }

/* Sidebar */
#sidebar {
  width: 380px;
  min-width: 380px;
  border-right: 1px solid #e5e7eb;
  background: #fafafa;
  display: flex;
  flex-direction: column;
}
.sidebar-header {
  padding: 12px 16px 10px;
  border-bottom: 1px solid #e5e7eb;
  background: white;
}
.sidebar-header h1 {
  font-size: 13px;
  font-weight: 700;
  color: #1A365D;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.sidebar-header h1::before { content: "💧"; }

.filter-bar {
  display: flex;
  gap: 6px;
  margin-bottom: 6px;
}
.filter-bar select {
  flex: 1;
  font-size: 12px;
  padding: 5px 7px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: white;
  color: #1f2937;
  cursor: pointer;
}
.filter-bar select:hover { border-color: #2563eb; }
.result-count {
  font-size: 11px;
  color: #6b7280;
}
.result-count strong { color: #1A365D; font-weight: 700; }

#results {
  flex: 1;
  overflow-y: auto;
}
.list-item {
  padding: 12px 14px;
  border-bottom: 1px solid #f3f4f6;
  cursor: pointer;
  background: white;
  transition: background 0.1s;
}
.list-item:hover { background: #eff6ff; }
.list-item.top20 { border-left: 5px solid #dc2626; padding-left: 9px; }
.list-item.top50 { border-left: 5px solid #f97316; padding-left: 9px; }
.list-item.top100 { border-left: 5px solid #eab308; padding-left: 9px; }
.list-item.active { background: #dbeafe; }

.list-item-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 4px;
}
.list-rank-side { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
.list-rank-num {
  font-size: 13px;
  font-weight: 800;
  color: #6b7280;
  line-height: 1;
}
.list-rank-badge {
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.05em;
  padding: 2px 6px;
  border-radius: 3px;
  background: #e5e7eb;
  color: #6b7280;
}
.list-item.top20 .list-rank-num { color: #dc2626; }
.list-item.top20 .list-rank-badge { background: #fee2e2; color: #b91c1c; }
.list-item.top50 .list-rank-num { color: #f97316; }
.list-item.top50 .list-rank-badge { background: #ffedd5; color: #c2410c; }
.list-item.top100 .list-rank-num { color: #eab308; }
.list-item.top100 .list-rank-badge { background: #fef9c3; color: #a16207; }

.list-score-side {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}
.list-score-num {
  font-size: 18px;
  font-weight: 900;
  color: #1A365D;
  letter-spacing: -0.03em;
  line-height: 1;
}
.list-score-stars {
  color: #f59e0b;
  font-size: 11px;
  letter-spacing: 0.5px;
  margin-left: 2px;
}
.list-score-stars .empty { color: #d1d5db; }

.list-location {
  font-size: 14px;
  font-weight: 700;
  color: #1f2937;
  line-height: 1.2;
  margin-bottom: 4px;
}
.list-location strong { color: #1A365D; }

.list-output-line {
  font-size: 13px;
  color: #4b5563;
  margin-bottom: 4px;
  line-height: 1.3;
}
.list-output-kw {
  color: #0D6B3B;
  font-weight: 800;
  font-size: 14px;
}

.list-meta {
  font-size: 11px;
  color: #6b7280;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.list-meta-tag {
  background: #f3f4f6;
  padding: 1px 6px;
  border-radius: 3px;
  white-space: nowrap;
}
.list-meta-tag strong { color: #1f2937; }

.item-payback {
  background: #fef3c7;
  color: #92400e;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 3px;
}
.item-payback.good { background: #d1fae5; color: #065f46; }
.item-payback.bad { background: #fecaca; color: #991b1b; }

.item-weir-tag {
  background: #d1fae5;
  color: #065f46;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 3px;
}

/* Map */
#map-container { flex: 1; position: relative; }
#map { height: 100%; width: 100%; background: #e5e7eb; }
#search-area-btn {
  position: absolute;
  top: 14px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1100;
  padding: 10px 20px 10px 16px;
  background: white;
  color: #1f2937;
  border: 1.5px solid #d1d5db;
  border-radius: 24px;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  box-shadow:
    0 6px 18px rgba(0, 0, 0, 0.18),
    0 0 0 5px rgba(255, 255, 255, 0.55);
  transition: all 0.15s;
  white-space: nowrap;
}
#search-area-btn:hover {
  background: #2563eb;
  color: white;
  border-color: #2563eb;
  transform: translateX(-50%) translateY(-1px);
  box-shadow:
    0 8px 20px rgba(37, 99, 235, 0.45),
    0 0 0 5px rgba(255, 255, 255, 0.55);
}
#search-area-btn::before { content: "🔍"; margin-right: 6px; }

/* Markers - 3-tier stars with size + color heat scale */
.star-marker {
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 900;
  border: 2px solid white;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.4);
}
.star-top20 {
  width: 32px; height: 32px;
  background: #dc2626;
  font-size: 17px;
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.25), 0 2px 6px rgba(0, 0, 0, 0.5);
  animation: star-pulse 2.4s ease-in-out infinite;
}
.star-top50 {
  width: 26px; height: 26px;
  background: #f97316;
  font-size: 14px;
}
.star-top100 {
  width: 20px; height: 20px;
  background: #eab308;
  font-size: 11px;
}
@keyframes star-pulse {
  0%, 100% { box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.25), 0 2px 6px rgba(0, 0, 0, 0.5); }
  50% { box-shadow: 0 0 0 8px rgba(220, 38, 38, 0.10), 0 2px 8px rgba(0, 0, 0, 0.6); }
}
.circle-marker {
  width: 12px; height: 12px;
  border-radius: 50%;
  border: 2px solid white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

/* Quality cluster - color shows avg composite_score */
.quality-cluster {
  border-radius: 50%;
  border: 3px solid white;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 800;
}
.quality-cluster .cluster-count { font-size: 14px; line-height: 1; font-weight: 800; }
.quality-cluster .cluster-grade { font-size: 10px; line-height: 1; font-weight: 700; opacity: 0.92; margin-top: 2px; }

/* Popup */
.leaflet-popup-content { margin: 0 !important; min-width: 280px; }
.leaflet-popup-content-wrapper { padding: 0 !important; border-radius: 6px !important; overflow: hidden; }
.popup-card { font-family: inherit; }

.popup-header {
  background: linear-gradient(135deg, #1A365D 0%, #2563eb 100%);
  color: white;
  padding: 10px 14px 8px;
}
.popup-rank-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.popup-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 3px 9px;
  border-radius: 10px;
  letter-spacing: 0.04em;
}
.popup-badge.top20 { background: #dc2626; color: white; box-shadow: 0 0 0 2px rgba(255,255,255,0.4); }
.popup-badge.top50 { background: #f97316; color: white; }
.popup-badge.top100 { background: #eab308; color: white; }
.popup-badge.normal { background: rgba(255, 255, 255, 0.2); color: white; }
.popup-stars { font-size: 14px; letter-spacing: 1px; }
.popup-stars .filled { color: #fbbf24; }
.popup-stars .empty { color: rgba(255, 255, 255, 0.3); }
.popup-composite {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.85);
  margin-top: 2px;
}
.popup-composite strong { color: white; font-size: 14px; }

.popup-body { padding: 12px 14px; }
.popup-output {
  font-size: 28px;
  font-weight: 900;
  color: #0D6B3B;
  text-align: center;
  letter-spacing: -0.03em;
  line-height: 1;
}
.popup-output-unit {
  font-size: 14px;
  color: #6b7280;
  font-weight: 600;
  margin-left: 4px;
}
.popup-location {
  text-align: center;
  font-size: 13px;
  color: #4b5563;
  margin: 4px 0 12px;
  font-weight: 500;
}

.popup-section { margin-top: 10px; }
.popup-section-title {
  font-size: 10px;
  font-weight: 800;
  color: #6b7280;
  letter-spacing: 0.08em;
  margin-bottom: 6px;
  padding-bottom: 4px;
  border-bottom: 1px solid #e5e7eb;
}

.metric-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 4px 0;
  font-size: 11px;
}
.metric-bar-label {
  width: 58px;
  color: #4b5563;
  font-weight: 600;
}
.metric-bar-track {
  flex: 1;
  height: 7px;
  background: #f3f4f6;
  border-radius: 4px;
  overflow: hidden;
}
.metric-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s;
}
.metric-bar-fill.high { background: #34d399; }
.metric-bar-fill.mid { background: #f59e0b; }
.metric-bar-fill.low { background: #ef4444; }
.metric-bar-value {
  width: 38px;
  text-align: right;
  font-weight: 700;
  color: #1f2937;
}

.proscons { display: grid; grid-template-columns: 1fr; gap: 4px; margin-top: 6px; }
.pro, .con {
  font-size: 12px;
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 5px 8px;
  border-radius: 4px;
  line-height: 1.3;
}
.pro { background: #ecfdf5; color: #065f46; }
.con { background: #fef2f2; color: #991b1b; }
.pro::before { content: "✓"; font-weight: 800; flex-shrink: 0; }
.con::before { content: "✗"; font-weight: 800; flex-shrink: 0; }

.popup-meta {
  font-size: 11px;
  color: #6b7280;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid #e5e7eb;
  line-height: 1.5;
}
.popup-meta b { color: #1f2937; }

/* Economics section */
.econ-grid {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px 10px;
  font-size: 12px;
  margin: 4px 0;
}
.econ-key { color: #6b7280; font-weight: 600; }
.econ-value { text-align: right; color: #1f2937; font-weight: 600; }
.econ-highlight {
  margin-top: 6px;
  padding: 8px 10px;
  background: linear-gradient(135deg, #ecfdf5, #d1fae5);
  border-radius: 6px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}
.econ-headline {
  text-align: center;
}
.econ-headline-label {
  font-size: 10px;
  color: #047857;
  font-weight: 700;
  letter-spacing: 0.05em;
  margin-bottom: 2px;
}
.econ-headline-value {
  font-size: 18px;
  font-weight: 800;
  color: #064e3b;
  line-height: 1;
}
.econ-headline-unit {
  font-size: 11px;
  font-weight: 600;
  color: #047857;
  margin-left: 2px;
}
.econ-warn {
  background: linear-gradient(135deg, #fef2f2, #fee2e2) !important;
}
.econ-warn .econ-headline-label { color: #991b1b; }
.econ-warn .econ-headline-value { color: #7f1d1d; }
.econ-warn .econ-headline-unit { color: #991b1b; }
.econ-note {
  font-size: 10px;
  color: #6b7280;
  margin-top: 4px;
  text-align: center;
  line-height: 1.4;
}

/* 3-scenario table */
.scenario-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
  margin-top: 4px;
}
.scenario-table th, .scenario-table td {
  padding: 4px 6px;
  border: 1px solid #e5e7eb;
  text-align: right;
}
.scenario-table thead th {
  font-size: 10px;
  font-weight: 800;
  text-align: center;
  letter-spacing: 0.05em;
}
.scenario-table th.opt-h { background: #ecfdf5; color: #065f46; }
.scenario-table th.std-h { background: #dbeafe; color: #1e40af; }
.scenario-table th.rep-h { background: #fee2e2; color: #991b1b; }
.scenario-table tbody th {
  background: #f9fafb;
  text-align: left;
  font-size: 10.5px;
  color: #4b5563;
  font-weight: 600;
}
.scenario-table td {
  font-weight: 700;
  color: #1f2937;
}
.scenario-table td.std-col {
  background: #eff6ff;
  font-weight: 800;
}
.scenario-table td small {
  font-size: 9px;
  font-weight: 500;
  color: #9ca3af;
  margin-left: 2px;
}

.item-payback {
  background: #fef3c7;
  color: #92400e;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 10px;
}
.item-payback.good {
  background: #d1fae5;
  color: #065f46;
}
.item-payback.bad {
  background: #fecaca;
  color: #991b1b;
}

.popup-links {
  display: flex;
  gap: 6px;
  margin-top: 10px;
}
.popup-links a {
  flex: 1;
  text-align: center;
  font-size: 12px;
  font-weight: 600;
  padding: 7px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 4px;
  text-decoration: none;
  color: #1d4ed8;
  transition: background 0.1s;
}
.popup-links a:hover { background: #dbeafe; }

/* Layer control overrides */
.leaflet-control-layers { font-size: 12px; }

/* Bottom-left button container */
.map-bottom-left {
  position: absolute;
  bottom: 22px;
  left: 22px;
  z-index: 1000;
  display: flex;
  gap: 8px;
}
.map-bottom-left button {
  padding: 9px 16px;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 22px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  color: #1f2937;
  white-space: nowrap;
}
.map-bottom-left button:hover {
  background: #f9fafb;
  border-color: #2563eb;
  color: #2563eb;
}
#glossary-btn::before { content: "❓ "; }
#actions-btn::before { content: "📋 "; }
#actions-btn { background: #1A365D; color: white; border-color: #1A365D; }
#actions-btn:hover { background: #2563eb; color: white; border-color: #2563eb; }
#share-btn::before { content: "🔗 "; }

.update-tag {
  font-size: 10px;
  color: #9ca3af;
  margin-top: 4px;
}
.sheet-state-bar {
  display: none;
  gap: 4px;
  margin: 6px 0 4px;
}
.sheet-state-bar button {
  flex: 1;
  padding: 6px 4px;
  font-size: 11px;
  background: white;
  border: 1px solid #d1d5db;
  border-radius: 5px;
  cursor: pointer;
  font-weight: 700;
  color: #4b5563;
  transition: all 0.12s;
}
.sheet-state-bar button.active {
  background: #2563eb;
  color: white;
  border-color: #2563eb;
  box-shadow: 0 2px 6px rgba(37, 99, 235, 0.3);
}
.disclaimer-tag {
  background: #fef3c7;
  color: #92400e;
  padding: 1px 6px;
  border-radius: 3px;
  font-weight: 700;
}

.modal-shell {
  display: none;
  position: fixed;
  top: 0; left: 0;
  width: 100vw; height: 100vh;
  background: rgba(15, 23, 42, 0.55);
  z-index: 9999;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.modal-shell.open { display: flex; }
.glossary-card {
  width: 760px;
  max-width: 96vw;
  max-height: 88vh;
  background: white;
  border-radius: 10px;
  overflow: auto;
  padding: 0;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.35);
  position: relative;
}
.glossary-header {
  position: sticky;
  top: 0;
  z-index: 10;
  background: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 24px 12px;
  border-bottom: 2px solid #2563eb;
  margin-bottom: 14px;
}
.glossary-header h2 {
  font-size: 17px;
  font-weight: 800;
  color: #1A365D;
}
.glossary-close {
  background: #f3f4f6;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: #1f2937;
  padding: 0;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-weight: 700;
  transition: all 0.15s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}
.glossary-close:hover {
  background: #fee2e2;
  color: #dc2626;
}

.glossary-section {
  padding: 0 24px;
  margin-bottom: 16px;
}
.glossary-section:last-child { padding-bottom: 24px; }
.glossary-h3 {
  font-size: 13px;
  font-weight: 800;
  color: #1A365D;
  margin-bottom: 6px;
  padding-bottom: 3px;
  border-bottom: 1px solid #e5e7eb;
}
.glossary-card p {
  font-size: 12.5px;
  line-height: 1.65;
  color: #374151;
  margin-bottom: 4px;
}
.glossary-card ul {
  margin-left: 18px;
  font-size: 12.5px;
  line-height: 1.65;
  color: #374151;
}
.glossary-card table {
  width: 100%;
  font-size: 11.5px;
  border-collapse: collapse;
  margin: 6px 0;
}
.glossary-card td, .glossary-card th {
  padding: 5px 8px;
  border: 1px solid #e5e7eb;
  text-align: left;
  vertical-align: top;
}
.glossary-card th { background: #f3f4f6; font-weight: 700; }
.glossary-card .warn {
  background: #fef3c7;
  border-left: 4px solid #f59e0b;
  padding: 8px 12px;
  margin: 8px 0;
  font-size: 12px;
  border-radius: 0 4px 4px 0;
}
.glossary-card code {
  background: #f3f4f6;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 11.5px;
  font-family: 'Menlo', monospace;
  color: #1f2937;
}

/* ============================================
 * モバイル対応: Bottom Sheet レイアウト
 * ============================================ */
@media (max-width: 768px) {
  #app { flex-direction: column; }

  #sidebar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    width: 100%;
    min-width: 0;
    max-height: 92vh;
    border-right: none;
    border-top: 1px solid #d1d5db;
    border-radius: 18px 18px 0 0;
    z-index: 1500;
    transform: translateY(calc(100% - 130px));
    transition: transform 0.28s cubic-bezier(0.32, 0.72, 0, 1);
    box-shadow: 0 -8px 24px rgba(0, 0, 0, 0.18);
    background: white;
    padding-bottom: env(safe-area-inset-bottom);
  }
  #sidebar.sheet-mid { transform: translateY(50vh); }
  #sidebar.sheet-full { transform: translateY(8vh); }

  .sidebar-header {
    cursor: pointer;
    position: relative;
    padding-top: 16px;
    user-select: none;
  }
  .sidebar-header::before {
    content: '';
    display: block;
    width: 40px;
    height: 4px;
    background: #d1d5db;
    border-radius: 2px;
    margin: -10px auto 10px;
  }
  #sidebar.sheet-full .sidebar-header::before { background: #9ca3af; }

  .sidebar-header h1 { font-size: 12px; }
  .sheet-state-bar { display: flex; }

  /* マップは全画面 */
  #map-container { height: 100vh; width: 100%; }

  /* desktop左下のボタン群はモバイルでヘッダ最下部に移動 (JSでDOM移動) */
  .map-bottom-left {
    position: static !important;
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    padding: 8px 14px;
    border-bottom: 1px solid #f3f4f6;
    background: #f9fafb;
  }
  .map-bottom-left button {
    flex: 1 1 0;
    min-width: 0;
    padding: 7px 8px;
    font-size: 11px;
    white-space: nowrap;
  }

  /* 凡例非表示（場所食う） */
  #map-legend { display: none; }

  /* search-area-btn 縮小 */
  #search-area-btn {
    font-size: 12px;
    padding: 8px 14px;
    top: 10px;
  }

  /* リストアイテム余白縮小 */
  .list-item { padding: 10px 12px; }
  .list-item.top20 { border-left-width: 4px; padding-left: 8px; }
  .list-item.top50 { border-left-width: 4px; padding-left: 8px; }
  .list-item.top100 { border-left-width: 4px; padding-left: 8px; }

  /* glossary/actions モーダルもモバイル最適化 */
  .glossary-card {
    width: 100% !important;
    max-height: 90vh;
    padding: 16px 18px 22px;
    border-radius: 12px;
  }
  .modal-shell { padding: 8px; }

  /* ポップアップは画面の70%まで */
  .leaflet-popup-content { max-width: 86vw !important; }
}

/* Map legend (top-right corner) */
#map-legend {
  position: absolute;
  bottom: 22px;
  right: 22px;
  z-index: 999;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 11px;
  color: #374151;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
  line-height: 1.5;
}
#map-legend .legend-row {
  display: flex;
  align-items: center;
  gap: 6px;
}
#map-legend .legend-mark {
  display: inline-block;
  border-radius: 50%;
  border: 2px solid white;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
  flex-shrink: 0;
}
"""


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>小水力発電 候補地マップ</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css">
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css">
<style>
__CSS__
</style>
</head>
<body>
<div id="app">
  <aside id="sidebar">
    <div class="sidebar-header">
      <h1>小水力発電 候補地スクリーニング</h1>
      <div class="filter-bar">
        <select id="band-filter">
          <option value="all">全出力帯</option>
          <option value="50-100" selected>50-100kW（最優先）</option>
          <option value="100-150">100-150kW（次点）</option>
          <option value="50-150">50-150kW（合計）</option>
          <option value="150-500">150kW以上</option>
        </select>
        <select id="sort-by">
          <option value="composite">合成スコア順</option>
          <option value="payback">回収期間順</option>
          <option value="irr">利回り(IRR)順</option>
          <option value="cost">kW単価順</option>
          <option value="output">出力順</option>
        </select>
      </div>
      <div class="result-count" id="result-count"></div>
      <div class="sheet-state-bar">
        <button data-state="peek" type="button">▼ 縮小</button>
        <button data-state="mid" type="button">▌ 標準</button>
        <button data-state="full" type="button">▲ 全画面</button>
      </div>
      <div class="update-tag">最終更新: __UPDATED_AT__ ・<span class="disclaimer-tag">机上一次スクリーニング</span></div>
    </div>
    <div id="results"></div>
  </aside>
  <main id="map-container">
    <button id="search-area-btn">このエリアで再検索</button>
    <div id="map"></div>
    <div class="map-bottom-left">
      <button id="glossary-btn">用語・前提解説</button>
      <button id="actions-btn">絞り込み後アクション</button>
      <button id="share-btn">URL共有</button>
    </div>
    <div id="map-legend">
      <div class="legend-row"><span class="legend-mark" style="width:18px;height:18px;background:#dc2626"></span><b>TOP 20</b> (大赤・脈動)</div>
      <div class="legend-row"><span class="legend-mark" style="width:14px;height:14px;background:#f97316"></span>TOP 50 (中橙)</div>
      <div class="legend-row"><span class="legend-mark" style="width:11px;height:11px;background:#eab308"></span>TOP 100 (小黄)</div>
      <div class="legend-row" style="margin-top:4px;border-top:1px solid #e5e7eb;padding-top:4px"><span class="legend-mark" style="width:14px;height:14px;background:#10b981"></span>クラスタ A: 平均≥0.7</div>
      <div class="legend-row"><span class="legend-mark" style="width:14px;height:14px;background:#3b82f6"></span>クラスタ B: 0.5-0.7</div>
      <div class="legend-row"><span class="legend-mark" style="width:14px;height:14px;background:#f59e0b"></span>クラスタ C: 0.3-0.5</div>
      <div class="legend-row"><span class="legend-mark" style="width:14px;height:14px;background:#9ca3af"></span>クラスタ D: &lt;0.3</div>
    </div>
  </main>
</div>

<div id="glossary-modal" class="modal-shell" onclick="if(event.target===this)closeGlossary()">
  <div class="glossary-card" id="glossary-content"></div>
</div>
<div id="actions-modal" class="modal-shell" onclick="if(event.target===this)closeActions()">
  <div class="glossary-card" id="actions-content"></div>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
<script>
const ALL_CANDIDATES = __CANDIDATES__;
const PROTECTED_AREAS = __PROTECTED__;
const CENTER = __CENTER__;
const TOTAL = __TOTAL__;
__JS__
</script>
</body>
</html>
"""


_JS = """
const map = L.map('map', { preferCanvas: true }).setView(CENTER, 8);

const osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap', maxZoom: 19
}).addTo(map);
const gsiLayer = L.tileLayer('https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png', {
  attribution: '国土地理院', maxZoom: 18
});
const photoLayer = L.tileLayer('https://cyberjapandata.gsi.go.jp/xyz/seamlessphoto/{z}/{x}/{y}.jpg', {
  attribution: '国土地理院', maxZoom: 18
});
L.control.layers({
  'OpenStreetMap': osmLayer,
  '国土地理院 標準': gsiLayer,
  '国土地理院 航空': photoLayer
}, {}, { collapsed: true }).addTo(map);

if (PROTECTED_AREAS && PROTECTED_AREAS.features && PROTECTED_AREAS.features.length > 0) {
  L.geoJSON(PROTECTED_AREAS, {
    style: { fillColor: '#ef4444', color: '#c53030', weight: 1, fillOpacity: 0.12 },
    onEachFeature: (f, layer) => {
      const name = (f.properties && f.properties.name) || '規制エリア';
      layer.bindTooltip(name);
    }
  }).addTo(map);
}

function makeIcon(c) {
  if (c.rank && c.rank <= 20) {
    return L.divIcon({ html: '<div class="star-marker star-top20">★</div>', className: '', iconSize: [32, 32], iconAnchor: [16, 16] });
  }
  if (c.rank && c.rank <= 50) {
    return L.divIcon({ html: '<div class="star-marker star-top50">★</div>', className: '', iconSize: [26, 26], iconAnchor: [13, 13] });
  }
  if (c.rank && c.rank <= 100) {
    return L.divIcon({ html: '<div class="star-marker star-top100">★</div>', className: '', iconSize: [20, 20], iconAnchor: [10, 10] });
  }
  let color = '#9ca3af';
  if (c.output_kw >= 50 && c.output_kw < 100) color = '#34d399';
  else if (c.output_kw >= 100 && c.output_kw < 150) color = '#4a7dff';
  else if (c.output_kw >= 150) color = '#a855f7';
  return L.divIcon({ html: '<div class="circle-marker" style="background:' + color + '"></div>', className: '', iconSize: [12, 12], iconAnchor: [6, 6] });
}

function makeQualityClusterIcon(cluster) {
  const markers = cluster.getAllChildMarkers();
  let sumScore = 0, count = 0;
  markers.forEach(m => {
    if (m.candidate) { sumScore += (m.candidate.composite || 0); count++; }
  });
  const avg = count > 0 ? sumScore / count : 0;
  const childCount = cluster.getChildCount();

  let bg = '#9ca3af', label = 'D';
  if (avg >= 0.7) { bg = '#10b981'; label = 'A'; }
  else if (avg >= 0.5) { bg = '#3b82f6'; label = 'B'; }
  else if (avg >= 0.3) { bg = '#f59e0b'; label = 'C'; }

  const size = Math.round(Math.min(60, 42 + Math.log10(Math.max(2, childCount)) * 7));
  const tooltip = '平均スコア ' + avg.toFixed(2) + ' / ' + childCount + '件';
  return L.divIcon({
    html: '<div class="quality-cluster" title="' + tooltip + '" style="background:' + bg + ';width:' + size + 'px;height:' + size + 'px">' +
      '<span class="cluster-count">' + childCount + '</span>' +
      '<span class="cluster-grade">' + label + '</span>' +
      '</div>',
    iconSize: [size, size],
    className: 'quality-cluster-wrapper'
  });
}

function classFor(score) {
  if (score >= 0.7) return 'high';
  if (score >= 0.4) return 'mid';
  return 'low';
}

function fmtMan(jpy) {
  if (!jpy || jpy === 0) return '-';
  return (jpy / 10000).toLocaleString(undefined, { maximumFractionDigits: 0 });
}

function fmtNum(v, digits) {
  if (v === null || v === undefined) return '-';
  return v.toFixed(digits);
}

function economicsSection(c) {
  if (!c.scenarios || !c.scenarios.standard) return '';
  const std = c.scenarios.standard;
  if (!std.annual_revenue_jpy || std.annual_revenue_jpy <= 0) return '';

  const opt = c.scenarios.optimistic;
  const repos = c.scenarios.repos;

  function row(label, opt_v, std_v, repos_v, suffix) {
    return '<tr>' +
      '<th>' + label + '</th>' +
      '<td>' + opt_v + suffix + '</td>' +
      '<td class="std-col">' + std_v + suffix + '</td>' +
      '<td>' + repos_v + suffix + '</td>' +
      '</tr>';
  }

  const weirNote = c.near_weir
    ? '<span style="color:#065f46;font-weight:700">✓既存堰200m以内</span>＝標準シナリオを15%減で試算'
    : '※ 楽観=既存堰活用想定 / 標準=NEF実例平均 / REPOS=環境省試算';

  const irrPct = (v) => v === null || v === undefined ? '-' : (v * 100).toFixed(1);

  return '<div class="popup-section">' +
    '<div class="popup-section-title">経済性試算（3シナリオ）</div>' +
    '<table class="scenario-table">' +
      '<thead><tr>' +
      '<th></th>' +
      '<th class="opt-h">楽観</th>' +
      '<th class="std-h">標準</th>' +
      '<th class="rep-h">REPOS悲観</th>' +
      '</tr></thead>' +
      '<tbody>' +
      row('kW単価',
        fmtNum(opt.cost_per_kw, 1),
        fmtNum(std.cost_per_kw, 1),
        fmtNum(repos.cost_per_kw, 1),
        '<small>百万/kW</small>') +
      row('建設費',
        fmtNum(opt.cost_mjpy, 0),
        fmtNum(std.cost_mjpy, 0),
        fmtNum(repos.cost_mjpy, 0),
        '<small>百万円</small>') +
      row('単純回収',
        fmtNum(opt.payback_years, 1),
        fmtNum(std.payback_years, 1),
        fmtNum(repos.payback_years, 1),
        '<small>年</small>') +
      row('想定IRR',
        irrPct(opt.irr),
        irrPct(std.irr),
        irrPct(repos.irr),
        '<small>%</small>') +
      '</tbody>' +
    '</table>' +
    '<div class="econ-grid" style="margin-top:6px">' +
      '<div class="econ-key">売電収入(/年)</div><div class="econ-value">' + fmtMan(std.annual_revenue_jpy) + ' 万円</div>' +
      '<div class="econ-key">O&amp;M費(/年)</div><div class="econ-value">- ' + fmtMan(std.annual_om_jpy) + ' 万円</div>' +
      '<div class="econ-key">年間CF(標準)</div><div class="econ-value">' + fmtMan(std.annual_cf_jpy) + ' 万円</div>' +
    '</div>' +
    '<div class="econ-note">' + weirNote + '</div>' +
    '</div>';
}

function bar(label, score, valueText) {
  const pct = Math.max(0, Math.min(100, Math.round(score * 100)));
  return '<div class="metric-bar"><div class="metric-bar-label">' + label +
    '</div><div class="metric-bar-track"><div class="metric-bar-fill ' + classFor(score) +
    '" style="width:' + pct + '%"></div></div><div class="metric-bar-value">' + valueText + '</div></div>';
}

function makePopupHTML(c) {
  const filled = Math.max(0, Math.min(5, Math.round(c.composite * 5)));
  const cf = c.output_kw > 0 ? c.annual_kwh / (c.output_kw * 8760) : 0;

  let badge = '';
  if (c.rank && c.rank <= 20) badge = '<span class="popup-badge top20">★TOP 20  #' + c.rank + '</span>';
  else if (c.rank && c.rank <= 50) badge = '<span class="popup-badge top50">TOP 50  #' + c.rank + '</span>';
  else if (c.rank && c.rank <= 100) badge = '<span class="popup-badge top100">TOP 100  #' + c.rank + '</span>';
  else if (c.rank) badge = '<span class="popup-badge normal">#' + c.rank + '</span>';

  const pros = [];
  const cons = [];
  if (c.output_kw >= 50 && c.output_kw < 100) pros.push('出力 ' + c.output_kw.toFixed(0) + 'kW（最優先 50-100kW帯）');
  else if (c.output_kw >= 100 && c.output_kw < 150) pros.push('出力 ' + c.output_kw.toFixed(0) + 'kW（次点 100-150kW帯）');
  else if (c.output_kw < 30) cons.push('出力 ' + c.output_kw.toFixed(0) + 'kW（小さすぎる）');
  else if (c.output_kw >= 300) cons.push('出力 ' + c.output_kw.toFixed(0) + 'kW（対象帯から大きく外れる）');

  if (c.cost_per_kw > 0 && c.cost_per_kw <= 5) pros.push('kW単価 ' + c.cost_per_kw.toFixed(1) + '百万円/kW（コスト最優秀）');
  else if (c.cost_per_kw > 0 && c.cost_per_kw <= 10) pros.push('kW単価 ' + c.cost_per_kw.toFixed(1) + '百万円/kW（許容範囲）');
  else if (c.cost_per_kw > 0) cons.push('kW単価 ' + c.cost_per_kw.toFixed(1) + '百万円/kW（割高）');

  if (cf >= 0.5) pros.push('設備利用率 ' + (cf * 100).toFixed(0) + '%（高稼働）');
  else if (cf >= 0.3) pros.push('設備利用率 ' + (cf * 100).toFixed(0) + '%（標準）');
  else if (cf > 0) cons.push('設備利用率 ' + (cf * 100).toFixed(0) + '%（低稼働）');

  if (c.near_weir) pros.push('既存堰200m以内 → 構造物再利用の可能性');
  else cons.push('既存堰なし → +0.15加点未獲得');

  if (c.in_park) cons.push('規制エリア内（実質除外）');

  return '<div class="popup-card">' +
    '<div class="popup-header"><div class="popup-rank-row">' + badge +
    '<span class="popup-stars"><span class="filled">' + '★'.repeat(filled) + '</span><span class="empty">' + '★'.repeat(5 - filled) + '</span></span>' +
    '</div><div class="popup-composite">合成スコア: <strong>' + c.composite.toFixed(3) + '</strong></div></div>' +

    '<div class="popup-body">' +
    '<div class="popup-output">' + c.output_kw.toFixed(1) + '<span class="popup-output-unit">kW</span></div>' +
    '<div class="popup-location">' + c.prefecture + ' ' + c.municipality + '</div>' +

    economicsSection(c) +

    '<div class="popup-section"><div class="popup-section-title">スコア内訳</div>' +
    bar('出力帯', c.band_score, c.band_score.toFixed(2)) +
    bar('コスト', c.cost_score, c.cost_score.toFixed(2)) +
    bar('利用率', c.cf_score, c.cf_score.toFixed(2)) +
    '</div>' +

    '<div class="popup-section"><div class="popup-section-title">良い点 / 弱点</div><div class="proscons">' +
    pros.map(p => '<div class="pro">' + p + '</div>').join('') +
    cons.map(c => '<div class="con">' + c + '</div>').join('') +
    '</div></div>' +

    '<div class="popup-meta">' +
    '年間発電量 <b>' + c.annual_kwh.toLocaleString(undefined, { maximumFractionDigits: 0 }) + '</b> kWh<br>' +
    '建設費 <b>' + c.cost_mjpy.toLocaleString(undefined, { maximumFractionDigits: 0 }) + '</b> 百万円<br>' +
    '<span style="color:#9ca3af">LINKID: ' + c.linkid + ' | (' + c.lat.toFixed(5) + ', ' + c.lon.toFixed(5) + ')</span>' +
    '</div>' +

    '<div class="popup-links">' +
    '<a href="https://www.google.com/maps?q=' + c.lat + ',' + c.lon + '" target="_blank">📍 Google Maps</a>' +
    '<a href="https://maps.gsi.go.jp/#16/' + c.lat + '/' + c.lon + '/" target="_blank">🗾 地理院地図</a>' +
    '</div>' +

    '</div></div>';
}

map.createPane('starsPane');
map.getPane('starsPane').style.zIndex = 650;

const MARKER_BY_RANK = {};
const cluster = L.markerClusterGroup({
  maxClusterRadius: 50,
  spiderfyOnMaxZoom: true,
  chunkedLoading: true,
  iconCreateFunction: makeQualityClusterIcon
});
const starsLayer = L.featureGroup();

const isMobileNow = () => window.innerWidth <= 768;

ALL_CANDIDATES.forEach(c => {
  const isTop = c.rank && c.rank <= 100;
  const m = L.marker([c.lat, c.lon], {
    icon: makeIcon(c),
    pane: isTop ? 'starsPane' : 'markerPane'
  });
  m.bindPopup(() => makePopupHTML(c), {
    maxWidth: 380,
    maxHeight: isMobileNow() ? 380 : 600,
    autoPan: true,
    autoPanPaddingTopLeft: L.point(10, 60),
    autoPanPaddingBottomRight: L.point(10, isMobileNow() ? 160 : 30),
  });
  m.on('click', () => {
    if (isMobileNow()) setSheetState('peek');
  });
  m.candidate = c;
  if (isTop) {
    starsLayer.addLayer(m);
  } else {
    cluster.addLayer(m);
  }
  if (c.rank) MARKER_BY_RANK[c.rank] = m;
});
map.addLayer(cluster);
map.addLayer(starsLayer);

function applyBand(arr, band) {
  if (band === '50-100') return arr.filter(c => c.output_kw >= 50 && c.output_kw < 100);
  if (band === '100-150') return arr.filter(c => c.output_kw >= 100 && c.output_kw < 150);
  if (band === '50-150') return arr.filter(c => c.output_kw >= 50 && c.output_kw < 150);
  if (band === '150-500') return arr.filter(c => c.output_kw >= 150);
  return arr;
}
function applySort(arr, sortBy) {
  const a = arr.slice();
  if (sortBy === 'composite') a.sort((x, y) => y.composite - x.composite);
  else if (sortBy === 'cost') a.sort((x, y) => (x.cost_per_kw || Infinity) - (y.cost_per_kw || Infinity));
  else if (sortBy === 'output') a.sort((x, y) => y.output_kw - x.output_kw);
  else if (sortBy === 'payback') a.sort((x, y) => (x.payback_years === null || x.payback_years === undefined ? Infinity : x.payback_years) - (y.payback_years === null || y.payback_years === undefined ? Infinity : y.payback_years));
  else if (sortBy === 'irr') a.sort((x, y) => (y.irr || -Infinity) - (x.irr || -Infinity));
  return a;
}

function paybackTag(c) {
  const p = c.payback_years;
  if (p === null || p === undefined) return '<span class="item-payback bad">回収不能</span>';
  let cls = 'item-payback';
  if (p < 12) cls += ' good';
  else if (p > 25) cls += ' bad';
  return '<span class="' + cls + '">回収' + p.toFixed(1) + '年</span>';
}

function makeListItem(c) {
  const item = document.createElement('div');
  item.className = 'list-item';
  if (c.rank && c.rank <= 20) item.classList.add('top20');
  else if (c.rank && c.rank <= 50) item.classList.add('top50');
  else if (c.rank && c.rank <= 100) item.classList.add('top100');
  item.dataset.rank = c.rank || '';

  const filled = Math.max(0, Math.min(5, Math.round(c.composite * 5)));
  const cf = c.output_kw > 0 ? c.annual_kwh / (c.output_kw * 8760) : 0;

  let rankBadgeText = '';
  if (c.rank && c.rank <= 20) rankBadgeText = 'TOP20';
  else if (c.rank && c.rank <= 50) rankBadgeText = 'TOP50';
  else if (c.rank && c.rank <= 100) rankBadgeText = 'TOP100';

  const stdPayback = c.scenarios && c.scenarios.standard ? c.scenarios.standard.payback_years : c.payback_years;

  item.innerHTML =
    '<div class="list-item-header">' +
      '<div class="list-rank-side">' +
        '<span class="list-rank-num">#' + (c.rank || '-') + '</span>' +
        (rankBadgeText ? '<span class="list-rank-badge">' + rankBadgeText + '</span>' : '') +
      '</div>' +
      '<div class="list-score-side">' +
        '<span class="list-score-num">' + c.composite.toFixed(2) + '</span>' +
        '<span class="list-score-stars">' + '★'.repeat(filled) + '<span class="empty">' + '★'.repeat(5 - filled) + '</span></span>' +
      '</div>' +
    '</div>' +
    '<div class="list-location"><strong>' + c.prefecture + '</strong> ' + c.municipality + '</div>' +
    '<div class="list-output-line"><span class="list-output-kw">' + c.output_kw.toFixed(1) + ' kW</span>' +
      ' / 年間 ' + (c.annual_kwh / 10000).toFixed(0) + '万kWh</div>' +
    '<div class="list-meta">' +
      '<span class="list-meta-tag">標準回収 <strong>' + (stdPayback === null || stdPayback === undefined ? 'N/A' : stdPayback.toFixed(1) + '年') + '</strong></span>' +
      '<span class="list-meta-tag">利用率<strong>' + (cf * 100).toFixed(0) + '%</strong></span>' +
      (c.near_weir ? '<span class="item-weir-tag">堰活用可</span>' : '') +
    '</div>';

  item.onclick = () => {
    document.querySelectorAll('.list-item.active').forEach(el => el.classList.remove('active'));
    item.classList.add('active');
    if (window.innerWidth <= 768) {
      setSheetState('peek');
    }
    map.flyTo([c.lat, c.lon], 14, { duration: 0.5 });
    setTimeout(() => {
      const m = MARKER_BY_RANK[c.rank];
      if (m) m.openPopup();
    }, 600);
  };
  return item;
}

function renderSidebar(list) {
  const root = document.getElementById('results');
  root.innerHTML = '';
  const limit = 200;
  document.getElementById('result-count').innerHTML =
    '<strong>' + list.length.toLocaleString() + '</strong>件 ' +
    (list.length > limit ? '（上位' + limit + '件を表示）' : '');
  list.slice(0, limit).forEach(c => root.appendChild(makeListItem(c)));
}

function applyFilter(useBoundsFilter = false) {
  const band = document.getElementById('band-filter').value;
  const sortBy = document.getElementById('sort-by').value;
  let list = ALL_CANDIDATES;
  if (useBoundsFilter) {
    const bounds = map.getBounds();
    list = list.filter(c => bounds.contains([c.lat, c.lon]));
  }
  list = applyBand(list, band);
  list = applySort(list, sortBy);
  renderSidebar(list);
}

document.getElementById('search-area-btn').onclick = () => applyFilter(true);
document.getElementById('band-filter').onchange = () => { applyFilter(false); updateUrlHash(); };
document.getElementById('sort-by').onchange = () => { applyFilter(false); updateUrlHash(); };

// URL hash 同期: #lat,lon,zoom/band/sort
function updateUrlHash() {
  const c = map.getCenter();
  const z = map.getZoom();
  const band = document.getElementById('band-filter').value;
  const sort = document.getElementById('sort-by').value;
  const newHash = '#' + c.lat.toFixed(4) + ',' + c.lng.toFixed(4) + ',' + z + '/' + band + '/' + sort;
  if (window.location.hash !== newHash) {
    history.replaceState(null, '', newHash);
  }
}
function applyUrlHash() {
  const hash = window.location.hash.slice(1);
  if (!hash) return;
  const parts = hash.split('/');
  const view = parts[0];
  if (view) {
    const v = view.split(',').map(parseFloat);
    if (v.length === 3 && v.every(n => !isNaN(n))) {
      map.setView([v[0], v[1]], v[2]);
    }
  }
  if (parts[1]) {
    const sel = document.getElementById('band-filter');
    if ([...sel.options].some(o => o.value === parts[1])) sel.value = parts[1];
  }
  if (parts[2]) {
    const sel = document.getElementById('sort-by');
    if ([...sel.options].some(o => o.value === parts[2])) sel.value = parts[2];
  }
}
map.on('moveend', updateUrlHash);
map.on('zoomend', updateUrlHash);
applyUrlHash();

// ============================================
// モバイル: Bottom Sheet 状態管理 + DOM再配置
// ============================================
const sheet = document.getElementById('sidebar');
let sheetState = 'peek';

function setSheetState(state) {
  sheet.classList.remove('sheet-peek', 'sheet-mid', 'sheet-full');
  if (state !== 'peek') sheet.classList.add('sheet-' + state);
  sheetState = state;
  document.querySelectorAll('.sheet-state-bar button').forEach(b => {
    b.classList.toggle('active', b.dataset.state === state);
  });
}

document.querySelectorAll('.sheet-state-bar button').forEach(btn => {
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    setSheetState(btn.dataset.state);
  });
});

function cycleSheetState() {
  if (sheetState === 'peek') setSheetState('mid');
  else if (sheetState === 'mid') setSheetState('full');
  else setSheetState('peek');
}

// Tap header to cycle
document.querySelector('.sidebar-header').addEventListener('click', (e) => {
  if (window.innerWidth > 768) return;
  if (e.target.closest('button') || e.target.closest('select') || e.target.closest('a')) return;
  cycleSheetState();
});

// DOM再配置: モバイルでは map-bottom-left を sidebar-header に移動
function reflowForViewport() {
  const buttons = document.querySelector('.map-bottom-left');
  const sidebarHeader = document.querySelector('.sidebar-header');
  const mapContainer = document.querySelector('#map-container');
  if (!buttons || !sidebarHeader || !mapContainer) return;

  if (window.innerWidth <= 768) {
    if (!sidebarHeader.contains(buttons)) sidebarHeader.appendChild(buttons);
    if (!sheet.classList.contains('sheet-mid') && !sheet.classList.contains('sheet-full')) {
      setSheetState('peek');
    }
  } else {
    if (!mapContainer.contains(buttons)) {
      // map-legend の前に挿入してDOM順を維持
      const legend = document.getElementById('map-legend');
      if (legend) mapContainer.insertBefore(buttons, legend);
      else mapContainer.appendChild(buttons);
    }
    sheet.classList.remove('sheet-peek', 'sheet-mid', 'sheet-full');
  }
}
reflowForViewport();
window.addEventListener('resize', reflowForViewport);

// タッチドラッグでシート操作（簡易版）
let dragStartY = null, dragStartState = null;
const header = document.querySelector('.sidebar-header');
header.addEventListener('touchstart', (e) => {
  if (window.innerWidth > 768) return;
  dragStartY = e.touches[0].clientY;
  dragStartState = sheetState;
});
header.addEventListener('touchend', (e) => {
  if (window.innerWidth > 768 || dragStartY === null) return;
  const endY = e.changedTouches[0].clientY;
  const dy = endY - dragStartY;
  if (Math.abs(dy) < 30) { dragStartY = null; return; }  // tapで処理
  // 上スワイプ(dy<0): 拡大
  if (dy < -40) {
    if (dragStartState === 'peek') setSheetState('mid');
    else if (dragStartState === 'mid') setSheetState('full');
  } else if (dy > 40) {
    if (dragStartState === 'full') setSheetState('mid');
    else if (dragStartState === 'mid') setSheetState('peek');
  }
  dragStartY = null;
  e.preventDefault();
});

// 共有URLボタン
document.getElementById('share-btn').addEventListener('click', () => {
  const btn = document.getElementById('share-btn');
  const orig = btn.innerHTML;
  navigator.clipboard.writeText(window.location.href).then(() => {
    btn.innerHTML = '✅ コピー完了';
    btn.disabled = true;
    setTimeout(() => { btn.innerHTML = orig; btn.disabled = false; }, 2000);
  }).catch(() => {
    btn.innerHTML = '⚠️ コピー失敗';
    setTimeout(() => { btn.innerHTML = orig; }, 2000);
  });
});

const GLOSSARY_HTML = `
<div class="glossary-header">
  <h2>用語・前提解説</h2>
  <button class="glossary-close" onclick="closeGlossary()">×</button>
</div>

<div class="glossary-section">
  <div class="glossary-h3">📊 データソース</div>
  <ul>
    <li><b>環境省REPOS R4</b>: 全国28,283件の小水力ポテンシャル（出力kW・年間kWh・建設費）</li>
    <li><b>OpenStreetMap (Overpass API)</b>: 既存堰（waterway=weir）・規制エリア（boundary=national_park）</li>
    <li><b>国土地理院 標高API</b>: 任意座標の標高（拡張機能で利用）</li>
  </ul>
</div>

<div class="glossary-section">
  <div class="glossary-h3">🏆 ランキング（TOP★）</div>
  <table>
    <tr><th>段階</th><th>表示</th><th>意味</th></tr>
    <tr><td>TOP 20</td><td>大★ 深紅 (脈動)</td><td>合成スコア最上位の絶対候補</td></tr>
    <tr><td>TOP 50</td><td>中★ 橙</td><td>事業性が高く現地視察推奨</td></tr>
    <tr><td>TOP 100</td><td>小★ 黄</td><td>有望候補プール</td></tr>
  </table>
  <p>TOP100の★は<b>クラスタリングせず常に表示</b>（密集地でも見える）。</p>
</div>

<div class="glossary-section">
  <div class="glossary-h3">🎯 合成スコア (composite_score)</div>
  <p><code>合成 = 出力帯×0.5 + コスト×0.3 + 利用率×0.2 + 堰加点(+0.15)</code></p>
  <p>規制エリア内なら 0（除外）。</p>
  <table>
    <tr><th>サブスコア</th><th>計算</th><th>意味</th></tr>
    <tr><td>出力帯</td><td>50-100kW=1.0 / 100-150kW=0.7 / 30-50/150-300=0.4-0.5</td><td>用途優先度（小水力の最適規模）</td></tr>
    <tr><td>コスト効率</td><td>5百万円/kW以下で1.0、線形低下</td><td>建設費の妥当性</td></tr>
    <tr><td>設備利用率</td><td>50%以上で1.0、線形低下</td><td>稼働の安定性</td></tr>
    <tr><td>堰加点</td><td>OSM堰200m以内で +0.15</td><td>既存インフラ流用の可能性</td></tr>
  </table>
</div>

<div class="glossary-section">
  <div class="glossary-h3">💰 経済性（3シナリオ）</div>
  <p>建設費の幅が大きいため、業界実例から3段階で試算する。</p>
  <table>
    <tr><th>シナリオ</th><th>kW単価</th><th>適用条件</th></tr>
    <tr><td><b style="color:#065f46">楽観</b></td><td>1.5百万/kW</td><td>既存堰活用、地形条件良好</td></tr>
    <tr><td><b style="color:#1e40af">標準</b></td><td>2.5百万/kW (堰近接で-15%)</td><td>NEF実例平均（中央値174万/kW）</td></tr>
    <tr><td><b style="color:#991b1b">REPOS悲観</b></td><td>4-5百万/kW</td><td>環境省REPOSのCONST_COST（新設グリーンフィールド）</td></tr>
  </table>
  <div class="warn"><b>重要:</b> REPOSは「保守的な悲観値」で、実例平均（民間1.35百万/kW・公営含み3.54百万/kW）の3倍程度。100kW＝1億円想定は楽観シナリオに合致。</div>
</div>

<div class="glossary-section">
  <div class="glossary-h3">⚡ FIT制度</div>
  <ul>
    <li>200kW未満: <b>34円/kWh</b> × 20年</li>
    <li>200-1000kW: 29円/kWh × 20年</li>
    <li>1000-5000kW: 27円/kWh × 20年</li>
  </ul>
  <p>FIT期間後10年は売電単価実質半減と仮定（市場価格相場）。</p>
</div>

<div class="glossary-section">
  <div class="glossary-h3">🔧 ランニングコスト（O&M）</div>
  <p><code>年間O&M = 建設費 × 2%</code>（業界rule of thumb）</p>
  <p>含むもの：保守点検・設備更新引当・水利権・固定資産税・人件費</p>
</div>

<div class="glossary-section">
  <div class="glossary-h3">📈 単純回収期間 / IRR</div>
  <p><b>単純回収</b> = 建設費 / (売電収入 - O&M)</p>
  <p><b>IRR</b> = FIT 20年 + post-FIT 10年（売電単価0.5倍）の現在価値ゼロとなる年率</p>
  <div class="warn">税効果・補助金・建中金利は未考慮。詳細事業計画では別途織込み必要。</div>
</div>

<div class="glossary-section">
  <div class="glossary-h3">🗺️ クラスタの色（A/B/C/D）</div>
  <table>
    <tr><th>段階</th><th>平均合成スコア</th><th>意味</th></tr>
    <tr><td><b style="color:#065f46">A 緑</b></td><td>≥ 0.7</td><td>そのエリアは候補が多くかつ有望</td></tr>
    <tr><td><b style="color:#1e40af">B 青</b></td><td>0.5-0.7</td><td>そこそこ有望</td></tr>
    <tr><td><b style="color:#92400e">C 橙</b></td><td>0.3-0.5</td><td>普通</td></tr>
    <tr><td><b style="color:#374151">D 灰</b></td><td>< 0.3</td><td>有望度低</td></tr>
  </table>
  <p>密集地（数字大）かつA緑のクラスタ＝<b>フォーカスすべきエリア</b>。</p>
</div>

<div class="glossary-section">
  <div class="glossary-h3">🚫 規制エリア</div>
  <p>OSMの<code>boundary=national_park</code>等。実際の保安林・自然公園・水利権規制は別途確認必須。</p>
  <div class="warn">OSMの規制エリアカバレッジは限定的。投資判断時には国土数値情報や自治体GIS必読。</div>
</div>

<div class="glossary-section">
  <div class="glossary-h3">⚠️ 試算の限界</div>
  <ul>
    <li>建設費は地点固有条件（アクセス・水利権・系統工事費）で大きく変動</li>
    <li>水利権交渉・地元調整・環境アセスは机上では試算不能</li>
    <li>本マップは<b>一次スクリーニング</b>用途。事業性精査は専門業者の現地調査が必須</li>
  </ul>
</div>
`;

const ACTIONS_HTML = `
<div class="glossary-header">
  <h2>絞り込み後の意思決定アクションガイド</h2>
  <button class="glossary-close" onclick="closeActions()">×</button>
</div>

<div class="glossary-section">
  <div class="glossary-h3">📍 全体フロー（3〜12ヶ月）</div>
  <p>本アプリ → Phase 2 机上精査 → Phase 3 現地視察 → Phase 4 ヒアリング → Phase 5 事業性精査 → Phase 6 意思決定 → Phase 7 事業開始</p>
</div>

<div class="glossary-section">
  <div class="glossary-h3">Phase 2: 机上精査（2〜4週） — TOP20を5〜10地点に絞込</div>
  <table>
    <tr><th>チェック項目</th><th>確認先</th><th>落とす基準</th></tr>
    <tr><td>水利権の競合</td><td>都道府県河川課</td><td>既存水利権が密集 → 取得困難</td></tr>
    <tr><td>系統連系空き容量</td><td>中部電力PG等</td><td>「空きゼロ」エリア → 接続不可</td></tr>
    <tr><td>規制エリア（精緻）</td><td>国土数値情報</td><td>国立公園特別保護地区 → ほぼ不可</td></tr>
    <tr><td>慣行水利権</td><td>農業用水組合・漁協</td><td>灌漑期に流量を渡す必要</td></tr>
    <tr><td>流況詳細</td><td>国交省 水文水質DB</td><td>渇水流量が想定の半分以下</td></tr>
    <tr><td>土地所有</td><td>法務局・自治体</td><td>不在地主多数 → 用地交渉困難</td></tr>
    <tr><td>アクセス道路</td><td>地形図+Google Earth</td><td>4m未満 → 工事車両不可</td></tr>
    <tr><td>既設施設活用</td><td>砂防事務所</td><td>既存堰活用可なら<b>楽観シナリオ適用</b></td></tr>
  </table>
</div>

<div class="glossary-section">
  <div class="glossary-h3">Phase 3: 現地視察（1〜2週） — 3〜5地点に絞込</div>
  <p><b>持ち物:</b> 候補座標(GPS)・地形図・流況データ・レーザー距離計・カメラ・沢登り装備・入山届</p>
  <table>
    <tr><th>確認項目</th><th>方法</th><th>NG基準</th></tr>
    <tr><td>落差</td><td>GPS高度＋距離計</td><td>REPOS値と±20%超ズレ</td></tr>
    <tr><td>河床状況</td><td>目視・撮影</td><td>土砂・倒木で導水路ルート困難</td></tr>
    <tr><td>道路幅員</td><td>巻尺</td><td>4m未満</td></tr>
    <tr><td>周辺住宅</td><td>集落地図</td><td>200m以内 → 騒音苦情リスク</td></tr>
    <tr><td>系統連系電柱</td><td>配電図照合</td><td>1km超 → 工事費1000万円超</td></tr>
    <tr><td>既存堰の構造</td><td>撮影・寸法</td><td>劣化・所有者不明 → 流用不可</td></tr>
    <tr><td>渓流環境</td><td>水生生物・植生</td><td>希少種 → 環境アセス必要</td></tr>
  </table>
</div>

<div class="glossary-section">
  <div class="glossary-h3">Phase 4: ヒアリング（1〜3ヶ月） — 1〜2地点に絞込</div>
  <div class="glossary-h3" style="font-size:12px;color:#374151;margin-top:6px">段階1: 制度系（事業可否を決める）</div>
  <table>
    <tr><th>相手</th><th>聞くこと</th></tr>
    <tr><td>都道府県河川課</td><td>水利権取得の見込み・申請プロセス</td></tr>
    <tr><td>送配電事業者</td><td>連系可否＋初期工事費（<b>事業性最重要</b>）</td></tr>
    <tr><td>市町村役場 産業振興課</td><td>補助金情報・地元キーマン紹介</td></tr>
  </table>
  <div class="glossary-h3" style="font-size:12px;color:#374151;margin-top:8px">段階2: 地元調整（事業を進める）</div>
  <table>
    <tr><th>相手</th><th>注意点</th></tr>
    <tr><td>区長/自治会長</td><td>信頼関係構築。即決即断は避ける</td></tr>
    <tr><td>農業用水組合</td><td>慣行水利は法律より優先される</td></tr>
    <tr><td>漁協</td><td>漁業権者全員の合意が必要</td></tr>
  </table>
  <div class="glossary-h3" style="font-size:12px;color:#374151;margin-top:8px">段階3: 技術系（事業を組み立てる）</div>
  <table>
    <tr><th>相手</th><th>聞くこと</th></tr>
    <tr><td>水車メーカー（東芝/田中水力/三浦工業）</td><td>推奨機種＋見積</td></tr>
    <tr><td>建設コンサル</td><td>導水路設計＋土木工事費</td></tr>
    <tr><td>新エネルギー財団 (NEF)</td><td>事業性評価補助金の申請可否</td></tr>
  </table>
</div>

<div class="glossary-section">
  <div class="glossary-h3">Phase 5: 事業性精査（1〜2ヶ月）</div>
  <ul>
    <li>詳細設計（流量解析・水車選定・電気設計）</li>
    <li>工事費見積（3社相見積）</li>
    <li>設備利用率の精緻化</li>
    <li>補助金組合せ（NEF + 自治体 + 環境省）</li>
    <li>資金計画（自己資金/銀行融資/ESGファンド）</li>
    <li>IRR最終試算（楽観/標準/悲観）</li>
  </ul>
</div>

<div class="glossary-section">
  <div class="glossary-h3">Phase 6: Go/No-Go判定軸</div>
  <table>
    <tr><th>判定軸</th><th>Go閾値</th><th>No-Go判定</th></tr>
    <tr><td>IRR</td><td>≥ 8%（民間） / ≥ 5%（公益型）</td><td>< 5%</td></tr>
    <tr><td>初期投資</td><td>自己調達+融資で賄える額</td><td>想定より20%超過</td></tr>
    <tr><td>水利権</td><td>取得確度70%以上</td><td>既存権者の反対明確</td></tr>
    <tr><td>系統連系</td><td>工事費が建設費の15%以下</td><td>容量ゼロ or 工事費高騰</td></tr>
    <tr><td>地元同意</td><td>キーマン3名以上 賛成</td><td>反対住民/漁協NG</td></tr>
    <tr><td>補助金</td><td>1件以上採択見込み</td><td>すべて落選</td></tr>
  </table>
</div>

<div class="glossary-section">
  <div class="glossary-h3">Phase 7: 事業開始（6〜18ヶ月）</div>
  <p>並行作業：水利権申請 / FIT認定申請 / 系統連系契約 / 詳細設計委託 / 補助金申請 / 工事発注 → 着工 → 試運転 → 売電開始</p>
</div>

<div class="glossary-section">
  <div class="glossary-h3">⏰ 全体時間軸</div>
  <table>
    <tr><th>Phase</th><th>期間</th><th>成果物</th></tr>
    <tr><td>1 (本アプリ)</td><td>1日</td><td>TOP100候補リスト</td></tr>
    <tr><td>2 (机上精査)</td><td>2-4週</td><td>5-10地点</td></tr>
    <tr><td>3 (現地視察)</td><td>1-2週</td><td>3-5地点</td></tr>
    <tr><td>4 (ヒアリング)</td><td>1-3ヶ月</td><td>1-2地点</td></tr>
    <tr><td>5 (事業性精査)</td><td>1-2ヶ月</td><td>詳細事業計画</td></tr>
    <tr><td>6 (意思決定)</td><td>1-2週</td><td>Go/No-Go</td></tr>
    <tr><td>7 (事業実行)</td><td>6-18ヶ月</td><td>売電開始</td></tr>
  </table>
  <div class="warn"><b>合計:</b> 着手から売電開始まで <b>約1〜2.5年</b>。本アプリのスクリーニングはこの最初の1日に相当する。</div>
</div>
`;

function openGlossary() {
  document.getElementById('glossary-content').innerHTML = GLOSSARY_HTML;
  document.getElementById('glossary-modal').classList.add('open');
}
function closeGlossary() {
  document.getElementById('glossary-modal').classList.remove('open');
}
function openActions() {
  document.getElementById('actions-content').innerHTML = ACTIONS_HTML;
  document.getElementById('actions-modal').classList.add('open');
}
function closeActions() {
  document.getElementById('actions-modal').classList.remove('open');
}
document.getElementById('glossary-btn').onclick = openGlossary;
document.getElementById('actions-btn').onclick = openActions;
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') { closeGlossary(); closeActions(); }
});

applyFilter(false);
"""
