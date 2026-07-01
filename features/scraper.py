import os
import re
import hashlib
import requests
from markdownify import markdownify as md
from features.logger_config import get_logger

API_URL = "https://support.optisigns.com/api/v2/help_center/en-us/articles.json"
DATA_DIR = "./data"
OUTPUT_DIR = os.path.join(DATA_DIR, "articles")
MANIFEST_FILE = os.path.join(DATA_DIR, "hash_manifest.txt")

# Initialize the shared logger instance
logger = get_logger(__name__)


def slugify(title):
    slug = title.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    return slug


def ensure_directories():
    """Ensures both data and articles output directories exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)


def load_manifest() -> dict:
    manifest = {}
    if os.path.exists(MANIFEST_FILE):
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    filename, file_hash = line.strip().split(":", 1)
                    manifest[filename] = file_hash
    return manifest


def save_manifest(manifest: dict):
    ensure_directories()
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        for filename, file_hash in manifest.items():
            f.write(f"{filename}:{file_hash}\n")


def fetch_and_convert_articles():
    ensure_directories()

    logger.info("Fetching articles from OptiSigns support...")
    response = requests.get(f"{API_URL}?per_page=35")

    if response.status_code != 200:
        logger.error(f"Failed to fetch data: {response.status_code}")
        return {"added": 0, "updated": 0, "skipped": 0}, []

    data = response.json()
    articles = data.get("articles", [])

    current_manifest = load_manifest()
    new_manifest = {}
    stats = {"added": 0, "updated": 0, "skipped": 0}
    active_files = set()
    files_to_upload = []

    for article in articles:
        if not article.get("body") or article.get("draft"):
            continue

        title = article.get("title")
        html_body = article.get("body")
        url = article.get("html_url")
        slug = slugify(title) or f"article-{article.get('id')}"
        filename = f"{slug}.md"
        active_files.add(filename)

        markdown_content = md(html_body, heading_style="ATX")
        final_output = (
            f"---\ntitle: {title}\nsource_url: {url}\n---\n\n{markdown_content}"
        )

        content_hash = hashlib.md5(final_output.encode("utf-8")).hexdigest()
        new_manifest[filename] = content_hash

        # Keep/refresh local files on disk for physical evaluation/inspection
        file_path = os.path.join(OUTPUT_DIR, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(final_output)

        # Delta evaluation
        if filename in current_manifest:
            if current_manifest[filename] == content_hash:
                stats["skipped"] += 1
                continue
            else:
                stats["updated"] += 1
                files_to_upload.append(filename)
        else:
            stats["added"] += 1
            files_to_upload.append(filename)

    # Clean up local files no longer present in upstream API source
    for local_file in os.listdir(OUTPUT_DIR):
        if local_file.endswith(".md") and local_file not in active_files:
            os.remove(os.path.join(OUTPUT_DIR, local_file))

    save_manifest(new_manifest)

    logger.info(
        f"Scrape Complete -> Added: {stats['added']} | Updated: {stats['updated']} | Skipped: {stats['skipped']}"
    )
    return stats, files_to_upload
