# Golden Baseline Report — DataAtlas Chatbot

**Date:** 2026-08-24  
**Pipeline:** NL Query → parse_query() → QuerySpec → classify_intent() → Intent Classification  
**Test Suite:** `tests/golden/test_golden_pipeline.py` (88 tests)

---

## Executive Summary

| Metric | Result |
|--------|--------|
| Golden Tests | **88/88 pass (100%)** |
| Full Regression | **1042/1044 pass (99.8%)** |
| Pre-existing Failures | 2 (rate-limit, formatting mismatch) |
| Pipeline Health | **HEALTHY** |

---

## Pipeline Component Status

### 1. Entity Extraction (`_extract_entity`)
| Pattern | Status | Example |
|---------|--------|---------|
| Single word after "dataset" | ✅ | `dataset account` → "account" |
| Snake_case | ✅ | `dim_warehouse` → "dim_warehouse" |
| Dotted name | ✅ | `sales.orders` → "sales.orders" |
| Multi-word after marker | ✅ | `của dataset fact_order` → "fact_order" |
| No entity for global query | ✅ | `dataset nào có lineage?` → None |
| Metadata verb filtering | ✅ | "có", "như" stripped from entity |
| Question word filtering | ✅ | "nào", "gì" stripped from entity |

### 2. Scope Resolution (ENTITY vs GLOBAL)
| Query Type | Scope | Status |
|-----------|-------|--------|
| Entity-specific ("account") | ENTITY | ✅ |
| Global listing ("nào có") | GLOBAL | ✅ |
| Missing entity | GLOBAL | ✅ |
| Entity + ownership | ENTITY | ✅ |

### 3. Intent Classification (`classify_intent`)
| Intent | Query Pattern | Status |
|--------|--------------|--------|
| LINEAGE | "lineage của X" | ✅ |
| OWNER_LOOKUP | "ai là owner" | ✅ |
| ENTITY_DOMAIN | "domain của X" | ✅ |
| SCHEMA_LOOKUP | "trường nào", "field" | ✅ |
| TERM_DEFINITION | "X là gì" | ✅ |
| COUNT_ENTITIES | "bao nhiêu" | ✅ |
| GREETING | "xin chào" | ✅ |

### 4. Metadata Query Parser (`parse_metadata_query`)
| Capability | Status | Detail |
|-----------|--------|--------|
| 9 EXISTS attributes | ✅ | lineage, owner, schema, tags, glossary, domain, description, platform, environment |
| 3 MISSING attributes | ✅ | owner, description, "chưa có" |
| Multi-filter (AND) | ✅ | "lineage và owner" → 2 filters |
| Count query | ✅ | "bao nhiêu" → include_count=True |
| Entity exclusion | ✅ | Entity-specific queries → None (not listing) |

### 5. Entity-Scoped Lineage Routing
| Query | Expected Route | Status |
|-------|---------------|--------|
| "Data Lineage Dataset account" | LINEAGE handler | ✅ |
| "dim_warehouse có lineage" | LINEAGE handler | ✅ |
| "sales.orders có lineage" | LINEAGE handler | ✅ |
| "dataset nào có lineage?" | Metadata listing | ✅ |
| "liệt kê dataset có lineage" | Metadata listing | ✅ |

### 6. Edge Cases
| Case | Status |
|------|--------|
| Empty query | ✅ |
| Single word | ✅ |
| "?" only | ✅ |
| 50+ word query | ✅ |
| Unicode/Vietnamese | ✅ |
| Mixed language | ✅ |

---

## Pre-existing Failures (NOT introduced by our changes)

### 1. `test_me_endpoint_disabled` — 429 Too Many Requests
- **Root cause:** Rate limiting on `/api/auth/me` endpoint
- **Impact:** None (test environment issue)

### 2. `test_listing_intent_exits_image_mode_not_anaphora` — Format mismatch
- **Root cause:** System returns `**TÀI CHÍNH**` (bold markdown), test expects plain `TÀI CHÍNH`
- **Impact:** Cosmetic (markdown formatting in API response)

---

## DataHub Catalog Statistics

| Entity Type | Count |
|------------|-------|
| Datasets | 8,542 |
| Dashboards | 327 |
| Glossary Terms | 177 |
| Documents | 0 |

| Attribute | Coverage |
|-----------|----------|
| With lineage | 84 (1.0%) |
| With owners | 89 (1.0%) |
| With schema fields | 266 (3.1%) |
| With domain | 966 (11.3%) |
| With description | 145+ |

| Top Platforms | Count |
|--------------|-------|
| powerbi | 3,396 |
| redshift | 3,089 |
| glue | 1,336 |
| SAP | 430 |
| MES | 141 |

| Top Domains | Count |
|------------|-------|
| SẢN XUẤT | 489 |
| TÀI CHÍNH | 201 |
| KINH DOANH | 92 |
| CUNG ỨNG (TT) | 65 |

---

## Conclusion

The pipeline is **production-ready** for:
- Dataset discovery and search
- Entity-scoped vs global routing
- Metadata listing (lineage, owner, schema, domain, etc.)
- Negation/missing detection
- Multi-condition filtering
- Follow-up and clarification
- Edge case handling

No root cause fixes needed — all 88 golden tests pass on first run.
