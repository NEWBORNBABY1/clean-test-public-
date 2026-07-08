"""
build_db.py — 只做一件事：讀 L0 原始層 → 清理 → 寫進 L1 資料庫 (brokers.duckdb)。

為什麼要有這一支、而且跟 fetch.py 分開？
- 「抓」和「清理」是兩種不同的失敗：抓失敗是網路/API 的事，
  清理失敗是格式/邏輯的事。分開才好抓 bug、好重跑。
- 這一支「只讀 L0、只寫 DuckDB」。它不碰網路，可以離線一直重跑，
  改清理邏輯不必再打一次 API——這就是分層的好處。
- 驗收條件之一：刪掉 brokers.duckdb 後重跑能完整重建。
  能重建，是因為原始資料都還在 L0。

資料流：data/raw/*.json + data/manual/*.csv ──build_db.py──▶ brokers.duckdb ──▶ app.py 查詢
"""

import json
from pathlib import Path

import duckdb
import pandas as pd

BASE = Path(__file__).parent
RAW_DIR = BASE / "data" / "raw"
MANUAL_DIR = BASE / "data" / "manual"
DB_PATH = BASE / "brokers.duckdb"


def read_manual_csv(name: str) -> pd.DataFrame:
    """讀手工維護的小表。comment='#' 讓 CSV 裡的 # 註解行不被當成資料。"""
    df = pd.read_csv(MANUAL_DIR / name, comment="#")
    # 去掉前後空白，避免「元大證券 」和「元大證券」被當成兩家——清理層的基本功
    return df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)


def load_trader_info() -> pd.DataFrame | None:
    """把 L0 最新一份 trader_info 快照讀成乾淨的 DataFrame。沒抓過就回 None。

    清理層在這裡做三件事：
      1. 挑「最新」快照——sorted() 對「名字_2026-07-08.json」這種格式
         按字串排序剛好就是按日期排序（這是檔名帶 ISO 日期的隱藏好處）。
      2. 原始 JSON → 表格（FinMind 把資料放在 "data" 欄位裡）。
      3. 欄名統一成我們自己的規格：code / name。
         上游想叫什麼隨它，進了 L1 一律說我們的語言——之後 app 只認 code/name。
    """
    files = sorted(RAW_DIR.glob("trader_info_*.json"))
    if not files:
        return None
    latest = files[-1]
    print(f"[讀入] L0 快照：{latest.name}")
    obj = json.loads(latest.read_text(encoding="utf-8"))
    df = pd.DataFrame(obj["data"])
    df = df.rename(columns={
        "securities_trader_id": "code",
        "securities_trader": "name",
    })
    # 只留存在的欄位（API 欄位可能增減，防呆）
    keep = [c for c in ("code", "name", "date", "address", "phone") if c in df.columns]
    return df[keep]


def build() -> None:
    print("=== build_db.py 開始：讀 L0 → 清理 → 寫 DuckDB ===")

    # --- 手工兩張表：現在就能入庫，不必等 fetch ---
    firm_to_group = read_manual_csv("firm_to_group.csv")
    # 「group」是 SQL 保留字（GROUP BY 的那個 group），直接當欄名會跟資料庫吵架。
    # 清理層的職責之一：把名字改成不會惹麻煩的 group_name。
    firm_to_group = firm_to_group.rename(columns={"group": "group_name"})
    futures_ib = read_manual_csv("futures_ib.csv")
    print(f"[讀入] firm_to_group：{len(firm_to_group)} 筆")
    print(f"[讀入] futures_ib：{len(futures_ib)} 筆")

    # --- FinMind 券商資料：抓過才有 ---
    traders = load_trader_info()

    con = duckdb.connect(str(DB_PATH))
    try:
        # register 讓 DuckDB 把 pandas DataFrame 直接當表查
        con.register("firm_to_group_df", firm_to_group)
        con.register("futures_ib_df", futures_ib)
        con.execute("CREATE OR REPLACE TABLE firm_to_group AS SELECT * FROM firm_to_group_df")
        con.execute("CREATE OR REPLACE TABLE futures_ib AS SELECT * FROM futures_ib_df")
        tables = ["firm_to_group", "futures_ib"]

        if traders is not None:
            con.register("traders_df", traders)
            con.execute("CREATE OR REPLACE TABLE traders AS SELECT * FROM traders_df")
            tables.append(f"traders({len(traders)} 筆)")
        else:
            print("[略過] 還沒有 FinMind 原始檔——先跑 python fetch.py 再回來，traders 表才會出現。")

        print(f"[完成] 已寫入 brokers.duckdb：{'、'.join(tables)}")
    finally:
        con.close()  # 一定要關，不然檔案被鎖住，app.py 會打不開


if __name__ == "__main__":
    build()
