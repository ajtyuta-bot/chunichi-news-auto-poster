

import json

import html

import urllib.request

import urllib.parse

import xml.etree.ElementTree as ET

from datetime import datetime, timezone, timedelta

from email.utils import parsedate_to_datetime

from pathlib import Path

# Googleニュースの検索条件

# when:3d を外して幅広く取得し、

# 取得後に72時間以内の記事だけ残す

QUERY = "中日ドラゴンズ"

RSS = (

    "https://news.google.com/rss/search?q="

    + urllib.parse.quote(QUERY)

    + "&hl=ja&gl=JP&ceid=JP:ja"

)

HEADERS = {

    "User-Agent": "Mozilla/5.0",

    "Accept": "application/rss+xml,application/xml"

}

now = datetime.now(timezone.utc)

articles = []

diagnostics = {

    "checked_at": now.isoformat(),

    "rss_items": 0,

    "within_72_hours": 0,

    "newest_article": None,

    "oldest_article": None,

    "error": None

}

try:

    request = urllib.request.Request(

        RSS, headers=HEADERS

    )

    with urllib.request.urlopen(

        request, timeout=30

    ) as response:

        xml_data = response.read()

    root = ET.fromstring(xml_data)

    items = root.findall(".//item")

    diagnostics["rss_items"] = len(items)

    print("RSSの記事数:", len(items))

    seen = set()

    all_dates = []

    for item in items:

        title = item.findtext("title", "").strip()

        link = item.findtext("link", "").strip()

        date_text = item.findtext("pubDate", "")

        try:

            date = parsedate_to_datetime(date_text)

            if date.tzinfo is None:

                date = date.replace(

                    tzinfo=timezone.utc

                )

            date = date.astimezone(timezone.utc)

        except Exception:

            continue

        all_dates.append(date)

        if not title or not link:

            continue

        if not (

            now - timedelta(hours=72)

            <= date <= now

        ):

            continue

        if link in seen:

            continue

        seen.add(link)

        articles.append({

            "title": html.unescape(title),

            "url": link,

            "date": date.isoformat(),

            "image": "",

            "has_image": False

        })

    if all_dates:

        diagnostics["newest_article"] = (

            max(all_dates).isoformat()

        )

        diagnostics["oldest_article"] = (

            min(all_dates).isoformat()

        )

    articles.sort(

        key=lambda x: x["date"],

        reverse=True

    )

    diagnostics["within_72_hours"] = len(articles)

    # 0件だった場合は既存データを消さない

    if articles:

        Path("news.json").write_text(

            json.dumps(

                articles,

                ensure_ascii=False,

                indent=2

            ),

            encoding="utf-8"

        )

    else:

        print("72時間以内の記事が0件です")

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
