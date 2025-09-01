
import io
import os
import sqlite3
import pandas as pd
import streamlit as st
from utils import normalize_columns, coerce_numeric

st.set_page_config(page_title="BOM Builder", page_icon="🧩", layout="wide")

st.title("🧩 BOM Builder – Step 1++ : **複数行チェック** → BOM出力")

with st.sidebar:
    st.markdown("### 手順")
    st.write("1) マスターファイルをアップロード（Excel/CSV）")
    st.write("2) シート選択（Excelの場合）")
    st.write("3) 列名の正規化と数値化")
    st.write("4) 各行に**チェックボックス**（複数選択）")
    st.write("5) 選択行を**部品表（BOM）として出力**")

uploaded = st.file_uploader("マスターファイル（Excel: .xlsx / CSV: .csv）", type=["xlsx","csv"])

if uploaded is None:
    st.info("上のボタンからマスターファイルをアップロードしてください。")
    st.stop()

# 1) 読込（Excel or CSV）
df_raw = None
sheet_name = None
if uploaded.name.lower().endswith(".xlsx"):
    sheets = pd.read_excel(uploaded, sheet_name=None, dtype=object)
    # シート選択UI（自動スコア：行×列が最大のシート）
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

# セッションに選択セットを保持
if "selected_rows" not in st.session_state:
    st.session_state["selected_rows"] = set()

# 4) ページング
page_size = st.sidebar.number_input("ページサイズ", min_value=10, max_value=500, value=50, step=10)
page = st.sidebar.number_input("ページ番号 (1〜)", min_value=1, value=1, step=1)
start = (page-1)*page_size
end = min(start + page_size, len(df))
df_page = df.iloc[start:end].copy()
st.caption(f"表示範囲: 行 {start+1} 〜 {end} / 全 {len(df)} 行")

# 5) 各行チェックボックス（複数選択）＋ 数量欄（任意）
st.subheader("行選択（チェックボックス：複数可）")
with st.form(f"row_checkbox_form_page_{page}", clear_on_submit=False):
    # 一括選択/解除
    col_master = st.columns([1,3,3,3,3])[0]
    select_all = col_master.checkbox("このページを全選択", value=False, key=f"select_all_{page}")

    # 行ループ
    checked_keys = []
    qty_inputs = {}
    for i, (_, row) in enumerate(df_page.iterrows()):
        global_idx = start + i
        key_chk = f"row_chk_{global_idx}"
        key_qty = f"row_qty_{global_idx}"

        default_checked = select_all or (global_idx in st.session_state["selected_rows"])
        cols = st.columns([1, 6, 3])
        checked = cols[0].checkbox(f"{global_idx+1}", value=default_checked, key=key_chk)
        # 代表カラムの簡易表示
        show_name = None
        for c in ["Name","ItemID","PartNo"]:
            if c in df.columns:
                show_name = row.get(c, None)
                if pd.notna(show_name):
                    break
        cols[1].write(f"**{str(show_name) if show_name is not None else ''}**")
        # 数量（任意）：Qty列がある場合は初期値に利用
        default_qty = 1
        if "Qty" in df.columns and pd.notna(row.get("Qty", None)):
            try:
                default_qty = int(float(row["Qty"]))
            except:
                default_qty = 1
        qty = cols[2].number_input("Qty", min_value=1, value=default_qty, step=1, key=key_qty)
        if checked:
            checked_keys.append(global_idx)
        qty_inputs[global_idx] = qty

    submitted = st.form_submit_button("✅ このページの選択を適用")

if submitted:
    # 選択反映
    for idx in range(start, end):
        k = f"row_chk_{idx}"
        if k in st.session_state and st.session_state[k]:
            st.session_state["selected_rows"].add(idx)
        else:
            # select_all解除時に未チェックは外す（ページ単位）
            if idx in st.session_state["selected_rows"] and not st.session_state.get(k, False):
                st.session_state["selected_rows"].discard(idx)
    st.success(f"このページの選択を反映しました。現在の選択数: {len(st.session_state['selected_rows'])} 行")

# 6) 選択行の集計表示＆BOM出力
sel_indices = sorted(list(st.session_state["selected_rows"]))
st.subheader(f"選択済み行: {len(sel_indices)} 件")
if len(sel_indices) > 0:
    sel_df = df.iloc[sel_indices].copy()
    # セッション内の数量でQty列を上書き or 新規作成
    qty_list = []
    for gi in sel_indices:
        qv = st.session_state.get(f"row_qty_{gi}", 1)
        qty_list.append(qv)
    sel_df["Qty"] = qty_list

    # 金額計算（任意）：UnitPrice×Qty があれば Total = UnitPrice*Qty
    if "UnitPrice" in sel_df.columns:
        sel_df["Total"] = (sel_df["UnitPrice"].fillna(0).astype(float)) * (sel_df["Qty"].fillna(1).astype(float))

    st.dataframe(sel_df, use_container_width=True)

    # ダウンロード（CSV/Excel）
    csv_bytes = sel_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("🔽 選択行をBOM（CSV）としてダウンロード", data=csv_bytes, file_name="bom_selected_rows.csv", mime="text/csv")

    import io
    xbuf = io.BytesIO()
    with pd.ExcelWriter(xbuf, engine="openpyxl") as writer:
        sel_df.to_excel(writer, index=False, sheet_name="BOM")
    xbuf.seek(0)
    st.download_button("🔽 選択行をBOM（Excel）としてダウンロード", data=xbuf, file_name="bom_selected_rows.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# 7) クリア操作
col_a, col_b = st.columns(2)
if col_a.button("🧹 選択をすべてクリア"):
    st.session_state["selected_rows"] = set()
    st.experimental_rerun()

# 8) 参考：全体プレビュー（先頭100行）
with st.expander("全体プレビュー（先頭100行）を開く"):
    st.dataframe(df.head(100), use_container_width=True)

st.caption("※ ページごとに「このページの選択を適用」を押すと、選択が累積されます。数量は任意入力で、BOM出力時に反映されます。")
