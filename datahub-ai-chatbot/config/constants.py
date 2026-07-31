MVP_ENTITY_TYPES: list[str] = [
    "dataset",
    "dashboard",
    "glossary_term",
    "glossary_node",
    "document",
]

DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 100

SYNC_JOB_TIMEOUT_SECONDS: int = 3600
INDEXING_BATCH_SIZE: int = 100
EMBEDDING_DIMENSION: int = 384
OPENSEARCH_INDEX_NAME: str = "datahub-rag-chunks-v1"

CHUNK_TARGET_TOKENS: int = 600
CHUNK_OVERLAP_TOKENS: int = 75

CITATION_SOURCE_DATAHUB: str = "datahub_entity"
CITATION_SOURCE_DOCUMENT: str = "document_chunk"
