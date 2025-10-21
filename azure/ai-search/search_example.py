import os
import sys

from dotenv import load_dotenv, find_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient


def main() -> None:
    load_dotenv(find_dotenv())
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    key = os.getenv("AZURE_SEARCH_QUERY_KEY") or os.getenv("AZURE_SEARCH_ADMIN_KEY")
    index_name = os.getenv("AZURE_SEARCH_INDEX")
    if not endpoint or not key or not index_name:
        print("Missing AZURE_SEARCH_* envs", file=sys.stderr)
        sys.exit(1)

    client = SearchClient(endpoint=endpoint, index_name=index_name, credential=AzureKeyCredential(key))

    query = os.getenv("QUERY", "machine")
    print(f"Keyword search: '{query}'")
    results = client.search(search_text=query, top=5, query_type="semantic", semantic_configuration_name="VectorSearch")
    for r in results:
        print(f"- {r['title']} (id={r['id']}) score={r['@search.score']}")


if __name__ == "__main__":
    main()


