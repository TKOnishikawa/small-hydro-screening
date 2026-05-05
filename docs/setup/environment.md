# 環境構築

## 前提
- Python 3.11+
- QGIS 3.x（任意・最終可視化用）
- Git Bash or WSL（Windows で `make` 利用時）

## セットアップ手順

```bash
# 1. クローン後、仮想環境作成
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 2. 依存パッケージインストール
make setup
# または
pip install -e ".[dev,scrape]"

# 3. 環境変数
cp .env.example .env
# .env を編集（対象エリアの BBOX を設定）
```

## 動作確認

```bash
pytest tests/unit/ -v
```

## QGIS 連携
- `output/candidates.geojson` を QGIS にドラッグ＆ドロップ
- 国土地理院タイル（標準地図）をベースマップとして追加すると比較しやすい

## トラブルシュート

| 症状 | 対処 |
|------|------|
| `geopandas` インストール失敗（Windows） | `conda install -c conda-forge geopandas` または GDAL whl 経由 |
| 標高APIで `"-----"` が返る | 海域・水部の可能性。Null処理で除外される |
| `make` が動かない（Windows） | Git Bash で実行 or 直接 `python -m small_hydro.cli ...` を叩く |
