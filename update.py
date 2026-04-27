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


PREFIX_MIN = 20  # min normalized-prefix chars required for a "same paper" match


def match_count(title: str, articles: list[dict]) -> tuple[int | None, int]:
    """Sum citations across every Scholar article that looks like the same
    paper as `title`. Scholar often lists the arXiv preprint and the
    conference version as two separate clusters with independent counts;
    we want the combined number per paper.

    Returns (total_citations, n_versions_merged); (None, 0) if no match.
    """
    target = normalize(title)
    if not target or len(target) < PREFIX_MIN:
        return None, 0

    total = 0
    n_matched = 0
    for art in articles:
        art_title = normalize(art.get("title", ""))
        if not art_title:
            continue

        # Either a strong shared prefix in both directions, or one title is
        # contained in the other (handles "DUT: Real-time..." vs Scholar's
        # "Real-time..." and "ASH..." arXiv vs CVPR variants).
        prefix = min(len(target), len(art_title), 30)
        same_prefix = prefix >= PREFIX_MIN and target[:prefix] == art_title[:prefix]
        contained = target in art_title or art_title in target
        if not (same_prefix or contained):
            continue

        value = (art.get("cited_by") or {}).get("value")
        total += int(value) if value is not None else 0
        n_matched += 1

    if n_matched == 0:
        return None, 0
    return total, n_matched


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

    print("-- raw articles from Scholar profile --")
    for i, art in enumerate(articles):
        v = (art.get("cited_by") or {}).get("value")
        title = (art.get("title") or "").strip()
        print(f"  [{i:2d}] cited={v!s:>4}  {title[:90]}")
    print()

    counts: dict[str, int] = {}
    for key, title in papers.items():
        count, n = match_count(title, articles)
        if count is None:
            counts[key] = existing.get(key, 0)
            print(f"  {key:18s}  no match  (kept {counts[key]})")
        else:
            counts[key] = count
            suffix = f"  [merged {n} versions]" if n > 1 else ""
            print(f"  {key:18s}  {count}{suffix}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(counts, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"\nWrote {len(counts)} entries to {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
