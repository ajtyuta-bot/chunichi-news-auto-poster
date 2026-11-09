

import json

import re

import html

import urllib.request

import urllib.parse

import urllib.error

import xml.etree.ElementTree as ET

from datetime import datetime, timezone, timedelta

from email.utils import parsedate_to_datetime

from pathlib import Path

from html.parser import HTMLParser

QUERY = "中日ドラゴンズ when:3d"

RSS = (

    "https://news.google.com/rss/search?q="

    + urllib.parse.quote(QUERY)

    + "&hl=ja&gl=JP&ceid=JP:ja"

)

HEADERS = {

    "User-Agent": "Mozilla/5.0 (compatible; NewsPreviewBot/1.0)",

    "Accept": "text/html,application/xhtml+xml,application/xml"

}

class MetaParser(HTMLParser):

    def __init__(self):

        super().__init__()

        self.meta = {}

        self.canonical = None

    def handle_starttag(self, tag, attrs):

        a = dict(attrs)

        if tag == "meta":

            key = a.get("property") or a.get("name")

            if key:

                self.meta[key.lower()] = a.get("content", "")

        if tag == "link" and a.get("rel", "").lower() == "canonical":

            self.canonical = a.get("href")

def fetch(url, timeout=12):

    req = urllib.request.Request(url, headers=HEADERS)

    with urllib.request.urlopen(req, timeout=timeout) as res:

        return res.geturl(), res.read(500000).decode(

            "utf-8", errors="replace"

        )

def get_article_info(url):

    try:

        final_url, page = fetch(url)

        parser = MetaParser()

        parser.feed(page)

        meta = parser.meta

        article_url = (

            meta.get("og:url")

            or parser.canonical

            or final_url

        )

        article_url = urllib.parse.urljoin(final_url, article_url)

        image = (

            meta.get("og:image")

            or meta.get("twitter:image")

            or ""

        )

        if image:

            image = urllib.parse.urljoin(final_url, image)

        is_google = (

            "news.google.com" in

            urllib.parse.urlparse(article_url).netloc

        )

        return {

            "url": article_url,

            "image": image,

            "has_image": bool(image) and not is_google,

            "is_google": is_google

        }

    except Exception as e:

        print("記事確認失敗:", str(e)[:100])

        return {

            "url": url,

            "image": "",

            "has_image": False,

            "is_google": True

        }

now = datetime.now(timezone.utc)

items = []

_, rss_text = fetch(RSS, timeout=30)

root = ET.fromstring(rss_text)

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

    if not title or not link:

        continue

    if not (now - timedelta(hours=72) <= date <= now):

        continue

    items.append({

        "title": html.unescape(title),

        "url": link,

        "date": date.isoformat()

    })

# 最新60件を確認

items = items[:60]

results = []

seen = set()

for item in items:

    info = get_article_info(item["url"])

    url = info["url"]

    # Googleニュースのリンクのままなら除外

    if info["is_google"]:

        continue

    if url in seen:

        continue

    seen.add(url)

    results.append({

        "title": item["title"],

        "url": url,

        "date": item["date"],

        "image": info["image"],

        "has_image": info["has_image"]

    })

# 写真情報がある記事を優先

results.sort(

    key=lambda x: (not x["has_image"], x["date"]),

    reverse=False

)

Path("news.json").write_text(

    json.dumps(results, ensure_ascii=False, indent=2),

    encoding="utf-8"

)

print("取得件数:", len(results))

print("写真情報あり:", sum(x["has_image"] for x in results))
