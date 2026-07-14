"""
app.py — Streamlit 網頁介面。只做一件事：把 brokers.duckdb 變成可查詢的畫面。

對資料庫「只讀不寫」：read_only=True 從程式層面保證改版面不會動到資料。
核心查的是 v_chain（分點→總公司→母集團 寬表，build_db 建好的）。

啟動：streamlit run app.py   （停止：回終端機按 Ctrl+C）
"""

from pathlib import Path

import duckdb
import streamlit as st

BASE = Path(__file__).parent
DB_PATH = BASE / "brokers.duckdb"


@st.cache_resource
def get_con():
    if not DB_PATH.exists():
        return None
    return duckdb.connect(str(DB_PATH), read_only=True)


def main():
    st.set_page_config(page_title="broker-map", page_icon="📈")
    st.title("台灣券商關係查詢")
    con = get_con()
    if con is None:
        st.warning("還沒有 brokers.duckdb。請先在終端機跑 `python fetch.py` 再 `python build_db.py`。")
        return

    kw = st.text_input("輸入分點 / 總公司 / 集團 任一關鍵字（例：元大、元大-松江、開發金）")
    if not kw:
        st.info("輸入後顯示：完整 分點→總公司→母集團 鏈，以及同集團的全部分點。")
        return
    pat = f"%{kw.strip()}%"  # 參數化查詢：使用者輸入永遠只當「資料」，不會變成 SQL 指令

    # 1) 命中的分點（分點名/總公司/母集團 任一含關鍵字）
    hits = con.execute(
        "SELECT 分點代碼, 分點, 總公司, 母集團, 地址 FROM v_chain "
        "WHERE 分點 LIKE ? OR 總公司 LIKE ? OR 母集團 LIKE ? LIMIT 500",
        [pat, pat, pat],
    ).df()
    st.subheader(f"符合「{kw}」的分點（{len(hits)} 筆）")
    if hits.empty:
        st.write("查無資料。")
        return
    st.dataframe(hits, use_container_width=True, hide_index=True)

    # 2) 同集團全部分點：把命中的母集團收集起來，反查整個集團有多少分點
    groups = [g for g in hits["母集團"].dropna().unique().tolist()]
    if groups:
        ph = ",".join("?" for _ in groups)
        fam = con.execute(
            f"SELECT 母集團, 總公司, COUNT(*) AS 分點數 FROM v_chain "
            f"WHERE 母集團 IN ({ph}) GROUP BY 母集團, 總公司 ORDER BY 母集團, 分點數 DESC",
            groups,
        ).df()
        st.subheader("同集團版圖（各總公司分點數）")
        st.dataframe(fam, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
