# BOM Builder (Streamlit)

GitHub + Streamlit Cloud を前提にした最小実装です。**Step1: マスター読込→DB作成→表示**を実装済み。

## 機能
- Excel/CSV アップロード
- Excelはシート選択（自動で最有力シートを初期選択）
- 列名をDB向けに正規化（日本語→代表英名、記号除去、重複名ユニーク化）
- 数値らしい列（Qty/UnitPrice など）を自動数値化（全角・カンマ対応）
- SQLite（`parts`）を生成し、**DB/CSVをダウンロード**
- 先頭100行を表でプレビュー

## ローカル起動
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Community Cloud へのデプロイ
1. GitHub に本一式をコミット（ルートに `app.py` と `requirements.txt` があること）
2. Streamlit Cloud で **New app** → リポジトリ/ブランチを選択
3. Main file は `app.py` を指定
4. デプロイ後、画面でマスターファイル（Excel/CSV）をアップロード

## 次ステップ（今後の拡張）
- カテゴリ1/2 フィルタとチェックボックス選択 → BOM作成
- 端数処理（切上げ/切下げ/四捨五入・任意刻み/任意桁）
- 列順・ヘッダー名の最終調整 UI
- プリセット保存/読込（Streamlit Secrets or Cloud storage）
- Excel出力（書式付き）
