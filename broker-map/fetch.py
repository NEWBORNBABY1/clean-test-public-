"""
fetch.py — 只做一件事：抓證交所公開資料 → 存進 L0 原始層 (data/raw/)。

為什麼是證交所、不是 FinMind？
- 我們要的是「分點 → 總公司 → 集團」的關係。FinMind 只給一張券商名冊，沒有關係。
- 證交所 OpenAPI 兩支資料就把關係帶出來了，而且免 token、公開可抓：
    brokerService/brokerList  → 總公司清單（64 家：代碼、名稱、地址）
    opendata/OpenData_BRK02   → 分點清單（800+ 個，名稱格式「總公司-分點」）
  分點名開頭就是總公司名，所以「分點→總公司」能自動推導（在 build_db 做）。

為什麼只讓這支做「抓」？抓資料會碰網路，最容易失敗；獨立出來，壞了就知道是網路的事。
L0 鐵律：抓回來原封保存、帶日期、永不修改。清理是下一棒 build_db.py 的事。

資料流：證交所 OpenAPI ──fetch.py──▶ data/raw/*.json ──▶ build_db.py
"""

import datetime as dt
import json
from pathlib import Path

import requests

BASE = Path(__file__).parent
RAW_DIR = BASE / "data" / "raw"
TWSE = "https://openapi.twse.com.tw/v1"
SOURCES = {
    "heads": "/brokerService/brokerList",     # 總公司
    "branches": "/opendata/OpenData_BRK02",   # 分點（分公司）
}


def today_tag() -> str:
    """今天日期字串，當檔名一部分，例如 2026-07-14。L0 是歷史快照，不同天要分開留。"""
    return dt.date.today().isoformat()


def save_raw(name: str, text: str) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{name}_{today_tag()}.json"
    path.write_text(text, encoding="utf-8")
    print(f"[存檔] {path.name}  ({len(text)} 字元)")
    return path


def fetch_one(name: str, endpoint: str) -> None:
    resp = requests.get(TWSE + endpoint, timeout=30)
    resp.raise_for_status()  # HTTP 出錯就在這裡炸，比默默拿到空資料好查
    data = resp.json()       # 先確認是合法 JSON（抓到錯誤頁會在這裡發現）
    save_raw(name, json.dumps(data, ensure_ascii=False))
    print(f"    {name}: {len(data)} 筆")


def main() -> None:
    print("=== fetch.py 開始：抓證交所兩支公開資料（免 token）===")
    for name, endpoint in SOURCES.items():
        fetch_one(name, endpoint)
    print("完成。下一步：python build_db.py")


if __name__ == "__main__":
    main()
