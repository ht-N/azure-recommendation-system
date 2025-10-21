import os
import sys
from time import sleep

from dotenv import load_dotenv, find_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexerClient
from azure.search.documents import SearchClient


def main() -> None:
    load_dotenv(find_dotenv())
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    key = os.getenv("AZURE_SEARCH_ADMIN_KEY")
    index_name = os.getenv("AZURE_SEARCH_INDEX")
    if not endpoint or not key or not index_name:
        print("Missing AZURE_SEARCH_* envs", file=sys.stderr)
        sys.exit(1)

    indexer_name = f"{index_name}-indexer"
    client = SearchIndexerClient(endpoint=endpoint, credential=AzureKeyCredential(key))

    try:
        # Reset to force full re-crawl
        client.reset_indexer(indexer_name)
    except Exception:
        pass

    client.run_indexer(indexer_name)
    print(f"Triggered indexer '{indexer_name}'. Waiting for completion...")

    # Simple wait loop
    for _ in range(60):
        info = client.get_indexer_status(indexer_name)
        status_obj = getattr(info, "status", None)
        status_str = (getattr(status_obj, "value", status_obj) or "").lower()
        if status_str in ("running", "inprogress"):
            sleep(5)
            continue
        print(f"Indexer status: {status_obj}")
        last_result = getattr(info, "last_result", None)
        if last_result:
            err = getattr(last_result, "error_message", None)
            if err:
                print(f"Last error: {err}", file=sys.stderr)
        # Print item counts if available
        try:
            result_status = getattr(last_result, "status", None)
            items = getattr(last_result, "items_processed", None)
            failed = getattr(last_result, "items_failed", None)
            if result_status or items is not None:
                print(f"Last result: status={result_status}, processed={items}, failed={failed}")
        except Exception:
            pass
        break

    # Show indexed document count
    try:
        search_client = SearchClient(endpoint=endpoint, index_name=index_name, credential=AzureKeyCredential(key))
        count = search_client.get_document_count()
        print(f"Indexed documents in '{index_name}': {count}")
    except Exception:
        pass


if __name__ == "__main__":
    main()


