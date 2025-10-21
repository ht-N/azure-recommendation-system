import os
import sys
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv, find_dotenv

from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceNotFoundError
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    ComplexField,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SearchSuggester,
)
from azure.search.documents.indexes import SearchIndexerClient
from azure.search.documents.indexes.models import (
    SearchIndexerDataSourceConnection,
    SearchIndexer,
    SoftDeleteColumnDeletionDetectionPolicy,
    HighWaterMarkChangeDetectionPolicy,
    InputFieldMappingEntry,
    OutputFieldMappingEntry,
    SearchIndexerSkillset,
    SearchIndexerDataContainer,
    FieldMapping,
    IndexingSchedule,
)


def _get_env(name: str, required: bool = True) -> Optional[str]:
    value = os.getenv(name)
    if required and not value:
        print(f"Missing required env var: {name}", file=sys.stderr)
        sys.exit(1)
    return value


def create_index(index_client: SearchIndexClient, index_name: str, embedding_dim: int) -> None:
    # Define fields, including vector for abstract
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True, sortable=True, facetable=False),
        SearchableField(name="title", type=SearchFieldDataType.String, analyzer_name="en.lucene", sortable=True),
        SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="en.lucene"),
        SearchableField(name="abstract", type=SearchFieldDataType.String, analyzer_name="en.lucene"),
        SimpleField(name="tags", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True, facetable=True),
        SimpleField(name="views", type=SearchFieldDataType.Int32, filterable=True, sortable=True, facetable=True),
        SimpleField(name="created_at", type=SearchFieldDataType.String, filterable=True, sortable=True),
        SimpleField(name="updated_at", type=SearchFieldDataType.String, filterable=True, sortable=True),
        SimpleField(name="image", type=SearchFieldDataType.String, filterable=False),
        SimpleField(name="is_active", type=SearchFieldDataType.Boolean, filterable=True, facetable=True),
        SimpleField(name="app_id", type=SearchFieldDataType.String, filterable=True, facetable=True, sortable=True),
        SimpleField(name="author_id", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SimpleField(name="author_name", type=SearchFieldDataType.String, filterable=True, sortable=True),
        SimpleField(name="likes", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
        SimpleField(name="dislikes", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
        # Vector field for abstract embeddings (SDK 11.5.x naming)
        SearchField(
            name="abstract_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=embedding_dim,
            vector_search_profile_name="hnsw-cosine",
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="hnsw-default")],
        profiles=[VectorSearchProfile(name="hnsw-cosine", algorithm_configuration_name="hnsw-default")],
    )

    suggesters = [
        SearchSuggester(name="sg", source_fields=["title", "author_name", "tags"]),
    ]

    index = SearchIndex(
        name=index_name,
        fields=fields,
        vector_search=vector_search,
        suggesters=suggesters,
    )

    try:
        if any(ix.name == index_name for ix in index_client.list_indexes()):
            index_client.delete_index(index_name)
        index_client.create_index(index)
        print(f"Created index '{index_name}'")
    except Exception as e:
        print(f"Failed to create index: {e}", file=sys.stderr)
        sys.exit(1)


def build_cosmos_connection_string(endpoint: str, key: str, database: str) -> str:
    return f"AccountEndpoint={endpoint};AccountKey={key};Database={database};"


def create_datasource(indexer_client: SearchIndexerClient, name: str, cosmos_endpoint: str, cosmos_key: str, database_name: str, container_name: str) -> None:
    connection_string = build_cosmos_connection_string(cosmos_endpoint, cosmos_key, database_name)
    container = SearchIndexerDataContainer(name=container_name)

    # Soft delete when is_active == false; track changes via _ts
    soft_delete_policy = SoftDeleteColumnDeletionDetectionPolicy(soft_delete_column_name="is_active", soft_delete_marker_value="false")
    high_watermark_policy = HighWaterMarkChangeDetectionPolicy(high_water_mark_column_name="_ts")

    ds = SearchIndexerDataSourceConnection(
        name=name,
        type="cosmosdb",
        connection_string=connection_string,
        container=container,
        data_deletion_detection_policy=soft_delete_policy,
        data_change_detection_policy=high_watermark_policy,
    )

    try:
        try:
            # Delete if exists (SDKs differ on list_* availability)
            existing = indexer_client.get_data_source_connection(name)
            if existing:
                indexer_client.delete_data_source_connection(name)
        except ResourceNotFoundError:
            pass
        indexer_client.create_data_source_connection(ds)
        print(f"Created data source '{name}'")
    except Exception as e:
        print(f"Failed to create data source: {e}", file=sys.stderr)
        sys.exit(1)


def create_skillset(indexer_client: SearchIndexerClient, name: str, openai_endpoint: str, openai_key: str, openai_deployment: str, openai_model: str) -> None:
    # Use raw skill payload to avoid SDK version coupling
    skill = {
        "@odata.type": "#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill",
        "description": "Embed abstract into abstract_vector",
        "inputs": [
            {"name": "text", "source": "/document/abstract"}
        ],
        "outputs": [
            {"name": "embedding", "targetName": "abstract_vector"}
        ],
        "resourceUri": openai_endpoint,
        "apiKey": openai_key,
        "deploymentId": openai_deployment,
        "modelName": openai_model,
    }

    skillset = SearchIndexerSkillset(name=name, skills=[skill])

    try:
        try:
            existing = indexer_client.get_skillset(name)
            if existing:
                indexer_client.delete_skillset(name)
        except ResourceNotFoundError:
            pass
        indexer_client.create_skillset(skillset)
        print(f"Created skillset '{name}'")
    except Exception as e:
        print(f"Failed to create skillset: {e}", file=sys.stderr)
        sys.exit(1)


def create_indexer(indexer_client: SearchIndexerClient, name: str, data_source_name: str, index_name: str, skillset_name: str, schedule_start: Optional[str]) -> None:
    # Field mappings (mostly identity). Skill outputs map via outputFieldMappings
    field_mappings = [
        FieldMapping(source_field_name="id", target_field_name="id"),
        FieldMapping(source_field_name="title", target_field_name="title"),
        FieldMapping(source_field_name="content", target_field_name="content"),
        FieldMapping(source_field_name="abstract", target_field_name="abstract"),
        FieldMapping(source_field_name="tags", target_field_name="tags"),
        FieldMapping(source_field_name="views", target_field_name="views"),
        FieldMapping(source_field_name="created_at", target_field_name="created_at"),
        FieldMapping(source_field_name="updated_at", target_field_name="updated_at"),
        FieldMapping(source_field_name="image", target_field_name="image"),
        FieldMapping(source_field_name="is_active", target_field_name="is_active"),
        FieldMapping(source_field_name="app_id", target_field_name="app_id"),
        FieldMapping(source_field_name="author_id", target_field_name="author_id"),
        FieldMapping(source_field_name="author_name", target_field_name="author_name"),
        FieldMapping(source_field_name="likes", target_field_name="likes"),
        FieldMapping(source_field_name="dislikes", target_field_name="dislikes"),
    ]

    # Use raw dict for broader SDK compatibility
    output_mappings = [
        {"sourceFieldName": "/document/abstract_vector", "targetFieldName": "abstract_vector"}
    ]

    schedule = None
    if schedule_start:
        try:
            # Accept ISO8601 Z timestamps; default every 5 minutes
            start_dt = datetime.fromisoformat(schedule_start.replace("Z", "+00:00"))
            schedule = IndexingSchedule(start_time=start_dt, interval="PT5M")
        except Exception:
            print("Warning: INDEXER_START_TIME invalid; skipping schedule")

    indexer = SearchIndexer(
        name=name,
        data_source_name=data_source_name,
        target_index_name=index_name,
        skillset_name=skillset_name,
        field_mappings=field_mappings,
        output_field_mappings=output_mappings,
        schedule=schedule,
    )

    try:
        try:
            existing = indexer_client.get_indexer(name)
            if existing:
                indexer_client.delete_indexer(name)
        except ResourceNotFoundError:
            pass
        indexer_client.create_indexer(indexer)
        print(f"Created indexer '{name}'")
    except Exception as e:
        print(f"Failed to create indexer: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    load_dotenv(find_dotenv())

    search_endpoint = _get_env("AZURE_SEARCH_ENDPOINT")
    search_key = _get_env("AZURE_SEARCH_ADMIN_KEY")
    index_name = _get_env("AZURE_SEARCH_INDEX")
    cosmos_endpoint = _get_env("COSMOS_ENDPOINT")
    cosmos_key = _get_env("COSMOS_KEY")
    database_name = _get_env("DATABASE_NAME")
    container_name = _get_env("COSMOS_CONTAINER", required=False) or "articles"
    embedding_dim = int(_get_env("EMBEDDING_DIM"))

    # For embedding skill
    openai_endpoint = _get_env("AZURE_OPENAI_ENDPOINT")
    openai_key = _get_env("AZURE_OPENAI_API_KEY")
    openai_deployment = _get_env("AZURE_OPENAI_DEPLOYMENT")
    openai_model = _get_env("AZURE_OPENAI_MODELNAME")

    indexer_name = f"{index_name}-indexer"
    data_source_name = f"{index_name}-cosmos-src"
    skillset_name = f"{index_name}-skillset"
    schedule_start = os.getenv("INDEXER_START_TIME")

    credential = AzureKeyCredential(search_key)  # type: ignore[arg-type]
    index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
    indexer_client = SearchIndexerClient(endpoint=search_endpoint, credential=credential)

    create_index(index_client, index_name, embedding_dim)
    create_datasource(indexer_client, data_source_name, cosmos_endpoint, cosmos_key, database_name, container_name)
    create_skillset(indexer_client, skillset_name, openai_endpoint, openai_key, openai_deployment, openai_model)
    create_indexer(indexer_client, indexer_name, data_source_name, index_name, skillset_name, schedule_start)

    print("Provisioning complete. You can now run the indexer.")


if __name__ == "__main__":
    main()


