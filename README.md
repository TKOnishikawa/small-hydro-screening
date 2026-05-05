# 小水力発電 候補地マップ

> 中部・関東甲信越エリアの **50-150kW帯 小水力発電候補地** を、
> 環境省REPOS + OpenStreetMap + 国土地理院 のオープンデータで
> 一次スクリーニングするインタラクティブマップ。

## 🌐 公開URL

🔗 **[マップを開く（GitHub Pages）](https://tkonishikawa.github.io/small-hydro-screening/)**

> 初回ロードに数十秒かかります（11MB の HTML + 8,246件のマーカーデータ）。

## 🎯 これは何？

再生可能エネルギー事業の候補地を、現地に行かずに **机上で素早く絞り込む** ためのツール。

- 全国 28,283件 の REPOS ポテンシャルから対象エリアの **10,183件** を抽出
- **合成スコア**（出力帯×コスト×設備利用率×堰加点）でランキング
- 規制エリア（国立公園等）は自動除外
- 8,246件をブラウザ上でインタラクティブに探索可能

## 🔧 使い方

### 左サイドバー
- 候補リスト（**合成スコア順**、上位200件表示）
- 出力帯フィルタ（50-100kW最優先 / 100-150kW次点 / 全帯）
- ソート切替（合成 / 回収期間 / IRR / kW単価 / 出力）

### 右マップ
- **大赤★（脈動）**: TOP 20（絶対候補）
- **中橙★**: TOP 50
- **小黄★**: TOP 100
- **クラスタ色**: A緑(高品質) / B青 / C橙 / D灰 で密集と質を同時表示
- マーカークリック → **詳細ポップアップ**（経済性3シナリオ・スコア内訳・Google Maps直リンク）

### ボタン
- 🔍 **このエリアで再検索**: 表示中のエリアにフィルタ
- ❓ **用語・前提解説**: スコア計算式・建設費の精度評価（重要）
- 📋 **絞り込み後アクション**: 現地視察〜契約までのプロセスガイド
- 🔗 **URL共有**: 現在のビュー（位置・ズーム・フィルタ）をURLでコピー

## ⚠️ 重要な免責事項

これは **机上の一次スクリーニング** ツールです。事業判断には以下の追加検証が必須：

- 水利権・系統連系・地元調整は別途現地調査・行政協議が必要
- REPOSの建設費（CONST_COST）は **実例の約3倍の保守的悲観値**。詳細は アプリ内「用語・前提解説」参照
- 規制エリアは OpenStreetMap ベース → カバレッジ限定的（国土数値情報 KSJ-A11/A12 等で精緻化推奨）
- 経済性試算は税効果・補助金・建中金利を未考慮

詳細プロセスは アプリ内 **「絞り込み後アクション」** モーダル参照。

## 📊 データソース

| データ | 提供元 | ライセンス |
|------|------|---------|
| 河川水力ポテンシャル(R4) | 環境省 [REPOS](https://repos.env.go.jp/) | 出典明示で利用可 |
| 既存堰・規制エリア | © [OpenStreetMap](https://openstreetmap.org) | ODbL |
| 標高データ・地図タイル | 国土地理院 | 規約遵守 |

## 🛠️ 技術スタック

- **Python 3.11+** / GeoPandas / Shapely
- **Leaflet.js** + Leaflet.markercluster
- **Click** CLI / pytest
- 詳細: [docs/specs/](docs/specs/)

## 📂 リポジトリ構成

```
src/small_hydro/         # コア実装
  ingest/                # REPOS / OSM Overpass / GSI 標高API
  compute/               # 合成スコア・経済性試算（3シナリオ）
  geo/                   # 空間オーバーレイ・近接判定
  viz/                   # Leafletマップ生成
docs/
  index.html             # GitHub Pages 配信元
  specs/                 # 仕様書
  plan/adr/              # アーキテクチャ判断記録
tests/                   # ユニット/統合テスト (42件)
output/                  # ローカル生成物 (gitignore)
data/raw/                # REPOSデータ等 (gitignore)
```

## 🔄 マップ再生成（オーナー作業）

```bash
# 環境構築
python -m venv .venv
.venv/Scripts/activate    # Windows
pip install -e ".[dev,scrape]"

# データ配置
cp .env.example .env
# REPOS データを data/raw/repos/ に手動配置

# 再生成
python -m small_hydro.cli map --enrich

# Pages へ反映
cp output/map.html docs/index.html
git add docs/ && git commit -m "Update map" && git push
```

## 🧪 テスト

```bash
pytest tests/ -v
# 42 passed
```

## ライセンス

ソースコードは MIT。データは各提供元のライセンスに準拠。

## 🤝 共有・利用について

このツールは個人プロジェクトです。事業判断の参考にする場合は、必ず専門家（建設コンサル・電気工事業者・河川管理者）の意見を取得してください。
