# scholar-citations

Weekly-refreshed Google Scholar citation counts for the papers listed in
[papers.json](./papers.json). Counts live in [citations.json](./citations.json)
and are consumed by `kv2000.github.io` via `img.shields.io` dynamic JSON badges.

## How it works

1. GitHub Action runs every Monday 03:00 UTC (`.github/workflows/update.yml`).
2. `update.py` makes a single call to SerpAPI's
   [Google Scholar Author API](https://serpapi.com/google-scholar-author-api)
   (`author_id=u5KCnv0AAAAJ`), which returns every article on the profile with
   its `cited_by.value`. The script fuzzy-matches each entry in `papers.json`
   against the returned articles and writes counts to `citations.json`.
3. If `citations.json` changed, the workflow commits + pushes.
4. `img.shields.io` fetches the raw JSON file and renders a per-paper badge.

**API budget:** 1 call/week (one Author API page covers <100 articles), well
under SerpAPI's 100 calls/month free tier.

## Setup (one-time)

1. Create a public repo `kv2000/scholar-citations` on GitHub.
2. From this folder, push the contents:

   ```bash
   cd d:/woot_page_new/scholar-citations
   git init -b main
   git add .
   git commit -m "init"
   git remote add origin git@github.com:kv2000/scholar-citations.git
   git push -u origin main
   ```

3. On GitHub: **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `SERPAPI_KEY`
   - Value: (your fresh, rotated SerpAPI key)

4. **Settings → Actions → General → Workflow permissions**
   - Pick **"Read and write permissions"** so the workflow can push.

5. **Actions tab → "Update Scholar citations" → Run workflow** to populate
   `citations.json` immediately.

## Adding a new paper

1. Add `"key": "Exact paper title"` to `papers.json`.
2. Add the same key + a placeholder `0` to `citations.json` (optional; the
   script handles missing keys).
3. In the Hexo site, add a `shields.io` badge with `query=$.key` to the paper's
   `pub-links` block.

## Badge URL pattern (used in pug)

```
https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fkv2000%2Fscholar-citations%2Fmain%2Fcitations.json&query=%24.PAPERKEY&label=scholar&color=4285F4&logo=googlescholar&labelColor=beige
```

Replace `PAPERKEY` with the matching key from `papers.json`.
