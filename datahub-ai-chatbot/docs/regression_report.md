# Regression Test Report

| Item | Value |
|---|---|
| Generated | 2026-08-12 |
| Total test cases | 85 |
| Total turns | 120 |
| Errors | 0 |
| Multi-turn conversations kept context | 85 |

## Result

**PASS** — all 85 cases completed. Rate-limit fix and the `dataset_terms_flow` `UnboundLocalError` fix verified.

## Intent coverage

| Intent | Count |
|---|---|
| SCHEMA_LOOKUP | 31 |
| LINEAGE | 14 |
| TERM_DEFINITION | 6 |
| GENERAL | 6 |
| TERM_TO_DATASETS | 6 |
| CONTEXT_FIELD_TYPE | 5 |
| OWNER_LOOKUP | 4 |
| CONTEXT_FIELD_FIND | 2 |
| TERMS_FOR_ENTITY | 2 |
| ENTITY_DOMAIN | 1 |
| ENTITY_EXISTS | 1 |
| CONTEXT_FIELD_DESCRIPTION | 1 |
| DOMAIN_QUERY | 1 |
| CONTEXT_JOIN | 1 |
| CONTEXT_LINEAGE | 1 |
| IMPACT | 1 |
| FIND_ENTITY | 1 |
| CHITCHAT | 1 |


## Notes

- Ran against `/api/v1/chat` on localhost:8000.
- Source results: `/tmp/regression_results.json`.