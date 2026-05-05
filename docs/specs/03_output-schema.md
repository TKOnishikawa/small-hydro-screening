# 出力データ辞書

## 出力先
- `output/candidates.csv`: 表形式（Excel等で確認用）
- `output/candidates.geojson`: QGIS可視化用

## 列定義

| # | 列名 | 型 | 単位 | 説明 |
|---|-----|---|------|------|
| 1 | candidate_id | STRING | - | UUID |
| 2 | river_name | STRING | - | 河川名 |
| 3 | intake_lat | FLOAT | deg | 取水点緯度 |
| 4 | intake_lon | FLOAT | deg | 取水点経度 |
| 5 | outflow_lat | FLOAT | deg | 放水点緯度 |
| 6 | outflow_lon | FLOAT | deg | 放水点経度 |
| 7 | head_m | FLOAT | m | 有効落差 |
| 8 | flow_drought | FLOAT | m³/s | 渇水流量 |
| 9 | flow_normal | FLOAT | m³/s | 平水流量 |
| 10 | output_kw_drought | FLOAT | kW | 渇水流量ベース想定出力 |
| 11 | output_kw_normal | FLOAT | kW | 平水流量ベース想定出力 |
| 12 | grid_distance_km | FLOAT | km | 最寄系統接続点距離 |
| 13 | grid_capacity_ok | BOOL | - | 空き容量有無 |
| 14 | regulatory_flags | STRING | - | 該当規制（カンマ区切り） |
| 15 | score | FLOAT | - | 総合スコア（高い順） |
| 16 | data_sources | STRING | - | 算出根拠（REPOS/GSI/MLIT） |
| 17 | gsi_hsrc | STRING | - | 標高データ精度（hsrc） |

## サンプル

| candidate_id | river_name | head_m | flow_drought | output_kw_drought | score |
|--------------|-----------|--------|--------------|-------------------|-------|
| abc-123 | 木曽川支流A | 25.3 | 0.5 | 87.0 | 92.5 |
| def-456 | 飛騨川支流B | 12.1 | 0.8 | 66.5 | 71.2 |
