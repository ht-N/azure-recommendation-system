import json
import os
import sys
from typing import List, Dict

from azure.cosmos import CosmosClient, PartitionKey, exceptions
from dotenv import load_dotenv, find_dotenv


def read_json_array(file_path: str) -> List[Dict]:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array in {file_path}")
    return data


def ensure_database(client: CosmosClient, database_name: str):
    try:
        return client.create_database_if_not_exists(id=database_name)
    except exceptions.CosmosHttpResponseError as e:
        raise RuntimeError(f"Failed to create/access database '{database_name}': {e}")


def ensure_container(database, container_id: str, partition_key_path: str):
    try:
        return database.create_container_if_not_exists(
            id=container_id,
            partition_key=PartitionKey(path=partition_key_path),
        )
    except exceptions.CosmosHttpResponseError as e:
        raise RuntimeError(f"Failed to create/access container '{container_id}': {e}")


def _strip_system_fields(item: Dict) -> Dict:
    # Remove Cosmos system properties before comparison
    sys_fields = {"_rid", "_self", "_etag", "_attachments", "_ts"}
    return {k: v for k, v in item.items() if k not in sys_fields}


def upsert_documents(container, documents: List[Dict], id_field: str = "id") -> int:
    upserted = 0
    for doc in documents:
        if id_field not in doc:
            raise ValueError("Document missing required 'id' field")
        if "app_id" not in doc:
            raise ValueError("Document missing required partition key field 'app_id'")

        # Try to fetch existing to detect changes
        try:
            existing = container.read_item(item=doc[id_field], partition_key=doc["app_id"])  # type: ignore[index]
            if _strip_system_fields(existing) == _strip_system_fields(doc):
                # No change, skip upsert
                continue
        except exceptions.CosmosResourceNotFoundError:
            # Not found → will create
            pass

        container.upsert_item(doc)
        upserted += 1
    return upserted


def main() -> None:
    load_dotenv(find_dotenv())

    endpoint = os.getenv("COSMOS_ENDPOINT")
    key = os.getenv("COSMOS_KEY")
    database_name = os.getenv("DATABASE_NAME")

    if not endpoint or not key or not database_name:
        print(
            "Missing required env: COSMOS_ENDPOINT, COSMOS_KEY, DATABASE_NAME.\n"
            "Add them to .env or env.txt.",
            file=sys.stderr,
        )
        sys.exit(1)

    # upload.py lives in azure/cosmosdb → go two levels up to repo root
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    articles_path = os.path.join(repo_root, "azure/data", "articles.json")
    users_path = os.path.join(repo_root, "azure/data", "users.json")

    if not os.path.exists(articles_path):
        print(f"Not found: {articles_path}", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(users_path):
        print(f"Not found: {users_path}", file=sys.stderr)
        sys.exit(1)

    articles = read_json_array(articles_path)
    users = read_json_array(users_path)

    client = CosmosClient(endpoint, key)
    database = ensure_database(client, database_name)

    # Containers
    articles_container = ensure_container(database, container_id="articles", partition_key_path="/app_id")
    users_container = ensure_container(database, container_id="users", partition_key_path="/app_id")

    total_articles = upsert_documents(articles_container, articles)
    total_users = upsert_documents(users_container, users)

    print(f"Upserted {total_articles} articles into container 'articles'.")
    print(f"Upserted {total_users} users into container 'users'.")


if __name__ == "__main__":
    main()


