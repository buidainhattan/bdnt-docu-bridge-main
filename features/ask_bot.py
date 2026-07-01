import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client()
STORE_DISPLAY_NAME = os.getenv("STORE_DISPLAY_NAME")


def query_assistant(question: str):
    """
    Queries the Gemini model using the File Search tool attached
    to our custom knowledge vector store, via the new Interactions API.

    Expected Output: Prints the exact grounded answer with citations.
    """
    # 1. Locate our vector store resource reference
    target_store_name = None
    for store in client.file_search_stores.list():
        if store.display_name == STORE_DISPLAY_NAME:
            target_store_name = store.name
            break

    if not target_store_name:
        print("Error: Store not found. Run upload_articles.py first.")
        return

    print(f"Asking Bot: '{question}'\nThinking...")

    system_instruction = (
        "You are OptiBot, the customer-support bot for OptiSigns.com.\n"
        "Tone: helpful, factual, concise.\n"
        "Only answer using the uploaded docs.\n"
        "Max 5 bullet points; else link to the doc.\n"
        "Cite up to 3 'Article URL:' lines per reply."
    )

    try:
        interaction_stream = client.interactions.create(
            model="gemini-3.5-flash",
            system_instruction=system_instruction,
            input=question,
            stream=True,
            tools=[
                {
                    "type": "file_search",
                    "file_search_store_names": [target_store_name],
                }
            ],
        )
    except Exception as e:
        print(f"DEBUG: interactions.create raised: {type(e).__name__}: {e}")
        return

    print("\n=== OptiBot Response ===")

    # Print out response as soon as it arrives
    for event in interaction_stream:
        if event.event_type == "step.delta":
            if event.delta.type == "text":
                print(event.delta.text, end="", flush=True)

    print("\n=========================")


if __name__ == "__main__":
    query_assistant("How do I add a YouTube video?")
