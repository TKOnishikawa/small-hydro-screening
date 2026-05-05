from unittest.mock import MagicMock, patch

import pandas as pd

from small_hydro.ingest.osm_overpass import _build_weir_query, fetch_weirs


def test_build_weir_query_format():
    query = _build_weir_query((135.8, 34.5, 138.3, 36.5))
    assert "node[waterway=weir]" in query
    assert "(34.5,135.8,36.5,138.3)" in query
    assert "out:json" in query


def test_fetch_weirs_empty():
    mock_response = MagicMock()
    mock_response.json.return_value = {"elements": []}
    mock_response.raise_for_status.return_value = None

    with patch(
        "small_hydro.ingest.osm_overpass.requests.get", return_value=mock_response
    ):
        gdf = fetch_weirs((135.8, 34.5, 138.3, 36.5), use_cache=False)

    assert len(gdf) == 0
    assert gdf.crs.to_string() == "EPSG:4326"


def test_fetch_weirs_with_data():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "elements": [
            {"id": 1, "lat": 35.5, "lon": 137.0, "tags": {"name": "テスト堰A"}},
            {"id": 2, "lat": 35.6, "lon": 137.1, "tags": {}},
        ]
    }
    mock_response.raise_for_status.return_value = None

    with patch(
        "small_hydro.ingest.osm_overpass.requests.get", return_value=mock_response
    ):
        gdf = fetch_weirs((135.8, 34.5, 138.3, 36.5), use_cache=False)

    assert len(gdf) == 2
    assert gdf.iloc[0]["river_name"] == "テスト堰A"
    assert pd.isna(gdf.iloc[1]["river_name"])
    assert gdf.iloc[0]["osm_id"] == 1
    assert gdf.iloc[0].geometry.x == 137.0
    assert gdf.iloc[0].geometry.y == 35.5
