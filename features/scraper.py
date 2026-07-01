import os
import re
import requests
from markdownify import markdownify as md

# Target Zendesk Help Center API
API_URL = "https://support.optisigns.com/api/v2/help_center/en-us/articles.json"
OUTPUT_DIR = "./articles"


def slugify(title):
    """
    Converts an article title into a clean, URL-friendly filename slug.
    
    Example Input:  "How do I add a YouTube video?"
    Example Output: "how-do-i-add-a-youtube-video"
    """
    slug = title.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    return slug


def fetch_and_convert_articles():
    """
    Fetches articles from the OptiSigns Help Center API, strips layout elements,
    converts HTML bodies into clean Markdown, and saves them to local disk.

    Example Side-Effect: Creates a directory structure like:
    ./articles/
       ├── how-do-i-add-a-youtube-video.md
       ├── understanding-screen-zones.md
       └── ... (30+ markdown files)

    Each file contains front-matter metadata followed by clean Markdown prose.
    """
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    print("Fetching articles from OptiSigns support...")
    # Request 50 items to easily cross the minimum 30-article requirement
    response = requests.get(f"{API_URL}?per_page=50")

    if response.status_code != 200:
        print(f"Failed to fetch data: {response.status_code}")
        return

    data = response.json()
    articles = data.get("articles", [])

    print(f"Found {len(articles)} articles. Starting conversion...")
    count = 0

    for article in articles:
        # Skip empty or draft articles
        if not article.get("body") or article.get("draft"):
            continue

        title = article.get("title")
        html_body = article.get("body")
        url = article.get("html_url")
        slug = slugify(title) or f"article-{article.get('id')}"

        # Convert HTML to Markdown (preserves headings, code blocks, lists)
        markdown_content = md(html_body, heading_style="ATX")

        # Prepend Metadata for future LLM ingestion / citation accuracy
        final_output = (
            f"---\ntitle: {title}\nsource_url: {url}\n---\n\n{markdown_content}"
        )

        # Save to file
        file_path = os.path.join(OUTPUT_DIR, f"{slug}.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(final_output)

        count += 1

    print(
        f"Successfully processed and saved {count} articles to '{OUTPUT_DIR}' folder."
    )


if __name__ == "__main__":
    fetch_and_convert_articles()
