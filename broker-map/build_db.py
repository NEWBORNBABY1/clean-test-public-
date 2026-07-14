"""
build_db.py — 只做一件事：讀 L0 → 清理、推導關係 → 寫進 brokers.duckdb。

這支是本專案的核心，做三件事：
  1. 讀證交所兩份 L0：總公司(heads)、分點(branches)。
  2. **推導 分點→總公司**：分點名格式「總公司-分點」（如「元大-松江」），
     取名稱前綴對回總公司名。長名優先比對，臺銀證券等差字的用別名表補。
  3. 讀手工表 firm_to_group（總公司→母集團，這層只有人知道，無 API），
     建 VIEW v_chain 把整條「分點→總公司→母集團」串成一張寬表給 app 查。

為什麼跟 fetch 分開？抓是網路的事、清理是邏輯的事，分開才好各自重跑。
這支不碰網路，可離線一直重跑；改推導邏輯不必再抓一次。

資料流：data/raw/*.json + data/manual/firm_to_group.csv ──▶ brokers.duckdb（含 v_chain）
"""

import html
import json
from pathlib import Path

import duckdb
import pandas as pd

BASE = Path(__file__).parent
RAW_DIR = BASE / "data" / "raw"
MANUAL_DIR = BASE / "data" / "manual"
DB_PATH = BASE / "brokers.duckdb"

# 分點名開頭與總公司名對不上的少數例外，在這裡補別名（分點前綴 -> 總公司名）
# 來源命名不一致：麥格理/麥格里、台中銀/台中商銀、臺銀/臺銀證券。
ALIASES = {"臺銀": "臺銀證券", "犇亞": "犇亞證券", "香港商麥格里": "港商麥格理",
           "麥格里": "港商麥格理", "台中商銀": "台中銀"}


def normalize(s: str) -> str:
    """統一字面：解 HTML 實體（犇→&#29319;）、去空白、臺↔台 視為同字。"""
    return html.unescape(s).replace(" ", "").replace("臺", "台")


def latest(prefix: str) -> Path:
    """取某來源最新一份 L0 快照。檔名帶 ISO 日期，字串排序=日期排序，取最後一個。"""
    files = sorted(RAW_DIR.glob(f"{prefix}_*.json"))
    if not files:
        raise SystemExit(f"找不到 {prefix}_*.json——請先跑 python fetch.py")
    return files[-1]


def read_manual_csv(name: str) -> pd.DataFrame:
    df = pd.read_csv(MANUAL_DIR / name, comment="#")
    return df.apply(lambda c: c.str.strip() if c.dtype == "object" else c)


def derive_head(branch_name: str, head_names: list[str]) -> str | None:
    """從分點名推出總公司名。head_names 需長名在前，避免「兆豐」誤吃更長的名。"""
    clean = normalize(branch_name)
    for h in head_names:
        if clean.startswith(normalize(h)):
            return h
    for alias, real in ALIASES.items():
        if clean.startswith(normalize(alias)):
            return real
    return None


def build() -> None:
    print("=== build_db.py 開始：讀 L0 → 推導關係 → 寫 DuckDB ===")

    heads = pd.DataFrame(json.loads(latest("heads").read_text(encoding="utf-8")))
    heads = heads.rename(columns={"Code": "code", "Name": "name",
                                  "Address": "address", "Telephone": "phone"})
    branch_raw = json.loads(latest("branches").read_text(encoding="utf-8"))
    branches = pd.DataFrame(branch_raw).rename(columns={
        "證券商代號": "code", "證券商名稱": "name", "地址": "address", "電話": "phone"})
    branches["name"] = branches["name"].apply(html.unescape)  # 解掉來源的 HTML 實體（如 犇）

    # 推導 分點→總公司（長名優先）
    head_names = sorted(heads["name"].tolist(), key=len, reverse=True)
    branches["head_name"] = branches["name"].apply(lambda n: derive_head(n, head_names))
    matched = branches["head_name"].notna().sum()
    print(f"[讀入] 總公司 {len(heads)}、分點 {len(branches)}")
    print(f"[推導] 分點→總公司：對到 {matched}、對不到 {len(branches) - matched}")

    firm_to_group = read_manual_csv("firm_to_group.csv").rename(columns={"group": "group_name"})
    print(f"[讀入] firm_to_group：{len(firm_to_group)} 筆（總公司→母集團，手工維護）")

    con = duckdb.connect(str(DB_PATH))
    try:
        for tname, df in [("heads", heads), ("branches", branches),
                          ("firm_to_group", firm_to_group)]:
            con.register(f"{tname}_df", df)
            con.execute(f"CREATE OR REPLACE TABLE {tname} AS SELECT * FROM {tname}_df")

        # v_chain：分點 → 總公司 → 母集團，一張寬表。LEFT JOIN 讓對不到集團的分點也留著。
        con.execute("""
            CREATE OR REPLACE VIEW v_chain AS
            SELECT b.code AS 分點代碼, b.name AS 分點, b.head_name AS 總公司,
                   g.group_name AS 母集團, b.address AS 地址
            FROM branches b
            LEFT JOIN firm_to_group g ON b.head_name = g.firm
            ORDER BY b.head_name, b.code
        """)
        n = con.execute("SELECT COUNT(*) FROM v_chain WHERE 母集團 IS NOT NULL").fetchone()[0]
        print(f"[完成] brokers.duckdb 已建：heads、branches、firm_to_group、v_chain")
        print(f"       其中 {n} 個分點已補上母集團（其餘待 firm_to_group 補齊）")
    finally:
        con.close()


if __name__ == "__main__":
    build()
