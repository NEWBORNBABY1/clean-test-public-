# broker-map — 台灣券商關係查詢小系統

一個「做小、做完、我能懂」的練習專案：把台灣證券分點對應到總公司、再對應到最終母集團，
順便完整走一次「抓資料 → 清理入庫 → 簡單 UI」的資料工程流程。

> 完整背景、合作方式與邊界請看 [`CLAUDE.md`](./CLAUDE.md)。

## 資料怎麼流動（分層觀念是本專案的核心）

```
  資料來源                    L0 原始層              L1 清理層            畫面
 (FinMind / 證交所)  ──▶   data/raw/*.csv   ──▶   brokers.duckdb   ──▶   app.py
   + 手工小表                (原封保存)            (統一格式入庫)        (只讀查詢)
      │                        ▲                      ▲
      └── fetch.py 只做這段 ───┘   build_db.py 只做這段 ┘
```

三支程式，職責分離，這樣壞掉時才知道去哪一支找問題：

| 程式 | 只做一件事 | 對資料的動作 |
|------|-----------|-------------|
| `fetch.py`    | 抓資料 → 存成帶日期的原始檔 | 只寫 `data/raw/`（L0） |
| `build_db.py` | 讀 L0、清理、寫入資料庫       | 讀 L0 → 寫 `brokers.duckdb`（L1） |
| `app.py`      | Streamlit 網頁查詢介面        | 只讀資料庫，絕不寫 |

## 本機啟動步驟（回家在自己電腦上做）

```bash
# 1. 裝套件（第一次才需要）
pip install -r requirements.txt

# 2. 設定 FinMind token（複製範本後填入自己的 token）
cp .env.example .env      # Windows PowerShell: copy .env.example .env
#   然後編輯 .env，填 FINMIND_TOKEN=你的token

# 3. 抓資料 → 進 L0
python fetch.py

# 4. 清理 → 建資料庫
python build_db.py

# 5. 開網頁
streamlit run app.py
```

## 驗收條件（做到就算完成）
- 輸入任一分點，一秒內查到集團歸屬。
- 我能用自己的話說明三支程式各自存在的理由、資料如何從來源流到畫面。
- 刪掉 `brokers.duckdb` 後，重跑 `fetch.py` 與 `build_db.py` 能完整重建。

## 目前進度
骨架已建好，三支程式的「關鍵邏輯」留了 `TODO(David)`，
之後我們照合作協議一步步填、每一步我都要能自己解釋。
