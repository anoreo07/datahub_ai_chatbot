# Pipeline

## Sync Pipeline

1. Fetch entities from DataHub via GraphQL
2. Normalize entity data
3. Store in PostgreSQL
4. Update sync checkpoint

## Indexing Pipeline

1. Read entities from PostgreSQL
2. Chunk entity text
3. Generate embeddings
4. Store in OpenSearch (vector + keyword)
5. Update index job status

## Retrieval Pipeline

1. Classify query intent
2. Resolve entities
3. Hybrid search (vector + keyword)
4. Rerank results
5. Expand with graph relationships
6. Build context
7. Generate answer with citations
