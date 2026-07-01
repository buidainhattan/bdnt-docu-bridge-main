from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client()

# 1. List all active Vector Stores in your account
print("=== Active File Search Stores ===")
for store in client.file_search_stores.list():
    print(f"Store Display Name: {store.display_name}")
    print(f"Store ID Resource : {store.name}\n")

    # 2. List every document indexed inside this specific store
    print(f"--- Documents Ingested into {store.display_name} ---")
    try:
        for doc in client.file_search_stores.documents.list(parent=store.name):
            print(f" 📄 Name: {doc.display_name} | Resource Path: {doc.name}")
    except Exception as e:
        print(f" Store is empty or uninitialized: {e}")
    print("=" * 40)
