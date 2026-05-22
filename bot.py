import os
import json
import time
import requests
from datetime import datetime

API_URL = "https://www.1-chome.com/api/index/findByKeyword?page=1&size=24&keyword=RICOH+GR+IV+HDF"
SEARCH_URL = "https://www.1-chome.com/searchResult?keyword=RICOH+GR+IV+HDF"
HISTORY_FILE = "price_history.json"
CHECK_INTERVAL = 3600  # 1時間


def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return {}


def save_history(data):
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_prices():
    resp = requests.get(API_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    items = data.get("data", {}).get("content", [])
    results = {}
    for item in items:
        title = item.get("title", "")
        for detail in item.get("goodsKbDetails", []):
            detail_id = str(detail.get("allGoodsKbDetailId", ""))
            kb_name = detail.get("kbDetailName", "")
            price = detail.get("kbDetailPrice")
            if detail_id and price is not None:
                results[detail_id] = {
                    "name": f"{title}【{kb_name}】",
                    "price": int(price),
                }
    return results


def format_price(price):
    return f"{price:,}円"


def send_discord(webhook_url, name, old_price, new_price):
    diff = new_price - old_price
    sign = "+" if diff >= 0 else ""
    message = (
        f"📸 **RICOH GR IV HDF** 買取価格変動！\n"
        f"条件：{name}\n"
        f"前回：{format_price(old_price)}\n"
        f"現在：{format_price(new_price)}\n"
        f"変動：{sign}{format_price(diff)}\n"
        f"🔗 {SEARCH_URL}"
    )
    payload = {"content": message}
    resp = requests.post(webhook_url, json=payload, timeout=10)
    resp.raise_for_status()


def check():
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        raise ValueError("DISCORD_WEBHOOK_URL が設定されていません")

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 価格チェック中...")

    history = load_history()
    current = fetch_prices()

    if not current:
        print("商品が見つかりませんでした")
        return

    changed = False
    for detail_id, info in current.items():
        name = info["name"]
        new_price = info["price"]
        old_price = history.get(detail_id, {}).get("price")

        if old_price is None:
            print(f"  新規登録: {name} → {format_price(new_price)}")
        elif old_price != new_price:
            print(f"  変動検知: {name} {format_price(old_price)} → {format_price(new_price)}")
            send_discord(webhook_url, name, old_price, new_price)
            changed = True
        else:
            print(f"  変動なし: {name} {format_price(new_price)}")

    save_history(current)
    if changed:
        print("Discord通知送信済み")
    print("チェック完了\n")


def main():
    while True:
        try:
            check()
        except Exception as e:
            print(f"エラー: {e}")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
