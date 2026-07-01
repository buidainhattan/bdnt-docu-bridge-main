import hashlib
import logging
import os
import sys
import time
from logging.handlers import TimedRotatingFileHandler
from dotenv import load_dotenv
from google import genai

load_dotenv()

# Read the variables dynamically from the environment
STORE_DISPLAY_NAME = os.getenv("STORE_DISPLAY_NAME")
ARTICLES_DIR = "./articles"
MANIFEST_FILE = ".data/hash_manifest.txt"
LOG_DIR = "./logs"

# Ensure the logs directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# --- Logging Configuration ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.handlers.clear()

# 1. Setup Daily Rotating File Handler (accurate to the minute)
file_handler = TimedRotatingFileHandler(
    filename=os.path.join(LOG_DIR, "sync.log"),
    when="midnight",
    interval=1,
    encoding="utf-8",
)
file_formatter = logging.Formatter(
    fmt="[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M"
)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# 2. Keep standard console output stream handler
console_handler = logging.StreamHandler(sys.stdout)
console_formatter = logging.Formatter(
    fmt="[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M"
)
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)


client = genai.Client()


def get_md5_hash(file_path: str) -> str:
    """Calculates the MD5 hash of a local file to detect content modifications."""
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()


def load_manifest() -> dict:
    """Loads the previously uploaded file hashes from a local file."""
    manifest = {}
    if os.path.exists(MANIFEST_FILE):
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    filename, file_hash = line.strip().split(":", 1)
                    manifest[filename] = file_hash
    return manifest


def save_manifest(manifest: dict):
    """Saves the current file hashes to the local manifest tracker."""
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        for filename, file_hash in manifest.items():
            f.write(f"{filename}:{file_hash}\n")


def get_or_create_file_search_store():
    logger.info("--- [START] VERIFYING DATASTORE INFRASTRUCTURE ---")
    existing_stores = client.file_search_stores.list()
    for store in existing_stores:
        if store.display_name == STORE_DISPLAY_NAME:
            return store

    logger.info("Datastore not found. Initializing brand new Vector Store container...")
    new_store = client.file_search_stores.create(
        config={
            "display_name": STORE_DISPLAY_NAME,
            "embedding_model": "models/gemini-embedding-2",
        }
    )
    return new_store


def upload_articles_to_store(store):
    """
    Upload scraped articles to file search store.
    Check for changes in old files through saved hash value before uploading old files.
    """
    if not os.path.exists(ARTICLES_DIR):
        logger.error(f"Directory '{ARTICLES_DIR}' does not exist.")
        return

    stats = {"added": 0, "updated": 0, "skipped": 0}
    current_manifest = load_manifest()
    new_manifest = {}

    remote_docs = {}
    try:
        for doc in client.file_search_stores.documents.list(parent=store.name):
            remote_name = (
                doc.display_name.rsplit(".", 1)[0]
                if "." in doc.display_name
                else doc.display_name
            )
            remote_docs[remote_name] = doc.name
    except Exception as e:
        logger.warning(f"Remote document index reading skipped or empty: {str(e)}")

    local_files = [f for f in os.listdir(ARTICLES_DIR) if f.endswith(".md")]

    logger.info("--- [PROCESSING] COMPUTING LOCAL FILES DELTA ---")
    logger.info(f"Targeting storage manifest: {len(local_files)} articles found.")

    for filename in local_files:
        file_path = os.path.join(ARTICLES_DIR, filename)
        current_hash = get_md5_hash(file_path)
        new_manifest[filename] = current_hash

        clean_name = filename.rsplit(".", 1)[0]

        # Scenario 1: File already exists on the remote store
        if clean_name in remote_docs:
            previous_hash = current_manifest.get(filename)

            if previous_hash and previous_hash == current_hash:
                stats["skipped"] += 1
                continue
            else:
                try:
                    client.file_search_stores.documents.delete(
                        name=remote_docs[clean_name], config={"force": True}
                    )

                    operation = client.file_search_stores.upload_to_file_search_store(
                        file_search_store_name=store.name,
                        file=file_path,
                        config={"display_name": filename},
                    )
                    while not operation.done:
                        time.sleep(1)
                        operation = client.operations.get(operation)

                    stats["updated"] += 1
                except Exception as e:
                    logger.error(f"Failed to update {filename}: {str(e)}")

        # Scenario 2: Brand new file container
        else:
            try:
                operation = client.file_search_stores.upload_to_file_search_store(
                    file_search_store_name=store.name,
                    file=file_path,
                    config={"display_name": filename},
                )
                while not operation.done:
                    time.sleep(1)
                    operation = client.operations.get(operation)

                stats["added"] += 1
            except Exception as e:
                logger.error(f"Failed to upload {filename}: {str(e)}")

    save_manifest(new_manifest)

    logger.info("--- [FINISHED] DOCUMENT VECTOR COMPILATION COMPLETION ---")
    logger.info(
        f"[METRICS] Delta Analytics -> Added: {stats['added']} | Updated: {stats['updated']} | Skipped: {stats['skipped']}"
    )


if __name__ == "__main__":
    target_store = get_or_create_file_search_store()
    upload_articles_to_store(target_store)
