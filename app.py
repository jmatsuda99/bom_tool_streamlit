
import io
import os
import re
import sqlite3
import pandas as pd
import streamlit as st
from utils import normalize_columns, coerce_numeric

st.set_page_config(page_title="BOM Builder", page_icon="🧩", layout="wide")
st.title("🧩 BOM Builder – 複数行チェック（全項目表示） → 列を動的に除外してBOM出力")

with st.sidebar:
    st.markdown("### 手順")
    st.write("1) マスターファイル（Excel/CSV）をアップロード")
    st.write("2) シート選択（Excel）→ 列名の正規化＆数値化")
    st.write("3) **全カラム表示**の編集テーブルで複数行チェック & 数量入力")
    st.write("4) サイドバーの **除外カラム** で不要列を動的に指定")
    st.write("5) 選択行をBOM（CSV/Excel）として出力")

uploaded = st.file_uploader("マスターファイル（Excel: .xlsx / CSV: .csv）", type=["xlsx","csv"])

if uploaded is None:
    st.info("上のボタンからマスターファイルをアップロードしてください。")
    st.stop()

# 1) 読込（Excel or CSV）
df_raw = None
sheet_name = None
if uploaded.name.lower().endswith(".xlsx"):
    sheets = pd.read_excel(uploaded, sheet_name=None, dtype=object)
    # 自動スコア：行×列が最大
    def score(df: pd.DataFrame):
        return int(df.shape[0]) * int(df.shape[1])
    auto_name, _ = max(sheets.items(), key=lambda kv: score(kv[1]))
    sheet_name = st.selectbox("シートを選択", list(sheets.keys()), index=list(sheets.keys()).index(auto_name))
    df_raw = sheets[sheet_name]
else:
    df_raw = pd.read_csv(uploaded, dtype=object)
    sheet_name = "(CSV)"

# 2) 前処理：空行・空列除去
df = df_raw.dropna(how="all")
df = df.dropna(axis=1, how="all")

# 3) 列名正規化・数値化
df = normalize_columns(df)
df = coerce_numeric(df)

st.success(f"読込完了: {uploaded.name} / シート: {sheet_name} / 形状: {df.shape[0]}行×{df.shape[1]}列")

# セッションに選択保持
if "selected_rows" not in st.session_state:
    st.session_state["selected_rows"] = set()
if "qty_map" not in st.session_state:
    st.session_state["qty_map"] = {}

# 4) ページング
page_size = st.sidebar.number_input("ページサイズ", min_value=10, max_value=500, value=50, step=10)
page = st.sidebar.number_input("ページ番号 (1〜)", min_value=1, value=1, step=1)
start = (page-1)*page_size
end = min(start + page_size, len(df))
df_page = df.iloc[start:end].copy()
st.caption(f"表示範囲: 行 {start+1} 〜 {end} / 全 {len(df)} 行")

# 5) 全カラム表示の編集テーブル（st.data_editor）にチェックボックス列と数量列を追加
# グローバル行IDを付与
df_page = df_page.reset_index(drop=False).rename(columns={"index":"__global_idx__"})
df_page["__global_idx__"] = df_page["__global_idx__"].astype(int)

# 既存選択・数量を反映
select_vals = []
qty_vals = []
for _, r in df_page.iterrows():
    gi = int(r["__global_idx__"])
    select_vals.append(gi in st.session_state["selected_rows"])
    if gi in st.session_state["qty_map"]:
        qty_vals.append(int(st.session_state["qty_map"][gi]))
    else:
        default_qty = 1
        if "Qty" in df_page.columns and pd.notna(r.get("Qty", None)):
            try:
                default_qty = int(float(r["Qty"]))
            except:
                default_qty = 1
        qty_vals.append(default_qty)

df_page.insert(1, "Select", select_vals)
df_page.insert(2, "QtySel", qty_vals)

# 表示順：グローバル番号、Select、QtySel、その後に**全ての元カラム**
base_cols = ["__global_idx__", "Select", "QtySel"]
other_cols = [c for c in df_page.columns if c not in base_cols]
df_display = df_page[base_cols + other_cols]

# === 列の動的除外UI（サイドバー）===
all_columns = [c for c in df.columns]  # DBに格納された全項目
# 既定で auto-generated っぽい列名（col, col__2 等）を除外対象に初期設定
default_exclude = [c for c in all_columns if re.match(r"^col(__\d+)?$", c)]
exclude_cols = st.sidebar.multiselect(
    "📦 除外するカラム（出力BOMから除外）",
    options=all_columns,
    default=default_exclude,
    help="不要な列を選ぶと、BOM出力時に除外されます（画面の編集テーブル表示には影響しません）。"
)
st.sidebar.caption(f"除外中: {len(exclude_cols)} 列")

# データエディタ表示（全カラム見せる）
edited = st.data_editor(
    df_display,
    use_container_width=True,
    num_rows="fixed",
    hide_index=True,
    column_config={
        "Select": st.column_config.CheckboxColumn("Select", help="この行をBOMに含める"),
        "QtySel": st.column_config.NumberColumn("Qty", min_value=1, step=1, help="この行の数量（BOM用）"),
        "__global_idx__": st.column_config.NumberColumn("Row#", disabled=True),
    }
)

# 6) 反映ボタン
col1, col2 = st.columns([1,1])
apply_now = col1.button("✅ 選択と数量を反映")
clear_all = col2.button("🧹 選択をすべてクリア")

if apply_now:
    # 反映処理：SelectとQtySelからセッションを更新
    for _, r in edited.iterrows():
        gi = int(r["__global_idx__"])
        if bool(r["Select"]):
            st.session_state["selected_rows"].add(gi)
            qty_val = int(r["QtySel"]) if not pd.isna(r["QtySel"]) else 1
            st.session_state["qty_map"][gi] = max(1, qty_val)
        else:
            if gi in st.session_state["selected_rows"]:
                st.session_state["selected_rows"].discard(gi)
            if gi in st.session_state["qty_map"]:
                st.session_state["qty_map"].pop(gi, None)
    st.success(f"反映しました。現在の選択数: {len(st.session_state['selected_rows'])} 行")

if clear_all:
    st.session_state["selected_rows"] = set()
    st.session_state["qty_map"] = {}
    st.experimental_rerun()

# 7) 選択行の集計表示＆BOM出力（除外カラム適用）
sel_indices = sorted(list(st.session_state["selected_rows"]))
st.subheader(f"選択済み行: {len(sel_indices)} 件")
if len(sel_indices) > 0:
    sel_df = df.iloc[sel_indices].copy()

    # 数量列を作成/上書き
    qty_list = [int(st.session_state["qty_map"].get(gi, 1)) for gi in sel_indices]
    sel_df["Qty"] = qty_list

    # 金額計算
    if "UnitPrice" in sel_df.columns:
        sel_df["Total"] = (sel_df["UnitPrice"].fillna(0).astype(float)) * (sel_df["Qty"].fillna(1).astype(float))

    # 除外カラムをBOM出力に反映（存在チェックの上で削除）
    drop_cols = [c for c in exclude_cols if c in sel_df.columns]
    bom_df = sel_df.drop(columns=drop_cols) if drop_cols else sel_df

    # 画面表示
    st.dataframe(bom_df, use_container_width=True)
    st.caption(f"※ 除外された列: {', '.join(drop_cols) if drop_cols else 'なし'}")

    # ダウンロード（CSV/Excel）
    csv_bytes = bom_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("🔽 選択行をBOM（CSV）としてダウンロード", data=csv_bytes, file_name="bom_selected_rows.csv", mime="text/csv")

    xbuf = io.BytesIO()
    with pd.ExcelWriter(xbuf, engine="openpyxl") as writer:
        bom_df.to_excel(writer, index=False, sheet_name="BOM")
    xbuf.seek(0)
    st.download_button("🔽 選択行をBOM（Excel）としてダウンロード", data=xbuf, file_name="bom_selected_rows.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# 8) 参考：全体プレビュー（先頭100行）
with st.expander("全体プレビュー（先頭100行）を開く"):
    st.dataframe(df.head(100), use_container_width=True)

st.caption("※ 除外カラムはBOM出力にのみ適用されます。画面の編集テーブルには全カラムを表示したままにしています。")
