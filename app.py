
import io
import os
import sqlite3
import pandas as pd
import streamlit as st
from utils import normalize_columns, coerce_numeric

st.set_page_config(page_title="BOM Builder", page_icon="🧩", layout="wide")

st.title("🧩 BOM Builder – Step 1: マスター読込 → DB作成 → 表示")

with st.sidebar:
    st.markdown("### 手順")
    st.write("1) マスターファイルをアップロード（Excel/CSV）")
    st.write("2) シート選択（Excelの場合）")
    st.write("3) 列名の正規化と数値化")
    st.write("4) SQLite DB 作成（`parts` テーブル）")
    st.write("5) 先頭100行プレビュー & ダウンロード")

uploaded = st.file_uploader("マスターファイル（Excel: .xlsx / CSV: .csv）", type=["xlsx","csv"])

if uploaded is None:
    st.info("上のボタンからマスターファイルをアップロードしてください。")
    st.stop()

# 1) 読込（Excel or CSV）
df_raw = None
sheet_name = None
if uploaded.name.lower().endswith(".xlsx"):
    sheets = pd.read_excel(uploaded, sheet_name=None, dtype=object)
    # シート選択UI
    sheet_opts = list(sheets.keys())
    # 自動スコア（行×列が最大のシート）
    def score(df: pd.DataFrame):
        return int(df.shape[0]) * int(df.shape[1])
    auto_name, _ = max(sheets.items(), key=lambda kv: score(kv[1]))
    sheet_name = st.selectbox("シートを選択", sheet_opts, index=sheet_opts.index(auto_name))
    df_raw = sheets[sheet_name]
else:
    # CSV
    df_raw = pd.read_csv(uploaded, dtype=object)
    sheet_name = "(CSV)"

# 2) 前処理：空行・空列除去
df = df_raw.dropna(how="all")
df = df.dropna(axis=1, how="all")

# 3) 列名正規化・数値化
df = normalize_columns(df)
df = coerce_numeric(df)

st.success(f"読込完了: {uploaded.name} / シート: {sheet_name} / 形状: {df.shape[0]}行×{df.shape[1]}列")

# 4) SQLite DB をメモリで作成し、ダウンロード用にも保存
conn = sqlite3.connect(":memory:")
df.to_sql("parts", conn, if_exists="replace", index=False)

# ダウンロード用にファイル化
buf_db = io.BytesIO()
with sqlite3.connect("file:parts.db?mode=rwc&cache=private&uri=true") as disk_conn:
    df.to_sql("parts", disk_conn, if_exists="replace", index=False)
    # ファイルを読み出してメモリへ
    with open("parts.db","rb") as f:
        buf_db.write(f.read())
os.remove("parts.db")
buf_db.seek(0)

# 5) プレビュー表示
st.subheader("プレビュー（先頭100行）")
st.dataframe(df.head(100), use_container_width=True)

# 6) ダウンロード
csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
st.download_button("🔽 正規化CSVをダウンロード", data=csv_bytes, file_name="parts_master_normalized.csv", mime="text/csv")
st.download_button("🔽 SQLite DB（partsテーブル）をダウンロード", data=buf_db, file_name="bom.db", mime="application/octet-stream")

st.caption("※ 次のステップでは、カテゴリ1/2フィルタ、チェックボックス選択、端数処理、列順・ヘッダー名調整、プリセット保存/読込を実装予定です。")
