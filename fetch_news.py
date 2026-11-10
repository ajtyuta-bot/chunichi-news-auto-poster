

import json

import html

import re

import urllib.request

import xml.etree.ElementTree as ET

from datetime import datetime, timezone, timedelta

from email.utils import parsedate_to_datetime

from pathlib import Path

from urllib.parse import urlparse

# Yahoo!ニュースのスポーツ記事

RSS_URL = "https://news.yahoo.co.jp/rss/categories/sports.xml"

# 中日ドラゴンズに関する検索ワード

KEYWORDS = [

    "中日",

    "ドラゴンズ",

    "ドラゴンズ",

    "バンテリンドーム",

    "ナゴヤ球場",

]

HOURS = 72

HEADERS = {

    "User-Agent": "Mozilla/5.0",

    "Accept": "application/rss+xml, application/xml"

}

now = datetime.now(timezone.utc)

diagnostics = {

    "checked_at": now.isoformat(),

    "source": "Yahoo!ニュース",

    "rss_items": 0,

    "within_72_hours": 0,

    "matched_articles": 0,

    "error": None

}

articles = []

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

    seen = set()

    for item in items:

        title = html.unescape(

            item.findtext("title", "").strip()

        )

        link = html.unescape(

            item.findtext("link", "").strip()

        )

        description = html.unescape(

            item.findtext("description", "")

        )

        date_text = item.findtext(

            "pubDate", ""

        )

        if not title or not link:

            continue

        # Yahoo!ニュースの記事URLだけを使用

        parsed = urlparse(link)

        if parsed.hostname not in (

            "news.yahoo.co.jp",

            "www.news.yahoo.co.jp"

        ):

            continue

        # 中日ドラゴンズに関連する記事を抽出

        search_text = (

            title + " " +

            re.sub(r"<[^>]*>", " ", description)

        )

        if not any(

            keyword in search_text

            for keyword in KEYWORDS

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

        # 72時間以内の記事のみ

        if not (

            now - timedelta(hours=HOURS)

            <= date <= now

        ):

            continue

        if link in seen:

            continue

        seen.add(link)

        articles.append({

            "title": title,

            "url": link,

            "date": date.isoformat(),

            "image": "",

            "has_image": False

        })

    articles.sort(

        key=lambda x: x["date"],

        reverse=True

    )

    diagnostics["within_72_hours"] = len(

        articles

    )

    diagnostics["matched_articles"] = len(

        articles

    )

    # Yahoo!の記事だけで更新する

    # 0件の場合は古いGoogle記事を残さない

    Path("news.json").write_text(

        json.dumps(

            articles,

            ensure_ascii=False,

            indent=2

        ),

        encoding="utf-8"

    )

    print("RSS取得件数:", len(items))

    print("中日関連記事:", len(articles))

except Exception as e:

    diagnostics["error"] = str(e)

    print("取得エラー:", e)

Path("diagnostics.json").write_text(

    json.dumps(

        diagnostics,

        ensure_ascii=False,

        indent=2

    ),

    encoding="utf-8"

)

print("診断結果:", diagnostics)
