# Generic Metadata Listing Engine — Improvement Report

## Problem
The chatbot couldn't handle generic metadata queries like:
- "dataset nào có lineage?" → which datasets have lineage?
- "dataset nào không có owner?" → which datasets are missing owners?
- "dataset nào thuộc domain SALES?" → which datasets are in SALES domain?

These were routed to entity lookup or clarification instead of structured metadata filtering.

## Solution Architecture

### Three Components

1. **`retrieval/metadata_query.py`** — Data contract + AttributeRegistry
   - `GenericMetadataQuery`: entity_type, filters, limit, offset
   - `MetadataFilter`: attribute + operation (EXISTS/MISSING/EQUALS/NOT_EQUALS/CONTAINS)
   - `AttributeRegistry`: 11 attributes (owner, lineage, domain, description, tags, glossary, schema, platform, environment, documentation, deprecation) with synonyms, SQL columns, JSON paths, and existence checks
   - Adding a new attribute = add one entry to the registry. No code changes elsewhere.

2. **`retrieval/metadata_query_parser.py`** — NLP → structured query
   - `parse_metadata_query()`: parses Vietnamese/English natural language into `GenericMetadataQuery`
   - Handles EXISTS, MISSING, EQUALS operations
   - Multi-filter support ("có lineage và owner?")
   - Typo normalization via attribute registry
   - False positive prevention: entity-specific queries, glossary entity type overlap, domain count queries

3. **`retrieval/metadata_filter_engine.py`** — structured query → PostgreSQL
   - `MetadataFilterEngine.execute()`: builds SQL with JSON checks for payload fields
   - SQL-level filtering for indexed columns (domain, platform, environment)
   - JSON-level filtering for payload fields (owners, tags, lineage, schema, etc.)
   - RBAC filtering integration
   - `MetadataQueryResult`: answer text generation, citation building

### Integration Point

`app/services/chat_service.py` — `_try_metadata_listing()` method:
- Inserted before the existing `_detect_listing()` call (line ~1565)
- Gated by `intent not in _DETERMINISTIC_LISTING_INTENTS` to avoid interfering with existing flows
- Returns `ChatResponse` with intent="METADATA_LISTING"

## Test Coverage

91 tests in `tests/unit/test_metadata_listing_engine.py`:

| Category | Count | Description |
|----------|-------|-------------|
| AttributeRegistry | 3 | Registry completeness, synonyms, entity types |
| normalize_attribute | 4 | Exact, Vietnamese, ASCII, fuzzy matching |
| Edit distance | 3 | Identical, one edit, different lengths |
| Parser positive | 18 | EXISTS/MISSING/EQUALS, multi-filter, limit, entity types, Vietnamese |
| Parser negative | 10 | Entity-specific, existence, pure listing, term-to-datasets, domain count |
| Entity type detection | 5 | dataset, dashboard, glossary, document, default |
| Operation detection | 4 | EXISTS, MISSING, thieu, EQUALS |
| Limit extraction | 3 | Number, no number, capped |
| SQL generation | 6 | EXISTS/MISSING/EQUALS for owner, domain, lineage, unknown |
| JSON checks | 5 | not_null, array, missing, lineage_edges |
| Result tests | 3 | to_dict, filter descriptions |
| Integration (parametrized) | 26 | 18 required queries + 8 negative queries |

## Supported Query Patterns

### EXISTS (có/dang có)
```
dataset nào có lineage?
dataset nào có linage?          # typo normalized
dataset nào có schema?
dataset nào có tags?
dataset nào có glossary?
dataset nào có business term?   # Vietnamese synonym
dataset nào có data flow?       # Vietnamese synonym
```

### MISSING (không có/thiếu/chưa có)
```
dataset nào không có owner?
dataset nào thiếu description?
dataset nào chưa có owner?
```

### EQUALS (thuộc/trên)
```
dataset nào thuộc domain SALES?
dataset nào trên platform powerbi?
```

### Multi-filter
```
dataset nào có lineage và owner?
```

### Count
```
có bao nhiêu dataset có owner?
```

### Limit
```
liệt kê 10 datasets có schema
list 20 datasets có tags
```

## False Positive Prevention

The parser correctly rejects:
- `Dataset sales.orders có những field nào?` → entity-specific SCHEMA_LOOKUP
- `Dataset abc.xyz có tồn tại không?` → entity existence check
- `Có những glossary terms nào?` → pure listing (glossary entity type overlap)
- `Dataset nào gắn term Customer?` → TERM_TO_DATASETS
- `Lĩnh vực tài chính có bao nhiêu datasets?` → domain count (COUNT_ENTITIES)
- `Có những dataset nào?` → pure listing
- `Có những document nào trong hệ thống?` → pure listing

## Files Changed/Created

| File | Action | Description |
|------|--------|-------------|
| `retrieval/metadata_query.py` | Created | Data contract, AttributeRegistry |
| `retrieval/metadata_query_parser.py` | Created | NLP parser |
| `retrieval/metadata_filter_engine.py` | Created | SQL filter engine |
| `app/services/chat_service.py` | Modified | Added `_try_metadata_listing()`, import, integration |
| `tests/unit/test_metadata_listing_engine.py` | Created | 91 tests |

## Performance

- Parser: O(1) per query (regex + dictionary lookup)
- Filter engine: SQL WHERE with JSON checks, NOT full catalog scan
- For 8,500+ datasets: `WHERE entity_type='dataset'` + JSON checks
- Limit default: 10 (configurable, capped at 100)
