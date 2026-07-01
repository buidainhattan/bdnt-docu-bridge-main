# OptiBot Mini-Clone

A support-bot clone built on Google Gemini. Scrapes a help center, converts articles to markdown, uploads them to a
Gemini File Search Store, and answers support questions grounded in that
content with cited article urls. Articles are updated on a daily schedule via
Railway.

## How it works

1. **Scrape** (`features/scraper.py`) — pulls articles through help center API, converts each article's HTML body to markdown,
   and writes it to `data/articles/<slug>.md` with a small front-matter
   header (`title`, `source_url`).
2. **Delta detection** — each article's final markdown output is hashed
   (MD5) and compared against `data/hash_manifest.txt` from the previous
   run. Only files that are new or whose hash changed are queued for
   upload, unchanged files are skipped. Articles removed upstream are
   deleted locally.
3. **Upload** (`features/upload_articles.py`) — the delta list is pushed to
   a Gemini File Search Store via the API (`file_search_stores.upload_to_file_search_store`).
   If a file already exists remotely (an update), the old remote copy is
   deleted first to avoid duplicate/stale chunks.
4. **Ask** (`ask_bot.py`) — queries the store through Gemini's Interactions
   API with the OptiBot system prompt, using the `file_search` tool scoped
   to our store so answers are grounded only in the uploaded docs.
5. **Orchestration** (`main.py`) — runs scrape → connect/create store →
   upload, logs added/updated/skipped counts, and exits `0` on success or
   `1` on any unhandled exception (for container/cron orchestration).

## Chunking strategy

Chunking is fully managed by Gemini's File Search Store. Whole markdown
files are uploaded as-is (`embedding_model: gemini-embedding-2`), and
Gemini handles splitting/embedding internally. The API does not expose a
per-file chunk count after ingestion, so the pipeline logs **file-level**
counts (added / updated / skipped) as the primary delta metric instead of
a chunk count. Example from a full run against 35 live articles:

```
[METRICS] Delta Analytics -> Added: 35 | Updated: 0 | Skipped: 0
```

Re-running immediately after with no upstream changes correctly detects
zero deltas:

```
[INFO] Scrape Complete -> Added: 0 | Updated: 0 | Skipped: 35
[INFO] No delta changes detected. Vector Store is up to date.
[METRICS] Delta Analytics -> Added: 0 | Updated: 0 | Skipped: 35
```

## Setup

1. Clone the repo and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Copy `.env.sample` to `.env` and fill in your values:
   ```
   GEMINI_API_KEY=your_key_here
   STORE_DISPLAY_NAME=your_store_name
   ```

## Run locally

```bash
python main.py
```

This scrapes the latest articles, uploads any delta to the vector store,
and exits `0` on success. Logs are written to `data/logs/sync_<dd_mm_yyyy>.log`
and echoed to stdout.

To ask the bot a question directly (currently only support embbed question directly in source file):

```bash
python ask_bot.py
```

## Run with Docker

```bash
docker build -t optibot-sync .
docker run --rm -e GEMINI_API_KEY=your_key_here -e STORE_DISPLAY_NAME=your_store_name -v ${PWD}/data:/app/data optibot-sync
```

The container runs the sync once and exits (`0` success / `1` failure) —
no long-running process.

## Daily job

Scheduled to run once per day on [Railway](https://railway.com/project/e10bbe9b-d0ba-4255-a539-4a4110a2fda3/service/cb26c50a-5332-4d28-838b-f52ace925dc1/schedule?environmentId=20345f99-e4cd-469b-810e-0600b74aab8a)
![Execution logging on Railway](https://drive.google.com/file/d/128Ef-g_ChMAflTS4cf6A0QOArr79o--r/view?usp=sharing)
as a scheduled (cron) run of the Docker image above. Job logs are visible
in the Railway deployment logs at that link.

## Sample question & answer

**Q: "How do I add a YouTube video?"**

![OptiBot answering a sample question with citations](https://drive.google.com/file/d/1v_2Kfo-sLtG1KmesZJcjD6W7knmBvSn5/view?usp=drive_link)

OptiBot answers in ≤5 bullets and cites up to 3 article urls, per system prompt.
