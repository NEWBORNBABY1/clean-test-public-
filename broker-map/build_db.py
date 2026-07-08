"""
build_db.py — 只做一件事：讀 L0 原始層 → 清理 → 寫進 L1 資料庫 (brokers.duckdb)。

為什麼要有這一支、而且跟 fetch.py 分開？
- 「抓」和「清理」是兩種不同的失敗：抓失敗是網路/API 的事，
  清理失敗是格式/邏輯的事。分開才好抓 bug、好重跑。
- 這一支「只讀 L0、只寫 DuckDB」。它不碰網路，所以可以離線一直重跑，
  改清理邏輯不必再打一次 API——這就是分層的好處。
- 驗收條件之一：刪掉 brokers.duckdb 後，重跑 fetch.py + build_db.py 能完整重建。
  能重建，是因為原始資料都還在 L0。

資料流：data/raw/*.csv  ──build_db.py──▶  brokers.duckdb   （下一棒交給 app.py 只讀查詢）
"""

from pathlib import Path

import duckdb
import pandas as pd

BASE = Path(__file__).parent
RAW_DIR = BASE / "data" / "raw"
MANUAL_DIR = BASE / "data" / "manual"
DB_PATH = BASE / "brokers.duckdb"


def read_manual_csv(name: str) -> pd.DataFrame:
    """讀手工維護的小表。comment='#' 讓我們能在 CSV 裡寫 # 註解而不被當成資料。"""
    df = pd.read_csv(MANUAL_DIR / name, comment="#")
    # 去掉前後空白，避免「元大證券 」和「元大證券」被當成兩家
    return df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)


def load_trader_info() -> pd.DataFrame:
    """把 L0 最新一份 trader_info 原始檔讀成乾淨的 DataFrame。

    TODO(David): 完成這段。步驟提示——
      1. 用 sorted(RAW_DIR.glob("trader_info_*.csv")) 找出所有快照，取最後一個（最新日期）。
      2. FinMind 回傳的是 JSON 文字，裡面資料在 "data" 欄位；
         可以先 import json 讀出來，再 pd.DataFrame(obj["data"])。
      3. 只留我們要的欄位（券商代碼、名稱），欄名統一成 code / name。
      4. 回傳整理好的 DataFrame。
    卡住就停下來，先把「為什麼要挑最新那份」講給 Claude 聽。
    """
    raise NotImplementedError("TODO(David): 實作 load_trader_info()")


def build() -> None:
    print("=== build_db.py 開始：讀 L0 → 清理 → 寫 DuckDB ===")

    # 手工兩張表：這兩張現在就能入庫，不必等 fetch
    firm_to_group = read_manual_csv("firm_to_group.csv")
    futures_ib = read_manual_csv("futures_ib.csv")
    print(f"[讀入] firm_to_group：{len(firm_to_group)} 筆")
    print(f"[讀入] futures_ib：{len(futures_ib)} 筆")

    # TODO(David): traders = load_trader_info()  # 等 fetch.py 先抓好 L0 再打開這行

    # 連到 DuckDB（檔案不存在會自動建立）。這是 L1 唯一的落點。
    con = duckdb.connect(str(DB_PATH))
    try:
        # register 讓 DuckDB 能直接把 pandas DataFrame 當表來查
        con.register("firm_to_group_df", firm_to_group)
        con.register("futures_ib_df", futures_ib)
        con.execute("CREATE OR REPLACE TABLE firm_to_group AS SELECT * FROM firm_to_group_df")
        con.execute("CREATE OR REPLACE TABLE futures_ib AS SELECT * FROM futures_ib_df")

        # TODO(David): 等 load_trader_info() 完成後，把 traders 也建成一張表，
        #   再想「分點 → 總公司 → 集團」這條鏈要怎麼 JOIN 出來（可先做成一個 VIEW）。

        print("[完成] 已寫入 brokers.duckdb：firm_to_group、futures_ib")
    finally:
        con.close()  # 一定要關，不然檔案會被鎖住


if __name__ == "__main__":
    build()
