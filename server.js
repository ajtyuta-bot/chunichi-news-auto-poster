require("dotenv").config();
const express = require("express");
const Parser = require("rss-parser");
const cron = require("node-cron");
const OAuth = require("oauth-1.0a");
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const app = express();
const parser = new Parser({ timeout: 15000 });
const PORT = Number(process.env.PORT || 3000);
const KEYWORD = process.env.KEYWORD || "中日ドラゴンズ";
const FEEDS = (process.env.RSS_FEEDS || "").split(",").map(s => s.trim()).filter(Boolean);
const STATE_FILE = path.join(__dirname, "state.json");
app.use(express.json());
app.use(express.static(path.join(__dirname, "public")));

function readState() {
  try { return JSON.parse(fs.readFileSync(STATE_FILE, "utf8")); }
  catch { return { seen: [], log: [], lastCheck: null, lastError: null }; }
}
function writeState(state) {
  fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
}
function titleOf(item) { return String(item.title || "").replace(/\s+/g, " ").trim(); }
function urlOf(item) { return item.link || item.guid || ""; }
function matches(item) {
  const text = `${titleOf(item)} ${item.contentSnippet || item.content || ""}`;
  return text.toLowerCase().includes(KEYWORD.toLowerCase());
}
function makePost(item) {
  // 記事本文の転載は避け、見出し・媒体名・リンク中心の短い投稿文にする
  const title = titleOf(item);
  const source = item.source?.title || item.creator || "";
  const link = urlOf(item);
  return `【中日ドラゴンズ関連ニュース】\n${title}${source ? `\n出典：${source}` : ""}\n${link}`;
}
async function postToX(text) {
  const keys = ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"];
  const missing = keys.filter(k => !process.env[k]);
  if (missing.length) throw new Error("X API認証情報が未設定です: " + missing.join(", "));
  const oauth = new OAuth({
    consumer: { key: process.env.X_API_KEY, secret: process.env.X_API_SECRET },
    signature_method: "HMAC-SHA1",
    hash_function(base, key) {
      return crypto.createHmac("sha1", key).update(base).digest("base64");
    }
  });
  const token = { key: process.env.X_ACCESS_TOKEN, secret: process.env.X_ACCESS_TOKEN_SECRET };
  const request = { url: "https://api.x.com/2/tweets", method: "POST" };
  const auth = oauth.toHeader(oauth.authorize(request, token));
  const response = await fetch(request.url, {
    method: "POST",
    headers: { ...auth, "Content-Type": "application/json" },
    body: JSON.stringify({ text })
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(`X API error ${response.status}: ${JSON.stringify(body)}`);
  return body.data?.id || "posted";
}

async function checkFeeds({ forcePost = false } = {}) {
  const state = readState();
  state.lastCheck = new Date().toISOString();
  state.lastError = null;
  if (!FEEDS.length) {
    state.lastError = "RSS_FEEDS が未設定です。.env に利用可能なRSS/AtomフィードURLを設定してください。";
    writeState(state);
    return { checked: 0, matches: 0, posted: 0, error: state.lastError };
  }
  let checked = 0, matched = 0, posted = 0;
  const maxPosts = Math.max(1, Number(process.env.MAX_POSTS_PER_CHECK || 2));
  for (const feedUrl of FEEDS) {
    try {
      const feed = await parser.parseURL(feedUrl);
      for (const item of (feed.items || []).slice(0, 100).reverse()) {
        checked++;
        const url = urlOf(item);
        const id = url || `${feedUrl}:${titleOf(item)}`;
        if (!url || state.seen.includes(id) || !matches(item)) continue;
        matched++;
        const entry = {
          title: titleOf(item), url, feed: feed.title || feedUrl,
          detectedAt: new Date().toISOString(), status: "検出のみ"
        };
        if ((process.env.AUTO_POST === "true" || forcePost) && posted < maxPosts) {
          try {
            entry.postId = await postToX(makePost({ ...item, source: { title: feed.title || "" } }));
            entry.status = "投稿済み";
            posted++;
          } catch (e) {
            entry.status = "投稿失敗";
            entry.error = e.message;
            state.lastError = e.message;
          }
        }
        state.log.unshift(entry);
        state.seen.push(id);
      }
    } catch (e) {
      state.lastError = `フィード取得エラー (${feedUrl}): ${e.message}`;
    }
  }
  state.seen = state.seen.slice(-5000);
  state.log = state.log.slice(0, 200);
  writeState(state);
  return { checked, matches: matched, posted, error: state.lastError };
}

app.get("/api/status", (_req, res) => {
  const state = readState();
  res.json({
    keyword: KEYWORD,
    feedCount: FEEDS.length,
    autoPost: process.env.AUTO_POST === "true",
    lastCheck: state.lastCheck,
    lastError: state.lastError,
    log: state.log.slice(0, 50)
  });
});
app.post("/api/check", async (_req, res) => {
  try { res.json(await checkFeeds()); }
  catch (e) { res.status(500).json({ error: e.message }); }
});
// 手動投稿は誤操作を避けるため、このエンドポイントは初期状態で無効
app.post("/api/post-latest", async (_req, res) => {
  if (process.env.ALLOW_MANUAL_POST !== "true") {
    return res.status(403).json({ error: "安全設定により無効です。サーバー管理者が明示的に有効化してください。" });
  }
  res.status(501).json({ error: "手動投稿は未実装です。自動投稿のテストを先に行ってください。" });
});

const schedule = process.env.CHECK_CRON || "*/5 * * * *";
if (cron.validate(schedule)) {
  cron.schedule(schedule, async () => {
    try { await checkFeeds(); }
    catch (e) { console.error("定期チェック失敗:", e.message); }
  });
} else {
  console.error("CHECK_CRON が不正です。");
}
app.listen(PORT, () => console.log(`Chunichi X Auto Poster running on port ${PORT}`));
