import os
import logging
from google import genai
from dotenv import load_dotenv

load_dotenv()
STORE_DISPLAY_NAME = os.getenv("STORE_DISPLAY_NAME")
MANIFEST_FILE = "./data/hash_manifest.txt"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M",
)
logger = logging.getLogger("drop_store")
client = genai.Client()


def drop_entire_store():
    if not STORE_DISPLAY_NAME:
        logger.error("STORE_DISPLAY_NAME environment variable is not set.")
        return

    logger.info(f"--- Deleting Store Container: '{STORE_DISPLAY_NAME}' ---")

    try:
        target_store = next(
            (
                s
                for s in client.file_search_stores.list()
                if s.display_name == STORE_DISPLAY_NAME
            ),
            None,
        )

        if not target_store:
            logger.warning("Remote store container not found.")
            return

        # Must clear documents first to prevent 400 FAILED_PRECONDITION
        documents = client.file_search_stores.documents.list(parent=target_store.name)
        for doc in documents:
            client.file_search_stores.documents.delete(
                name=doc.name, config={"force": True}
            )

        # Safe to delete container now
        client.file_search_stores.delete(name=target_store.name)
        logger.info("Remote vector store container deleted successfully.")

        # Clear local tracking manifest
        if os.path.exists(MANIFEST_FILE):
            os.remove(MANIFEST_FILE)
            logger.info("Local manifest cache cleared.")

    except Exception as e:
        logger.error(f"Error occurred during store drop: {e}")


if __name__ == "__main__":
    drop_entire_store()
