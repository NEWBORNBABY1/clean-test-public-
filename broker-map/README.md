# broker-map — 台灣券商關係查詢小系統

把台灣證券**分點 → 總公司 → 母集團**串成可查詢的關係鏈，並完整走一次
「抓資料 → 清理入庫 → 簡單 UI」的資料工程流程。

> 完整背景、合作方式與邊界請看 [`CLAUDE.md`](./CLAUDE.md)。

## 資料怎麼流動（分層觀念是本專案的核心）

```
  證交所 OpenAPI            L0 原始層              L1 清理層              畫面
 (brokerList / BRK02) ──▶ data/raw/*.json ──▶  brokers.duckdb    ──▶   app.py
   + 手工 firm_to_group      (原封保存)      (推導關係、建 v_chain)     (只讀查詢)
        │                      ▲                    ▲
        └── fetch.py 只做這段 ─┘   build_db.py 只做這段 ┘
```

三支程式，職責分離，壞掉時才知道去哪一支找問題：

| 程式 | 只做一件事 | 對資料的動作 |
|------|-----------|-------------|
| `fetch.py`    | 抓證交所兩支公開資料（免 token） | 只寫 `data/raw/`（L0） |
| `build_db.py` | 讀 L0、**推導分點→總公司**、接手工的總公司→集團 | 讀 L0 → 寫 `brokers.duckdb`（L1） |
| `app.py`      | Streamlit 網頁查詢介面 | 只讀資料庫，絕不寫 |

**關係怎麼來的**（兩層、兩種來源，難度不同）：
- **分點 → 總公司**：分點名格式「總公司-分點」（如「元大-松江」），`build_db.py` 用名稱前綴自動推導。
  這層資料源自證交所官方命名，812/812 全中，可信。
- **總公司 → 母集團**：無任何 API，靠手工表 `data/manual/firm_to_group.csv`。
  大型券商已由查證填入（凱基→凱基金控、台新/新光→台新新光金控…），
  小型獨立券商與外資行仍為初稿，**★需 David 逐筆核對★**（核對方法見該檔註解）。

## 本機啟動步驟

```bash
pip install -r requirements.txt   # 第一次才需要
python fetch.py                   # 抓證交所資料 → L0（免 token）
python build_db.py                # 推導關係 → brokers.duckdb
streamlit run app.py              # 開網頁（停止：Ctrl+C）
```

輸入「元大」→ 秒查到 元大 → 元大金控，同集團 149 個分點一覽。

## 驗收條件
- 輸入任一分點，一秒內查到集團歸屬。✅
- 能用自己的話說明三支程式各自存在的理由、資料如何從來源流到畫面。
- 刪掉 `brokers.duckdb` 後重跑 `fetch.py` + `build_db.py` 能完整重建。✅

## 待辦
- `firm_to_group.csv` 的母集團歸屬：大型已查證，其餘待 David 核對（尤其外資行對回全球母公司）。
- `data/manual/futures_ib.csv`（期貨商→交易輔助人）尚未接進 v_chain。
