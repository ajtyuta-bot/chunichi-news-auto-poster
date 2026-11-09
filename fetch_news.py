

import json

import html

import urllib.request

import urllib.parse

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

    "User-Agent": "Mozilla/5.0",

    "Accept": "text/html,application/xml"

}

class MetaParser(HTMLParser):

    def __init__(self):

        super().__init__()

        self.meta = {}

        self.canonical = ""

    def handle_starttag(self, tag, attrs):

        a = dict(attrs)

        if tag == "meta":

            key = a.get("property") or a.get("name")

            if key:

                self.meta[key.lower()] = a.get("content", "")

        if tag == "link":

            if "canonical" in a.get("rel", "").lower():

                self.canonical = a.get("href", "")

def fetch(url, timeout=10):

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

        article_url = urllib.parse.urljoin(

            final_url, article_url

        )

        image = (

            meta.get("og:image")

            or meta.get("twitter:image")

            or ""

        )

        if image:

            image = urllib.parse.urljoin(final_url, image)

        return article_url, image

    except Exception:

        return url, ""

now = datetime.now(timezone.utc)

articles = []

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

    if not (

        now - timedelta(hours=72) <= date <= now

    ):

        continue

    articles.append({

        "title": html.unescape(title),

        "url": link,

        "date": date.isoformat()

    })

articles = articles[:60]

results = []

seen = set()

for article in articles:

    original_url = article["url"]

    resolved_url, image = get_article_info(original_url)

    if not resolved_url.startswith("https://"):

        resolved_url = original_url

    if resolved_url in seen:

        continue

    seen.add(resolved_url)

    is_google = (

        urllib.parse.urlparse(resolved_url)

        .hostname == "news.google.com"

    )

    results.append({

        "title": article["title"],

        "url": resolved_url,

        "date": article["date"],

        "image": image,

        "has_image": bool(image) and not is_google

    })

# 写真情報のあるニュースを優先

# 同じ条件なら新しい記事が先

results.sort(

    key=lambda x: (

        x["has_image"],

        x["date"]

    ),

    reverse=True

)

Path("news.json").write_text(

    json.dumps(

        results,

        ensure_ascii=False,

        indent=2

    ),

    encoding="utf-8"

)

print("取得件数:", len(results))

print(

    "写真情報あり:",

    sum(x["has_image"] for x in results)

)
