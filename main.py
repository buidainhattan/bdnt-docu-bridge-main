import sys
import logging
from features.scraper import fetch_and_convert_articles
from features.upload_articles import get_or_create_file_search_store, upload_articles_to_store

# Set up logging to match your upload_articles config if desired
logger = logging.getLogger("main")
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M",
)


def main():
    logger.info("Starting Daily Scraper & Delta Upload Job...")

    try:
        # 1. Re-scrape support center
        fetch_and_convert_articles()

        # 2. Sync with Gemini File Search / Vector Store
        target_store = get_or_create_file_search_store()
        upload_articles_to_store(target_store)

        logger.info("Job completed successfully.")
        sys.exit(0)  # Explicit zero exit on success

    except Exception as e:
        logger.error(f"Critical failure during job execution: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
