"""
fetch.py — 只做一件事：抓資料 → 存進 L0 原始層 (data/raw/)。

為什麼要有這一支、而且只讓它做「抓」？
- 抓資料會碰網路，是最容易失敗、最不穩定的一段。把它獨立出來，
  失敗時就知道問題出在「抓」，不會跟「清理」或「畫面」混在一起。
- L0 的鐵律：抓回來的原始檔帶日期、原封保存、永不修改。
  之後清理若出錯，我們永遠能回到這份原始資料重來，不必再打一次 API。

資料流：FinMind  ──fetch.py──▶  data/raw/*.json   （下一棒交給 build_db.py）

執行前提：要先有 FinMind token——
  1. 到 https://finmindtrade.com 免費註冊，會員中心拿 API token
  2. 複製 .env.example 成 .env，填入 FINMIND_TOKEN=你的token
"""

import os
import datetime as dt
from pathlib import Path

import requests

BASE = Path(__file__).parent
RAW_DIR = BASE / "data" / "raw"
FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"


def load_env_file() -> None:
    """把 .env 裡的 KEY=VALUE 一行行讀進環境變數。

    為什麼不直接把 token 寫在程式裡？因為程式會上 GitHub（公開），
    token 等於密碼。.env 被 .gitignore 擋住、只留在你電腦上——
    「程式進版控、秘密不進版控」就是靠這招分離的。
    """
    env_path = BASE / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue  # 跳過空行、註解、格式不對的行
        key, value = line.split("=", 1)  # 只切第一個 =，值裡再出現 = 也不會壞
        os.environ.setdefault(key.strip(), value.strip())


def today_tag() -> str:
    """回傳今天日期字串，用來當檔名的一部分，例如 2026-07-08。"""
    return dt.date.today().isoformat()


def save_raw(name: str, text: str, suffix: str = ".json") -> Path:
    """把抓回來的原始內容存成帶日期的檔案，回傳存檔路徑。

    為什麼檔名帶日期？L0 是「歷史快照」，不同天抓的要分開留著。
    為什麼存 .json？FinMind 回傳的原始格式就是 JSON——L0 保持原樣、不轉格式，
    轉格式是下一層 build_db.py 的工作。
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{name}_{today_tag()}{suffix}"
    path.write_text(text, encoding="utf-8")
    print(f"[存檔] {path}  ({len(text)} 字元)")
    return path


def fetch_trader_info() -> str:
    """向 FinMind 抓 TaiwanSecuritiesTraderInfo（券商代碼與名稱），回傳原始 JSON 文字。"""
    token = os.environ.get("FINMIND_TOKEN")
    if not token:
        raise SystemExit(
            "找不到 FINMIND_TOKEN。請先：copy .env.example .env，"
            "再編輯 .env 填入你的 token（取得方式見檔頭）。"
        )
    params = {"dataset": "TaiwanSecuritiesTraderInfo", "token": token}
    resp = requests.get(FINMIND_URL, params=params, timeout=30)
    resp.raise_for_status()  # HTTP 出錯（401/500…）就在這裡炸，比默默拿到爛資料好查
    return resp.text


def main() -> None:
    print("=== fetch.py 開始：只抓資料，不做清理 ===")
    load_env_file()
    text = fetch_trader_info()
    save_raw("trader_info", text)
    print("完成。下一步：python build_db.py 會把這份原始檔清理入庫。")


if __name__ == "__main__":
    main()
