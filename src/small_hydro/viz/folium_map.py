"""Folium ベースのインタラクティブマップ生成。

出力HTMLはブラウザで開くだけで動作する単独ファイル。
- ズーム/パン
- マーカークリックで詳細ポップアップ
- レイヤートグル（出力帯ごと / TOP / 国立公園）
- ベースマップ切替（OSM / 国土地理院）
- マーカークラスタリング（大量ポイント対応）
"""
from pathlib import Path

import folium
import geopandas as gpd
import pandas as pd
from folium.plugins import MarkerCluster

DEFAULT_BANDS: list[dict] = [
    {"name": "★ 50-100kW", "min": 50, "max": 100, "color": "green", "show": True},
    {"name": "○ 100-150kW", "min": 100, "max": 150, "color": "blue", "show": True},
    {"name": "150kW+", "min": 150, "max": float("inf"), "color": "purple", "show": False},
    {"name": "10-50kW", "min": 10, "max": 50, "color": "lightgray", "show": False},
]


def _format_popup(row: pd.Series) -> str:
    output_kw = row.get("output_kw")
    annual_kwh = row.get("annual_kwh")
    cost = row.get("const_cost_mjpy")
    pref = row.get("prefecture", "")
    muni = row.get("municipality", "")
    linkid = row.get("linkid", "")
    lat = row.geometry.y
    lon = row.geometry.x

    cpkw = row.get("cost_per_kw_mjpy")
    composite = row.get("composite_score")
    rank = row.get("rank")
    band_score = row.get("band_score")
    cost_score = row.get("cost_score")
    cf_score = row.get("cf_score")
    weir_bonus = row.get("weir_bonus")
    near_weir = row.get("near_weir")

    gmaps_url = f"https://www.google.com/maps?q={lat:.6f},{lon:.6f}"
    gsi_url = f"https://maps.gsi.go.jp/#16/{lat:.6f}/{lon:.6f}/"

    rank_html = f"<div style='font-size:13px;color:#888'>順位: <b>{int(rank)}</b></div>" if pd.notna(rank) else ""
    composite_html = (
        f"<div style='font-size:16px;font-weight:bold;color:#1A365D'>"
        f"合成スコア: {composite:.3f}</div>"
        if pd.notna(composite)
        else ""
    )
    cpkw_html = (
        f"<div>kWあたり建設費: <b>{cpkw:.2f}</b> 百万円/kW</div>"
        if pd.notna(cpkw)
        else ""
    )
    weir_html = (
        f"<div style='color:#0D6B3B'>✓ 既存堰近接</div>"
        if (pd.notna(near_weir) and bool(near_weir))
        else ""
    )
    score_breakdown = ""
    if pd.notna(band_score):
        score_breakdown = (
            f"<div style='font-size:11px;color:#666;margin-top:4px'>"
            f"出力帯:{band_score:.2f} / コスト:{cost_score:.2f} / "
            f"設備利用率:{cf_score:.2f} / 堰加点:{weir_bonus:.2f}"
            f"</div>"
        )

    parts = [
        f"<div style='font-family:sans-serif; min-width:260px'>",
        composite_html,
        rank_html,
        f"<hr style='margin:4px 0'>",
        f"<div style='font-size:18px;font-weight:bold;color:#0D6B3B'>"
        f"{output_kw:.1f} kW</div>" if pd.notna(output_kw) else "",
        f"<div>年間発電量: <b>{annual_kwh:,.0f}</b> kWh</div>"
        if pd.notna(annual_kwh) else "",
        f"<div>建設費: <b>{cost:,.0f}</b> 百万円</div>" if pd.notna(cost) else "",
        cpkw_html,
        weir_html,
        f"<div>場所: {pref} {muni}</div>",
        f"<div style='font-size:11px;color:#888'>"
        f"LINKID:{linkid} ({lat:.5f}, {lon:.5f})</div>",
        score_breakdown,
        f"<hr style='margin:4px 0'>",
        f"<a href='{gmaps_url}' target='_blank'>📍 Google Maps</a> | ",
        f"<a href='{gsi_url}' target='_blank'>🗾 地理院地図</a>",
        f"</div>",
    ]
    return "".join(p for p in parts if p)


def _bbox_center(gdf: gpd.GeoDataFrame) -> list[float]:
    if gdf.empty:
        return [35.18, 136.91]
    return [gdf.geometry.y.mean(), gdf.geometry.x.mean()]


def generate_map(
    gdf: gpd.GeoDataFrame,
    output_path: Path,
    bands: list[dict] | None = None,
    zoom_start: int = 8,
    top_n: int = 100,
    protected_areas: gpd.GeoDataFrame | None = None,
) -> Path:
    """候補GeoDataFrame → インタラクティブHTMLマップ生成。

    Args:
        gdf: 候補一覧
        output_path: 出力HTMLパス
        bands: 出力帯定義
        zoom_start: 初期ズーム
        top_n: 合成スコア上位 N 件をハイライトレイヤとして追加
        protected_areas: 国立公園・規制エリアのポリゴンレイヤ
    """
    bands = bands or DEFAULT_BANDS

    center = _bbox_center(gdf)
    m = folium.Map(location=center, zoom_start=zoom_start, tiles=None)

    folium.TileLayer(
        tiles="OpenStreetMap", name="OpenStreetMap", control=True
    ).add_to(m)
    folium.TileLayer(
        tiles="https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png",
        attr="国土地理院",
        name="国土地理院 標準地図",
        max_zoom=18,
    ).add_to(m)
    folium.TileLayer(
        tiles="https://cyberjapandata.gsi.go.jp/xyz/seamlessphoto/{z}/{x}/{y}.jpg",
        attr="国土地理院",
        name="国土地理院 航空写真",
        max_zoom=18,
        show=False,
    ).add_to(m)

    if protected_areas is not None and not protected_areas.empty:
        folium.GeoJson(
            protected_areas[["geometry", "name", "boundary"]].to_json(),
            name=f"🚫 規制エリア (国立公園等 {len(protected_areas)}件)",
            style_function=lambda x: {
                "fillColor": "#ef4444",
                "color": "#c53030",
                "weight": 1,
                "fillOpacity": 0.15,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["name", "boundary"], aliases=["名称", "境界種別"]
            ),
            show=True,
        ).add_to(m)

    if "composite_score" in gdf.columns and len(gdf) > 0:
        top_gdf = (
            gdf.sort_values("composite_score", ascending=False)
            .head(top_n)
            .copy()
        )
        top_layer = folium.FeatureGroup(
            name=f"⭐ TOP {len(top_gdf)} (合成スコア上位)", show=True
        ).add_to(m)
        for _, row in top_gdf.iterrows():
            folium.Marker(
                location=[row.geometry.y, row.geometry.x],
                icon=folium.Icon(color="orange", icon="star", prefix="fa"),
                popup=folium.Popup(_format_popup(row), max_width=340),
                tooltip=(
                    f"#{int(row.get('rank', 0))} | "
                    f"{row.get('output_kw', 0):.1f}kW | "
                    f"score={row.get('composite_score', 0):.3f}"
                ),
            ).add_to(top_layer)

    band_counts: dict[str, int] = {}
    for band in bands:
        subset = gdf[
            (gdf["output_kw"] >= band["min"]) & (gdf["output_kw"] < band["max"])
        ].copy()
        if "excluded" in subset.columns:
            subset = subset[~subset["excluded"]]
        band_counts[band["name"]] = len(subset)

        cluster = MarkerCluster(
            name=f"{band['name']} ({len(subset)}件)",
            show=band.get("show", True),
        ).add_to(m)

        for _, row in subset.iterrows():
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=7,
                color=band["color"],
                weight=2,
                fillColor=band["color"],
                fillOpacity=0.6,
                popup=folium.Popup(_format_popup(row), max_width=340),
                tooltip=(
                    f"{row.get('output_kw', 0):.1f}kW | "
                    f"{row.get('prefecture', '')} {row.get('municipality', '')}"
                ),
            ).add_to(cluster)

    folium.LayerControl(collapsed=False).add_to(m)

    legend_html = _build_legend(bands, band_counts, len(gdf))
    m.get_root().html.add_child(folium.Element(legend_html))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(output_path))
    return output_path


def _build_legend(
    bands: list[dict], counts: dict[str, int], total: int
) -> str:
    rows = "".join(
        f'<div style="margin:2px 0">'
        f'<span style="display:inline-block;width:14px;height:14px;'
        f'background:{b["color"]};border-radius:50%;margin-right:6px;'
        f'vertical-align:middle"></span>'
        f'{b["name"]}: <b>{counts.get(b["name"], 0)}</b>件'
        f'</div>'
        for b in bands
    )
    return f"""
<div style="
  position: fixed; bottom: 30px; left: 30px; z-index: 9999;
  background: rgba(255,255,255,0.92);
  border: 1px solid #aaa; border-radius: 6px;
  padding: 10px 14px; font-family: sans-serif; font-size: 13px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.2);
">
  <div style="font-weight:bold; margin-bottom:4px; color:#1A365D">
    小水力発電 候補地（合成スコア順）
  </div>
  <div style="font-size:11px;color:#666;margin-bottom:6px">
    対象 {total:,} 件
  </div>
  {rows}
  <div style="font-size:11px;color:#888;margin-top:6px;border-top:1px solid #ddd;padding-top:6px">
    マーカークリックで詳細<br>
    🚫赤=規制エリア / ⭐橙=TOP100
  </div>
</div>
"""
