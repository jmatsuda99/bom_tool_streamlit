
import re
import math
import pandas as pd
import numpy as np

ALIAS = {
    "カテゴリ1":"Category1", "カテゴリ２":"Category2", "カテゴリ2":"Category2",
    "品目名":"Name", "品名":"Name", "部品名":"Name",
    "数量":"Qty", "初期数量":"QtyDefault", "既定数量":"QtyDefault",
    "単価":"UnitPrice", "価格":"UnitPrice", "金額":"Amount",
    "メモ":"Note", "備考":"Note",
    "年当たり":"Cost_per_year", "per-year":"Cost_per_year",
    "kWh当たり":"Cost_per_kWh", "per-kWh":"Cost_per_KWh",
    "型番":"PartNo", "品番":"PartNo", "ItemID":"ItemID", "ID":"ItemID"
}

NUMERIC_LIKE = {"qty","qtydefault","unitprice","amount","cost_per_year","cost_per_kwh"}

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols = []
    for c in df.columns:
        c0 = str(c).strip()
        c1 = ALIAS.get(c0, c0)
        c1 = re.sub(r"\s+", "_", c1)
        c1 = re.sub(r"[^0-9A-Za-z_]", "_", c1)
        if re.match(r"^[0-9]", c1):
            c1 = "C_" + c1
        if c1 == "" or re.match(r"^_+$", c1):
            c1 = "col"
        cols.append(c1 or "col")
    # make unique
    seen = {}
    uniq = []
    for i, c in enumerate(cols):
        base = c
        k = 1
        while c in seen:
            k += 1
            c = f"{base}__{k}"
        seen[c] = True
        uniq.append(c)
    df = df.copy()
    df.columns = uniq
    return df

def to_numeric_series(series: pd.Series) -> pd.Series:
    def to_num(x):
        if pd.isna(x): return np.nan
        s = str(x).strip().replace(",", "")
        s = s.translate(str.maketrans("０１２３４５６７８９．－", "0123456789.-"))
        try:
            return float(s)
        except:
            return np.nan
    return series.map(to_num)

def coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        if c.lower() in NUMERIC_LIKE:
            out[c] = to_numeric_series(out[c])
    return out
