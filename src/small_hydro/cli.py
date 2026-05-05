"""CLI エントリポイント。"""
import click


@click.group()
def main():
    """small-hydro: 小水力発電ポテンシャルスクリーニング"""


@main.command()
@click.option("--source", required=True, type=click.Choice(["repos", "hydro", "osm"]))
def fetch(source: str):
    """データ取得（REPOSは手動DL案内、OSMは即時取得）。"""
    if source == "repos":
        click.echo("REPOS は手動DLが必要です。")
        click.echo("URL: https://www.renewable-energy-potential.env.go.jp/RePos/")
        click.echo("DL後、data/raw/repos/ に Shapefile or CSV を配置してください。")
    elif source == "hydro":
        click.echo("[Phase 2 未実装] 水文DB取得は ADR-002 確定後に実装")
    elif source == "osm":
        from small_hydro.config import load_config
        from small_hydro.ingest.osm_overpass import fetch_weirs

        config = load_config()
        weirs = fetch_weirs(config.target_bbox)
        click.echo(f"OSM weir 件数: {len(weirs)}")


@main.command()
@click.option("--source", default="repos", type=click.Choice(["repos", "osm"]))
@click.option("--limit", type=int, default=None, help="OSM時の堰サンプル数制限（開発用）")
def screen(source: str, limit: int | None):
    """スクリーニング実行 → CSV/GeoJSON 両方出力。"""
    from small_hydro.pipeline import (
        export_results,
        run_screening,
        run_screening_osm,
    )

    if source == "repos":
        gdf = run_screening()
    else:
        gdf = run_screening_osm(limit=limit)

    csv_path = export_results(gdf, "csv")
    geo_path = export_results(gdf, "geojson")
    click.echo(f"件数: {len(gdf)}")
    click.echo(f"CSV: {csv_path}")
    click.echo(f"GeoJSON: {geo_path}")


@main.command()
@click.option("--format", "fmt", default="geojson", type=click.Choice(["csv", "geojson"]))
@click.option("--source", default="repos", type=click.Choice(["repos", "osm"]))
def export(fmt: str, source: str):
    """結果出力のみ実行。"""
    from small_hydro.pipeline import (
        export_results,
        run_screening,
        run_screening_osm,
    )

    gdf = run_screening() if source == "repos" else run_screening_osm()
    out_path = export_results(gdf, fmt)
    click.echo(f"出力完了: {out_path} ({len(gdf)}件)")


@main.command()
@click.option("--lat", type=float, required=True)
@click.option("--lon", type=float, required=True)
def elevation(lat: float, lon: float):
    """国土地理院標高API疎通確認。"""
    from small_hydro.config import load_config
    from small_hydro.ingest.gsi_elevation import fetch_elevation

    config = load_config()
    elev, hsrc = fetch_elevation(lat, lon, config)
    click.echo(f"elevation={elev}, hsrc={hsrc}")


@main.command()
@click.option("--upstream-lat", type=float, required=True)
@click.option("--upstream-lon", type=float, required=True)
@click.option("--downstream-lat", type=float, required=True)
@click.option("--downstream-lon", type=float, required=True)
def head(
    upstream_lat: float,
    upstream_lon: float,
    downstream_lat: float,
    downstream_lon: float,
):
    """指定2点の落差を標高APIから自動算出。"""
    from small_hydro.compute.head import compute_head
    from small_hydro.config import load_config
    from small_hydro.ingest.gsi_elevation import fetch_elevations

    config = load_config()
    results = fetch_elevations(
        [(upstream_lat, upstream_lon), (downstream_lat, downstream_lon)], config
    )
    up_elev, up_hsrc = results[0]
    down_elev, down_hsrc = results[1]
    click.echo(f"上流: {up_elev}m ({up_hsrc})")
    click.echo(f"下流: {down_elev}m ({down_hsrc})")
    if up_elev is not None and down_elev is not None:
        try:
            h = compute_head(up_elev, down_elev)
            click.echo(f"落差: {h:.2f}m")
        except ValueError as e:
            click.echo(f"エラー: {e}")


@main.command()
@click.option("--source", default="repos", type=click.Choice(["repos", "osm"]))
@click.option(
    "--output",
    default="output/map.html",
    type=click.Path(),
    help="出力HTMLパス",
)
@click.option(
    "--min-kw", type=float, default=10.0, help="表示する最小出力(kW)"
)
@click.option(
    "--max-kw", type=float, default=500.0, help="表示する最大出力(kW)"
)
@click.option(
    "--no-open", is_flag=True, default=False, help="生成後にブラウザを開かない"
)
@click.option(
    "--enrich",
    is_flag=True,
    default=False,
    help="OSM(規制/堰) + 合成スコアで再ランキング",
)
@click.option("--top-n", type=int, default=100, help="TOPレイヤに表示する件数")
def map(
    source: str,
    output: str,
    min_kw: float,
    max_kw: float,
    no_open: bool,
    enrich: bool,
    top_n: int,
):
    """候補をインタラクティブHTMLマップに描画。"""
    import webbrowser
    from pathlib import Path

    from small_hydro.config import load_config
    from small_hydro.ingest.repos import load_repos
    from small_hydro.viz.tabelog_map import generate_tabelog_map

    config = load_config()

    protected = None

    if enrich and source == "repos":
        from small_hydro.ingest.osm_overpass import fetch_protected_areas
        from small_hydro.pipeline import run_screening_enriched

        click.echo("エンリッチドパイプライン実行中（OSM規制/堰取得）...")
        gdf = run_screening_enriched(config=config)
        protected = fetch_protected_areas(config.target_bbox)
        click.echo(f"取得: 候補 {len(gdf)}件 / 規制エリア {len(protected)}件")
    elif source == "repos":
        gdf = load_repos(bbox=config.target_bbox)
    else:
        from small_hydro.pipeline import run_screening_osm

        gdf = run_screening_osm()

    if "output_kw" in gdf.columns:
        gdf = gdf[(gdf["output_kw"] >= min_kw) & (gdf["output_kw"] <= max_kw)]
    click.echo(f"地図対象: {len(gdf)}件 ({min_kw}-{max_kw}kW)")

    out_path = Path(output)
    generate_tabelog_map(gdf, out_path, protected_areas=protected)
    click.echo(f"マップ生成: {out_path.absolute()}")

    if not no_open:
        webbrowser.open(out_path.absolute().as_uri())


if __name__ == "__main__":
    main()
