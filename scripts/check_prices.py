#!/usr/bin/env python3
"""
Amazon Price Monitor
価格チェックスクリプト（ローカルPC実行版）
- 商品ページから価格・送料を取得
- 過去履歴と比較して目標価格以下の場合にメール通知
- docs/data/price_history.json に価格履歴を書き込む
"""

import json
import os
import re
import smtplib
import time
import random
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests
from bs4 import BeautifulSoup

# ---- パス設定 ----
BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCTS_PATH = os.path.join(BASE_DIR, "docs", "data", "products.json")
HISTORY_PATH  = os.path.join(BASE_DIR, "docs", "data", "price_history.json")

JST = timezone(timedelta(hours=9))


# ---- 価格パース ----
def parse_price(text: str) -> int | None:
    text_clean = text.replace(",", "").replace("\u00a0", "").replace(" ", "")
    jpy_matches = re.findall(r"[￥¥]\s*(\d+)", text_clean)
    if jpy_matches:
        valid = [int(v) for v in jpy_matches if int(v) >= 100]
        return max(valid) if valid else None
    float_matches = re.findall(r"(\d+)(?:\.\d+)?", text_clean)
    if float_matches:
        valid = [int(v) for v in float_matches if int(v) >= 100]
        return max(valid) if valid else None
    return None


# ---- Amazon 価格取得 ----
def fetch_price(asin: str, session: requests.Session) -> tuple[int | None, int]:
    url = f"https://www.amazon.co.jp/dp/{asin}?th=1&psc=1"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ja-JP,ja;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.amazon.co.jp/",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    try:
        resp = session.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [ERROR] GET failed for {asin}: {e}")
        return None, 0

    soup = BeautifulSoup(resp.content, "lxml")
    price = None

    for sel in [
        "#corePriceDisplay_desktop_feature_div .a-price .a-offscreen",
        "#corePrice_feature_div .a-price .a-offscreen",
        "#apex_offerDisplay_desktop .a-price[data-a-color='base'] .a-offscreen",
        "#newBuyBoxPrice", "#price_inside_buybox",
        "#priceblock_ourprice", "#priceblock_dealprice",
        "#buyNewSection .a-price .a-offscreen",
        "#buybox .a-price .a-offscreen",
        "#rightCol .a-price .a-offscreen",
    ]:
        el = soup.select_one(sel)
        if el:
            c = parse_price(el.get_text(strip=True))
            if c and c >= 100:
                price = c
                break

    if price is None:
        for el in soup.select(".a-price .a-offscreen"):
            c = parse_price(el.get_text(strip=True))
            if c and c >= 100:
                price = c
                break

    if price is None:
        print(f"  [WARN] Price element not found for ASIN={asin}")
        return None, 0

    shipping = 0
    for sel in ["#deliveryMessageMirId", "#price-shipping-message", ".shipping3P", "#ddmDeliveryMessage"]:
        el = soup.select_one(sel)
        if el:
            txt = el.get_text()
            if not any(kw in txt for kw in ["無料", "FREE", "0円"]):
                c = parse_price(txt)
                if c:
                    shipping = c
            break

    return price, shipping


# ---- メール送信 ----
def send_alert_email(alerts, gmail_user, gmail_app_password, notify_email):
    subject = f"【価格アラート】{len(alerts)}件 目標価格を下回りました"
    lines = ["以下の商品が目標価格を下回りました。\n"]
    for a in alerts:
        lines += [
            f"■ {a['name']}",
            f"  本体価格 : ¥{a['price']:,}",
            f"  送料     : ¥{a['shipping']:,}",
            f"  合計     : ¥{a['total']:,}  ← 目標 ¥{a['target_price']:,}",
            f"  過去最安 : ¥{a['min_price']:,}",
            f"  購入リンク: https://www.amazon.co.jp/dp/{a['asin']}",
            "",
        ]
    msg = MIMEMultipart()
    msg["From"]    = gmail_user
    msg["To"]      = notify_email
    msg["Subject"] = subject
    msg.attach(MIMEText("\n".join(lines), "plain", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_app_password)
        server.sendmail(gmail_user, notify_email, msg.as_string())
    print(f"  [MAIL] Alert sent → {notify_email} ({len(alerts)} items)")


# ---- メイン ----
def main():
    today = datetime.now(JST).strftime("%Y-%m-%d")

    with open(PRODUCTS_PATH, encoding="utf-8") as f:
        products = json.load(f)

    history = {}
    if os.path.exists(HISTORY_PATH):
        with open(HISTORY_PATH, encoding="utf-8") as f:
            history = json.load(f)

    session = requests.Session()
    alerts  = []

    for product in products:
        asin   = product["asin"]
        name   = product["name"]
        target = product.get("target_price")

        print(f"\nChecking [{name}] (ASIN: {asin})")
        price, shipping = fetch_price(asin, session)
        if price is None:
            continue

        total = price + shipping
        print(f"  price=¥{price:,}  shipping=¥{shipping:,}  total=¥{total:,}")

        if asin not in history:
            history[asin] = []
        if today not in [r["date"] for r in history[asin]]:
            history[asin].append({"date": today, "price": price, "shipping": shipping, "total": total})

        all_totals = [r["total"] for r in history[asin]]
        min_price  = min(all_totals)

        if target and total <= target:
            print(f"  [ALERT] ¥{total:,} <= target ¥{target:,}")
            alerts.append({"asin": asin, "name": name, "price": price,
                           "shipping": shipping, "total": total,
                           "target_price": target, "min_price": min_price})

        wait = random.uniform(4.0, 9.0)
        print(f"  waiting {wait:.1f}s ...")
        time.sleep(wait)

    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    print(f"\n[DONE] price_history.json updated.")

    gmail_user     = os.environ.get("GMAIL_USER", "")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD", "")
    notify_email   = os.environ.get("NOTIFY_EMAIL") or gmail_user

    if alerts:
        if gmail_user and gmail_password:
            send_alert_email(alerts, gmail_user, gmail_password, notify_email)
        else:
            print("[WARN] GMAIL_USER / GMAIL_APP_PASSWORD not set.")


if __name__ == "__main__":
    main()
