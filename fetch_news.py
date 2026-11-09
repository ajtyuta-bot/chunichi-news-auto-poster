

import json

import urllib.request

import urllib.parse

import xml.etree.ElementTree as ET

from datetime import datetime, timezone, timedelta

from email.utils import parsedate_to_datetime

from pathlib import Path

query = urllib.parse.quote("中日ドラゴンズ when:3d")

url = (

    "https://news.google.com/rss/search?q="

    + query + "&hl=ja&gl=JP&ceid=JP:ja"

)

req = urllib.request.Request(url, headers={

    "User-Agent": "Mozilla/5.0",

    "Accept": "application/rss+xml, application/xml"

})

now = datetime.now(timezone.utc)

articles = []

with urllib.request.urlopen(req, timeout=30) as response:

    root = ET.fromstring(response.read())

for item in root.findall(".//item"):

    title = item.findtext("title", "").strip()

    link = item.findtext("link", "").strip()

    date_text = item.findtext("pubDate", "")

    try:

        date = parsedate_to_datetime(date_text)

        if date.tzinfo is None:

            date = date.replace(tzinfo=timezone.utc)

    except Exception:

        continue

    if not (now - timedelta(hours=72) <= date <= now):

        continue

    if title and link.startswith("https://"):

        articles.append({

            "title": title,

            "url": link,

            "date": date.isoformat()

        })

articles.sort(key=lambda x: x["date"], reverse=True)

Path("news.json").write_text(

    json.dumps(articles, ensure_ascii=False, indent=2),

    encoding="utf-8"

)

print(f"ニュース取得成功：{len(articles)}件")
