import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

STORE_DISPLAY_NAME = os.getenv("STORE_DISPLAY_NAME")
client = genai.Client()


def wipe_store():
    # 1. Locate the target store resource ID
    target_store = None
    for store in client.file_search_stores.list():
        if store.display_name == STORE_DISPLAY_NAME:
            target_store = store
            break

    if not target_store:
        print(f"Store '{STORE_DISPLAY_NAME}' not found.")
        return

    # 2. Iterate and delete every single document inside the store
    print(f"Wiping documents from store: {target_store.name}")
    try:
        for doc in client.file_search_stores.documents.list(parent=target_store.name):
            client.file_search_stores.documents.delete(
                name=doc.name, config={"force": True}
            )
        print("Remote store successfully wiped.")
    except Exception as e:
        print(f"Error occurred: {e}")

    # 3. Remove local tracking state file
    if os.path.exists(".hash_manifest.txt"):
        os.remove(".hash_manifest.txt")
        print("Local manifest cache file removed.")


if __name__ == "__main__":
    wipe_store()
