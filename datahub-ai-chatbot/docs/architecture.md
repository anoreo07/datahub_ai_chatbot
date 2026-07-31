# Architecture

DataHub AI Chatbot is a RAG-based chatbot that indexes DataHub entities
and provides natural language query capabilities.

## High-level flow

1. **Ingestion**: Sync entities from DataHub via GraphQL API
2. **Indexing**: Chunk, embed, and store entities in vector store + keyword index
3. **Retrieval**: Classify intent, resolve entities, hybrid search, rerank, expand
4. **Generation**: Build context, call LLM, return answer with citations

## Components

- FastAPI application with async endpoints
- Background workers for sync and indexing
- PostgreSQL for metadata and job tracking
- Redis for cache and message queue
- OpenSearch for vector and keyword search
