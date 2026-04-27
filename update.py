"""Fetch Google Scholar citation counts via SerpAPI's Author API.

One API call (per page) returns every article for the configured author with
its citation count, so the whole script is ~1 call/week instead of N calls.
"""

import json
import os
import re
import sys
import urllib.parse
import urllib.request

AUTHOR_ID = "u5KCnv0AAAAJ"  # Heming Zhu
PAPERS_FILE = "papers.json"
OUTPUT_FILE = "citations.json"
SERPAPI_ENDPOINT = "https://serpapi.com/search"
PAGE_SIZE = 100  # max per request


def fetch_articles(api_key: str) -> list[dict]:
    """Walk all pages and return every article from the author's profile."""
    articles: list[dict] = []
    start = 0
    while True:
        params = {
            "engine": "google_scholar_author",
            "author_id": AUTHOR_ID,
            "api_key": api_key,
            "num": PAGE_SIZE,
            "start": start,
            "sort": "pubdate",
        }
        url = f"{SERPAPI_ENDPOINT}?{urllib.parse.urlencode(params)}"
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.load(resp)

        page = data.get("articles") or []
        articles.extend(page)
        if len(page) < PAGE_SIZE:
            break
        start += PAGE_SIZE
    return articles


def normalize(s: str) -> str:
    """Lowercase, strip everything except alphanumerics — for fuzzy matching."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def match_count(title: str, articles: list[dict]) -> int | None:
    """Find the article whose normalized title best matches `title`."""
    target = normalize(title)
    if not target:
        return None

    best_score = 0
    best_count: int | None = None
    for art in articles:
        art_title = normalize(art.get("title", ""))
        if not art_title:
            continue

        # Prefix match in either direction — handles title variants like
        # "DUT: Real-time..." vs Scholar's "Real-time..."
        prefix = min(len(target), len(art_title), 30)
        if target[:prefix] == art_title[:prefix]:
            score = prefix
        elif target in art_title or art_title in target:
            score = min(len(target), len(art_title))
        else:
            continue

        if score > best_score:
            best_score = score
            cited_by = art.get("cited_by", {}) or {}
            value = cited_by.get("value")
            best_count = int(value) if value is not None else 0

    return best_count


def main() -> int:
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        print("ERROR: SERPAPI_KEY env var not set", file=sys.stderr)
        return 1

    with open(PAPERS_FILE, encoding="utf-8") as f:
        papers: dict[str, str] = json.load(f)

    existing: dict[str, int] = {}
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, encoding="utf-8") as f:
            existing = json.load(f)

    print(f"Fetching articles for author {AUTHOR_ID}...")
    try:
        articles = fetch_articles(api_key)
    except Exception as e:
        print(f"ERROR: SerpAPI request failed: {e}", file=sys.stderr)
        return 2
    print(f"  got {len(articles)} articles\n")

    counts: dict[str, int] = {}
    for key, title in papers.items():
        count = match_count(title, articles)
        if count is None:
            counts[key] = existing.get(key, 0)
            print(f"  {key:18s}  no match  (kept {counts[key]})")
        else:
            counts[key] = count
            print(f"  {key:18s}  {count}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(counts, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"\nWrote {len(counts)} entries to {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
