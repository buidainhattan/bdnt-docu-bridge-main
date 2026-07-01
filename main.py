import sys
from features.scraper import fetch_and_convert_articles
from features.upload_articles import (
    get_or_create_file_search_store,
    upload_articles_to_store,
)
from features.logger_config import get_logger

# Initialize the shared logger instance
logger = get_logger(__name__)


def main():
    logger.info("=== Starting Daily Sync Job ===")

    try:
        # 1. Run the scraper to fetch, convert, and get delta lists
        scrape_stats, files_to_upload = fetch_and_convert_articles()

        # 2. Connect to or initialize the Gemini File Search Store
        store = get_or_create_file_search_store()

        # 3. Process the upload pipeline using the explicit delta list
        upload_articles_to_store(store, scrape_stats, files_to_upload)

        logger.info("=== Daily Sync Job Completed Successfully ===")
        # Explicit clean exit for Docker container orchestration
        sys.exit(0)

    except Exception as e:
        logger.critical(f"Job failed with an unhandled exception: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
