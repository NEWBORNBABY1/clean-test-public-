"""
app.py — Streamlit 網頁介面。只做一件事：把資料庫的內容變成可查詢的畫面。

為什麼對 brokers.duckdb「只讀不寫」？
- 畫面壞掉，跟資料壞掉，是兩回事。UI 只負責「呈現」，
  改版面時絕不會動到辛苦清好的資料。
- read_only=True 從程式層面保證這件事——就算寫錯程式也寫不進去。

啟動：streamlit run app.py   （停止：回終端機按 Ctrl+C）
"""

from pathlib import Path

import duckdb
import streamlit as st

BASE = Path(__file__).parent
DB_PATH = BASE / "brokers.duckdb"


@st.cache_resource
def get_con():
    """開一條唯讀連線。@st.cache_resource = 連線只開一次、之後重複用，
    不然 Streamlit 每次畫面刷新都會重跑整支程式、狂開連線。"""
    if not DB_PATH.exists():
        return None
    return duckdb.connect(str(DB_PATH), read_only=True)


def table_exists(con, name: str) -> bool:
    """問資料庫「有沒有這張表」。traders 要等 fetch.py 跑過才存在，先問再查才不會炸。"""
    row = con.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = ?", [name]
    ).fetchone()
    return row is not None


def main():
    st.set_page_config(page_title="broker-map", page_icon="📈")
    st.title("台灣券商關係查詢")

    con = get_con()
    if con is None:
        st.warning("還沒有 brokers.duckdb。請先在終端機跑 `python build_db.py`。")
        return

    keyword = st.text_input("輸入券商名稱、集團名或代碼")
    if not keyword:
        st.info("例：輸入「元大」→ 顯示 總公司 → 母集團 鏈、同集團全部成員、期貨 IB 對照。")
        return

    # 查詢鐵律：使用者輸入一律用 ? 佔位符傳進去（參數化查詢），
    # 絕不用字串拼 SQL。拼字串的話，有心人輸入一段 SQL 就能對資料庫為所欲為
    # （SQL injection）；參數化讓輸入永遠只是「資料」，不可能變成「指令」。
    pattern = f"%{keyword.strip()}%"   # 前後加 % = SQL 的「包含」比對

    # --- 1) 總公司 → 母集團 ---
    hits = con.execute(
        "SELECT firm AS 總公司, group_name AS 母集團 "
        "FROM firm_to_group WHERE firm LIKE ? OR group_name LIKE ?",
        [pattern, pattern],
    ).df()
    st.subheader("總公司 → 母集團")
    if hits.empty:
        st.write("手工表裡沒有符合的。firm_to_group.csv 還很小，查不到就是該去補表了。")
    else:
        st.dataframe(hits, use_container_width=True)

        # --- 2) 同集團全部成員：先收集命中的集團，再反查所有成員 ---
        groups = hits["母集團"].unique().tolist()
        placeholders = ",".join("?" for _ in groups)  # 幾個集團就生出幾個 ?
        members = con.execute(
            f"SELECT group_name AS 母集團, firm AS 成員 "
            f"FROM firm_to_group WHERE group_name IN ({placeholders}) "
            f"ORDER BY group_name, firm",
            groups,
        ).df()
        st.subheader("同集團全部成員")
        st.dataframe(members, use_container_width=True)

    # --- 3) 期貨商 ↔ 交易輔助人(IB) ---
    fut = con.execute(
        "SELECT futures_firm AS 期貨商, ib AS 交易輔助人 "
        "FROM futures_ib WHERE futures_firm LIKE ? OR ib LIKE ?",
        [pattern, pattern],
    ).df()
    if not fut.empty:
        st.subheader("期貨商 ↔ 交易輔助人(IB)")
        st.dataframe(fut, use_container_width=True)

    # --- 4) FinMind 券商基本資料（traders 表要 fetch.py + build_db.py 跑過才有）---
    if table_exists(con, "traders"):
        traders = con.execute(
            "SELECT * FROM traders WHERE name LIKE ? OR code LIKE ? LIMIT 100",
            [pattern, pattern],
        ).df()
        if not traders.empty:
            st.subheader("券商基本資料（FinMind）")
            st.dataframe(traders, use_container_width=True)
    else:
        st.caption("尚未匯入 FinMind 券商資料：跑過 fetch.py + build_db.py 後，這裡會多一區。")


if __name__ == "__main__":
    main()
