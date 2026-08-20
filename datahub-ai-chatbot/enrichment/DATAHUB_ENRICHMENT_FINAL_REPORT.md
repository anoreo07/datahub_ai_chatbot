# DataHub Metadata Enrichment — Final Report

> Pipeline: READ → VALIDATE → DRY RUN → WRITE → RE-READ → VERIFY → REGENERATE GROUND-TRUTH.
> Scope: metadata-only enrichment on DataHub (DataAtlas). No chatbot logic, no UI, no app-code refactor.

## 1. DataHub API / query used (READ)

- `http://localhost:8080/api/graphql` (GMS GraphQL), direct `httpx`.
- `scrollAcrossEntities` — 135 datasets + 167 glossary terms (canonical URNs, scroll pagination).
- `dataset{lineage}` (UPSTREAM / DOWNSTREAM, count=500) per dataset.
- `dataset` / `glossaryTerm` entity queries with `domain`, `schemaMetadata` (fields + nativeDataType + nullable + PK + FK), `ownership`, `glossaryTerms`, `tags`.
- Reader: `enrichment/dh_read.py`.

## 2. DataHub mutation used (WRITE)

- `datahub` MCP emitter (`DatahubRestEmitter` → GMS), targeted aspect UPSERT (no full-entity replace):
  - `DomainsClass` for glossary-term and dataset domains.
  - `SchemaMetadataClass` for PK / FK / `isPartOfKey` (fields rebuilt preserving all original metadata).
- Writer: `enrichment/dh_apply.py` (per-mutation GET → PATCH → RE-GET → compare).

## 3–4. Datasets / fields scanned

- Datasets scanned: **135**
- Schema fields scanned: **1649**
- Metadata derived strictly from source of truth (DataHub + verified `mock-data` yaml); nothing guessed from names.

## 5–6. Fields with real type / nullable

- Fields with `nativeDataType` (real type): **1649 / 1649** (100% — types were already present; verified unchanged).
- Fields with `nullable` known: **1649 / 1649** — nullable was already present in DataHub; **none guessed**.
  - No type/nullable was overwritten; no fabricated conversion (e.g. `VARCHAR`→integer never happened).

## 7. PK confirmed directly

- **45 PK** across **45 datasets** — written from explicit `khóa chính` evidence in the verified source `business_definition`, all present in the source-of-truth metadata. 0 before → 45 after.
- No PK inferred from `*_id` name alone.

## 8. FK confirmed directly

- **81 FK** constraints across **35 datasets** — each from explicit `tham chiếu đến <table>` / `khóa ngoại … tham chiếu` evidence with a resolvable target dataset + field. 0 before → 81 after.
- Same-name alone never treated as FK. 4 ambiguous FK phrases with unresolvable targets were skipped (`SKIP_FK_UNRESOLVED`) → reported as FK-ref UNKNOWN, not guessed.

## 9. Glossary relationships (dataset ↔ term)

- **0** explicit relationships in DataHub (no `dataset.glossaryTerms`, no `field.glossaryTerms`).
- No semantic-similarity linkage created (CASE 6/7: `sales.orders ↔ Revenue`, `finance.monthly_revenue ↔ NetRevenue` → correctly NOT created).
- Report: `enrichment/datahub_glossary_relationship_enrichment.json`.

## 10. Glossary domains

- Domain entities verified live in DataHub (all 9 domains exist: CUNG ỨNG NĐH/TT, HẬU MÃI, KINH DOANH, LOGISTIC, PHÁT TRIỂN XE, SẢN XUẤT, TÀI CHÍNH, VGreen).
- Glossary terms with domain: **164 / 167**. Remaining 3 (`AccountBalance`, `CustomerAccount`, `SavingAccount`) have no source metadata → left **UNKNOWN**, not fabricated.
- 2 terms with conflicting source-vs-DataHub domains kept the existing DataHub value (no-overwrite).
- DataHub GraphQL supports `GlossaryTerm.domain` — confirmed.

## 11. Lineage

- **41 datasets** have lineage (PRESENT), **94 datasets** NONE — read from DataHub both directions (count=500); verified query scope so "none" is real, not an empty-response artifact.
- Total lineage edges: **164**.
- Report: `enrichment/datahub_lineage_enrichment_report.json`.

## 12. Owner

- Owner PRESENT: **2** (dim_warehouse → `dang-quang-huy`; dim_dealer → DataHub owner).
- Owner NONE: **133** (verified absent in DataHub; not fabricated).
- No `budget_owner` / `created_by` / `warehouse_manager` ever treated as dataset owner.
- Report: `enrichment/datahub_owner_enrichment_report.json`.

## 13. Similar-name groups (deterministic)

- **23 groups** from a deterministic prefix/token/cross-namespace algorithm (no LLM).
- CASE 10 confirmed: `fact_inventory`, `fact_inventory_forecast`, `fact_inventory_movement` in the same group (`token_inventory`, + `dim_inventory_category`).
- Artifact: `enrichment/datahub_similar_name_groups.json`.

## 14. Exact entity inventory

- **135 datasets + 167 glossary terms**, canonical URNs, platform `redshift`, environment `PROD`, with domain/description/owner/schema/glossary/lineage.
- Artifact: `enrichment/datahub_exact_entity_inventory.json`.

## 15–16. Write strategy / idempotency

- Targeted aspect UPSERT only (no whole-entity overwrite).
- Per-mutation: GET current → SKIP if already desired → WRITE → RE-GET → compare.
- Write log: **236 mutations = 234 VERIFIED + 2 SKIPPED_ALREADY_DESIRED, 0 FAILED**.
- Field signature preserved on all 45 schema rewrites; description / tags / glossary / lineage / ownership untouched (verified 135/135 descriptions present before and after).
- Re-run safe: current == desired → skip.

## 17. LLM usage

- **No LLM** used to decide PK/FK/datatype/nullable/owner/lineage/glossary linkage. All values from DataHub or verified source text (deterministic). LLM was not consulted for any factual metadata decision.

## 18. Validation cases (all pass)

| Case | Result |
|------|--------|
| warehouse_id type | `varchar` (from DataHub) |
| quantity type | `decimal` (from DataHub) |
| movement_date type | `date` (from DataHub) |
| dim_warehouse.warehouse_id PK | confirmed (explicit evidence) |
| fact_inventory_movement.warehouse_id FK | confirmed → dim_warehouse.warehouse_id (explicit evidence) |
| sales.orders ↔ Revenue | not created (no evidence) |
| finance.monthly_revenue ↔ NetRevenue | not created (no evidence) |
| owner absence | NONE (133) vs PRESENT (2), never fabricated |
| lineage absence | NONE (94) vs PRESENT (41), verified scope |
| inventory similar-name group | present in `datahub_similar_name_groups.json` |

## 19–20. Post-write verification + ground-truth regeneration

- Re-read after write, drift vs live = **0**.
- `enrichment/datahub_enrichment_verification.md` (stats table, pipeline log, validation cases).
- Ground-truth regenerated from DataHub (no manual editing): `enrichment/datahub_ground_truth.json` (135 datasets, 167 glossary terms, 23 similar-name groups).

## 21. Subset semantic tests (live backend, post-enrichment)

- Selected QA categories depending directly on enriched metadata (field_questions, glossary, lineage, owner_domain, ambiguous): **11/12 full PASS**; F01 answer is data-correct, differing only on intent/tool classification (out of scope — no chatbot-logic changes).
- NOTE: the QA runner's console render mislabels case IDs; JSON (`--json`) output is authoritative.

## 22. Final tally

1. DataHub API: GraphQL `scrollAcrossEntities`, entity/lineage queries → `dh_read.py`.
2. DataHub mutation: MCP aspect UPSERT (`DomainsClass`, `SchemaMetadataClass`) → `dh_apply.py`.
3. Datasets scanned: **135**.
4. Fields scanned: **1649**.
5. Fields with real type: **1649**.
6. Fields with real nullable: **1649**.
7. PK confirmed directly: **45**.
8. FK confirmed directly: **81**.
9. Glossary relationships: **0** (none exist).
10. Lineage relationships: **164 edges** (41 datasets).
11. Datasets with owner: **2**.
12. Datasets with owner NONE (verified): **133**.
13. Lineage NONE (real, verified): **94**.
14. Still UNKNOWN (insufficient evidence): 3 glossary terms without domain; 4 unresolved FK references; 2 domain conflicts left to DataHub's existing value.
15. Similar-name groups: **23**.
16. Mutations: **234 SUCCESS / 2 SKIPPED / 0 FAILED**.
17. Metadata overwritten: **none** — 2 conflicting domains kept the existing DataHub value; no type/nullable/owner/lineage/glossary overwritten.
18. Regression / lost metadata: **none** (1649→1649 fields, 135/135 descriptions, field signatures preserved, drift 0).
19. Enriched entities (key examples):
   - `urn:li:dataset:(urn:li:dataPlatform:redshift,fact_inventory_movement,PROD)` — PK `movement_id`, FK `material_code→dim_material`, `warehouse_id→dim_warehouse`, domain `urn:li:domain:logistic`.
   - `urn:li:dataset:(urn:li:dataPlatform:redshift,dim_warehouse,PROD)` — PK `warehouse_id`, domain `urn:li:domain:logistic`.
   - `urn:li:glossaryTerm:andon` — domain `urn:li:domain:snxut`.
   All 45 schema + 191 domain entity URNs logged in `enrichment/datahub_enrichment_write_log.json`.
20. Verification after GET: drift 0, writes live, ground-truth regenerated and re-verified.

**Final verdict:** enrichment is complete and non-destructive. Remaining UNKNOWNs were deliberately left unresolved rather than fabricated — DataHub is now a trustworthy ground-truth for the semantic test suite.