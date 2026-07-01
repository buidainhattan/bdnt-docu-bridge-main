import os
import time
from google import genai
from dotenv import load_dotenv
from features.logger_config import get_logger

load_dotenv()

STORE_DISPLAY_NAME = os.getenv("STORE_DISPLAY_NAME")
ARTICLES_DIR = "./data/articles"

# Initialize the shared logger instance
logger = get_logger(__name__)
client = genai.Client()


def get_or_create_file_search_store():
    existing_stores = client.file_search_stores.list()
    for store in existing_stores:
        if store.display_name == STORE_DISPLAY_NAME:
            return store

    logger.info("Initializing brand new Vector Store container...")
    return client.file_search_stores.create(
        config={
            "display_name": STORE_DISPLAY_NAME,
            "embedding_model": "models/gemini-embedding-2",
        }
    )


def upload_articles_to_store(store, scrape_stats, files_to_upload):
    """
    Uploads new or updated files to the vector store based on delta tracking,
    preserving the local markdown copies for evaluation.
    """
    if not os.path.exists(ARTICLES_DIR):
        logger.error(f"Articles directory not found at {ARTICLES_DIR}")
        return

    if not files_to_upload:
        logger.info("No delta changes detected. Vector Store is up to date.")
        logger.info(
            f"[METRICS] Delta Analytics -> Added: 0 | Updated: 0 | Skipped: {scrape_stats['skipped']}"
        )
        return

    # Build a map of remote documents to drop replacements cleanly if updating
    remote_docs = {}
    try:
        for doc in client.file_search_stores.documents.list(parent=store.name):
            remote_docs[doc.display_name] = doc.name
    except Exception:
        pass  # Store might be empty

    for filename in files_to_upload:
        file_path = os.path.join(ARTICLES_DIR, filename)

        if not os.path.exists(file_path):
            continue

        # Clear existing remote file copy if it's an update scenario to prevent duplicates
        if filename in remote_docs:
            try:
                logger.info(f"Removing outdated remote document: {filename}")
                client.file_search_stores.documents.delete(
                    name=remote_docs[filename], config={"force": True}
                )
            except Exception as e:
                logger.error(f"Failed deleting old instance of {filename}: {e}")

        try:
            logger.info(f"Uploading: {filename}")
            operation = client.file_search_stores.upload_to_file_search_store(
                file_search_store_name=store.name,
                file=file_path,
                config={"display_name": filename},
            )
            while not operation.done:
                time.sleep(1)
                operation = client.operations.get(operation)
        except Exception as e:
            logger.error(f"Failed uploading {filename}: {e}")

    logger.info(
        f"[METRICS] Delta Analytics -> Added: {scrape_stats['added']} | Updated: {scrape_stats['updated']} | Skipped: {scrape_stats['skipped']}"
    )
