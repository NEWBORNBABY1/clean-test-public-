"""
fetch.py — 只做一件事：抓資料 → 存進 L0 原始層 (data/raw/)。

為什麼要有這一支、而且只讓它做「抓」？
- 抓資料會碰網路，是最容易失敗、最不穩定的一段。把它獨立出來，
  失敗時就知道問題出在「抓」，不會跟「清理」或「畫面」混在一起。
- L0 的鐵律：抓回來的原始檔帶日期、原封保存、永不修改。
  之後清理若出錯，我們永遠能回到這份原始資料重來，不必再打一次 API。

資料流：FinMind / 證交所  ──fetch.py──▶  data/raw/*.csv   （下一棒交給 build_db.py）
"""

import os
import datetime as dt
from pathlib import Path

import requests

# --- 路徑設定：所有原始檔都落在 data/raw/ ---
RAW_DIR = Path(__file__).parent / "data" / "raw"
FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"


def today_tag() -> str:
    """回傳今天日期字串，用來當檔名的一部分，例如 2026-07-07。"""
    return dt.date.today().isoformat()


def save_raw(name: str, text: str) -> Path:
    """把抓回來的原始內容存成帶日期的檔案，回傳存檔路徑。

    為什麼檔名要帶日期？因為 L0 是「歷史快照」，不同天抓的要分開留著。
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{name}_{today_tag()}.csv"
    path.write_text(text, encoding="utf-8")
    print(f"[存檔] {path}  ({len(text)} 字元)")
    return path


def fetch_trader_info() -> str:
    """向 FinMind 抓 TaiwanSecuritiesTraderInfo（券商代碼與名稱）。

    TODO(David): 完成這段。步驟提示——
      1. token 從環境變數讀，不要寫死在程式裡：
             token = os.environ.get("FINMIND_TOKEN")
         若沒設定就 raise 一個清楚的錯誤提醒自己去設 .env。
      2. 組 params：{"dataset": "TaiwanSecuritiesTraderInfo", "token": token}
      3. 用 requests.get(FINMIND_URL, params=params, timeout=30) 拿回應。
      4. resp.raise_for_status() 檢查有沒有 HTTP 錯誤。
      5. 回傳 resp.text（原始 JSON 文字），交給 save_raw 存起來。
    先把每一步的「為什麼」講給 Claude 聽，再動手寫。
    """
    raise NotImplementedError("TODO(David): 實作 fetch_trader_info()")


def main() -> None:
    print("=== fetch.py 開始：只抓資料，不做清理 ===")
    # TODO(David): 呼叫 fetch_trader_info() 拿到文字，再 save_raw("trader_info", 文字)。
    # 證交所／櫃買的券商基本資料之後再加第二個 fetch 函式。
    raise NotImplementedError("TODO(David): 在 main() 串起 fetch → save_raw")


if __name__ == "__main__":
    main()
