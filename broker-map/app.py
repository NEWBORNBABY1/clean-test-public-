"""
app.py — Streamlit 網頁介面。只做一件事：把資料庫的內容變成可查詢的畫面。

為什麼要有這一支、而且對 brokers.duckdb「只讀不寫」？
- 畫面壞掉，跟資料壞掉，是兩回事。UI 只負責「呈現」，
  這樣改版面時絕不會動到辛苦清好的資料。
- brokers.duckdb 是 build_db.py 的產物，這裡只查詢它。
  唯一會寫檔的是 study_log（學習紀錄），它寫到自己的 study_log.csv，
  不碰 brokers.duckdb——券商資料庫維持唯讀。

啟動：streamlit run app.py
"""

from pathlib import Path
import datetime as dt

import duckdb
import pandas as pd
import streamlit as st

BASE = Path(__file__).parent
DB_PATH = BASE / "brokers.duckdb"
STUDY_LOG = BASE / "study_log.csv"  # 學習紀錄自己一張表，跟券商資料庫分開


@st.cache_resource
def get_con():
    """開一條唯讀連線。read_only=True 從程式層面保證我們不會誤寫券商資料庫。"""
    if not DB_PATH.exists():
        return None
    return duckdb.connect(str(DB_PATH), read_only=True)


# ---------- 第 1 頁：券商查詢 ----------
def page_broker_lookup():
    st.header("券商查詢")
    con = get_con()
    if con is None:
        st.warning("還沒有 brokers.duckdb。請先在終端機跑 `python build_db.py`。")
        return

    keyword = st.text_input("輸入分點名稱或代碼")
    if not keyword:
        st.info("輸入關鍵字後，顯示 分點 → 總公司 → 集團 的歸屬鏈。")
        return

    # TODO(David): 這是本專案的核心查詢，留給你填——
    #   1. 用參數化查詢（別用字串拼 SQL，避免 SQL injection）：
    #        con.execute("SELECT * FROM firm_to_group WHERE firm LIKE ?", [f"%{keyword}%"])
    #   2. 查到總公司後，往上找集團；再往下列出同集團的全部分點。
    #   3. 用 st.dataframe(...) 把結果畫出來。
    #   先把「這條鏈怎麼一層一層查上去」講給 Claude 聽，再動手。
    st.error("TODO(David): 實作券商查詢邏輯")


# ---------- 第 2 頁：study_log 學習紀錄 ----------
def page_study_log():
    st.header("study_log — 學習紀錄")

    # 讀現有紀錄（沒有檔就給空表）
    if STUDY_LOG.exists():
        log = pd.read_csv(STUDY_LOG)
    else:
        log = pd.DataFrame(columns=["date", "topic", "minutes"])

    # 頁首顯示連續天數
    st.metric("連續學習天數", value=streak_days(log))

    with st.form("add_log"):
        d = st.date_input("日期", value=dt.date.today())
        topic = st.text_input("主題")
        minutes = st.number_input("分鐘數", min_value=0, step=5)
        submitted = st.form_submit_button("記一筆")
        if submitted:
            # TODO(David): 把這筆 append 進 log，再存回 STUDY_LOG（to_csv, index=False）。
            #   注意：這裡寫的是 study_log.csv，不是 brokers.duckdb——券商資料庫維持唯讀。
            st.warning("TODO(David): 實作寫入 study_log.csv")

    st.dataframe(log, use_container_width=True)


def streak_days(log: pd.DataFrame) -> int:
    """算「到今天為止的連續學習天數」。

    TODO(David): 留給你填。想法：把 date 欄轉成日期、去重、排序，
      從今天往回一天一天數，斷掉就停。先講清楚「連續」的定義再寫。
    """
    return 0  # 佔位，實作前先回傳 0


# ---------- 主程式：兩頁切換 ----------
def main():
    st.set_page_config(page_title="broker-map", page_icon="📈")
    st.sidebar.title("broker-map")
    page = st.sidebar.radio("選頁面", ["券商查詢", "study_log"])
    if page == "券商查詢":
        page_broker_lookup()
    else:
        page_study_log()


if __name__ == "__main__":
    main()
