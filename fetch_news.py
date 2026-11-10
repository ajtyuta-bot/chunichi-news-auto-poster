

import json

import html

import re

import urllib.request

import xml.etree.ElementTree as ET

from datetime import datetime, timezone, timedelta

from email.utils import parsedate_to_datetime

from pathlib import Path

from urllib.parse import urlparse

# ===== 設定 =====

RSS_URL = "https://news.yahoo.co.jp/rss/categories/sports.xml"

# 記事を保存する時間

HOURS = 72

# 中日ドラゴンズ関連のキーワード

KEYWORDS = [

    "中日",

    "ドラゴンズ",

    "バンテリンドーム",

    "ナゴヤ球場"

]

HEADERS = {

    "User-Agent": "Mozilla/5.0",

    "Accept": "application/rss+xml,application/xml"

}

# ===== 現在時刻 =====

now = datetime.now(timezone.utc)

cutoff = now - timedelta(hours=HOURS)

diagnostics = {

    "checked_at": now.isoformat(),

    "source": "Yahoo!ニュース",

    "rss_items": 0,

    "new_articles": 0,

    "saved_articles": 0,

    "error": None

}

# ===== 既存記事を読み込む =====

articles = []

seen = set()

path = Path("news.json")

if path.exists():

    try:

        old_articles = json.loads(

            path.read_text(encoding="utf-8")

        )

        for article in old_articles:

            url = article.get("url", "")

            date_text = article.get("date", "")

            # Googleニュースの記事は引き継がない

            parsed = urlparse(url)

            if parsed.hostname != "news.yahoo.co.jp":

                continue

            try:

                date = datetime.fromisoformat(

                    date_text

                )

                if date.tzinfo is None:

                    date = date.replace(

                        tzinfo=timezone.utc

                    )

                date = date.astimezone(

                    timezone.utc

                )

            except Exception:

                continue

            # 72時間以内の記事だけ保存

            if not cutoff <= date <= now:

                continue

            if url in seen:

                continue

            seen.add(url)

            articles.append({

                "title": article.get("title", ""),

                "url": url,

                "date": date.isoformat(),

                "image": "",

                "has_image": False

            })

    except Exception as e:

        print("既存記事の読み込みエラー:", e)

# ===== Yahoo!ニュースから新着取得 =====

try:

    request = urllib.request.Request(

        RSS_URL,

        headers=HEADERS

    )

    with urllib.request.urlopen(

        request,

        timeout=30

    ) as response:

        xml_data = response.read()

    root = ET.fromstring(xml_data)

    items = root.findall(".//item")

    diagnostics["rss_items"] = len(items)

    for item in items:

        title = html.unescape(

            item.findtext("title", "").strip()

        )

        url = html.unescape(

            item.findtext("link", "").strip()

        )

        description = html.unescape(

            item.findtext("description", "")

        )

        date_text = item.findtext(

            "pubDate", ""

        )

        if not title or not url:

            continue

        # Yahoo!ニュースの記事だけ取得

        parsed = urlparse(url)

        if parsed.hostname != "news.yahoo.co.jp":

            continue

        # 中日ドラゴンズ関連記事を抽出

        search_text = (

            title + " " +

            re.sub(r"<[^>]*>", " ", description)

        )

        if not any(

            word in search_text

            for word in KEYWORDS

        ):

            continue

        try:

            date = parsedate_to_datetime(

                date_text

            )

            if date.tzinfo is None:

                date = date.replace(

                    tzinfo=timezone.utc

                )

            date = date.astimezone(

                timezone.utc

            )

        except Exception:

            continue

        if not cutoff <= date <= now:

            continue

        if url in seen:

            continue

        seen.add(url)

        articles.append({

            "title": title,

            "url": url,

            "date": date.isoformat(),

            "image": "",

            "has_image": False

        })

        diagnostics["new_articles"] += 1

    print(

        "新しく追加した記事:",

        diagnostics["new_articles"]

    )

except Exception as e:

    diagnostics["error"] = str(e)

    print("RSS取得エラー:", e)

# ===== 新しい順に並べる =====

articles.sort(

    key=lambda x: x["date"],

    reverse=True

)

diagnostics["saved_articles"] = len(articles)

# ===== 記事を保存 =====

Path("news.json").write_text(

    json.dumps(

        articles,

        ensure_ascii=False,

        indent=2

    ),

    encoding="utf-8"

)

Path("diagnostics.json").write_text(

    json.dumps(

        diagnostics,

        ensure_ascii=False,

        indent=2

    ),

    encoding="utf-8"

)

print("保存記事数:", len(articles))

print("診断結果:", diagnostics)
