# ADR-002: 水文水質DBの取得方式

## ステータス
Proposed (2026-05-05)

## 背景
国交省 水文水質DB は公開APIなし。フレーム構造の古いWebシステム。

## 検討中の選択肢

| 方式 | メリット | デメリット |
|-----|---------|----------|
| A. `DPFssDB2.exe` をsubprocess駆動 | 公式提供のEXEで抽出が確実 | Windows専用。Cloud Run 等のLinuxサーバに乗らない |
| B. Selenium で検索画面操作 | 環境非依存（Chrome/Firefoxで動作） | 画面構造変更に弱い。重い |
| C. requests + 直接URL叩き | 軽量・高速 | フレーム構造のため可能か未検証 |

## 暫定方針
- Phase 2 着手時に**PoCで検証**
- ローカル運用 → A
- Cloud自動化 → B（C不可な場合）

## 未決事項
- Cloudで Windows コンテナを使うか、ローカルPC で月次バッチを回すか
- `DPFssDB2.exe` の同梱可否（ライセンス確認）

## 参照
- [docs/specs/01_data-sources.md](../../specs/01_data-sources.md)
