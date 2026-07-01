from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client()

# 1. List all active Vector Stores in your account
print("=== Active File Search Stores ===")
for store in client.file_search_stores.list():
    print(f"Store Display Name: {store.display_name}")
    print(f"Store ID Resource : {store.name}\n")

