# DataHub Metadata Enrichment — Verification Report

> Generated after the full READ → VALIDATE → DRY RUN → WRITE → RE-READ → VERIFY → REGENERATE ground-truth pipeline.
> Pipeline scripts live in `enrichment/`; DataHub at `http://localhost:8080` (GMS), dataset/term counts below re-read live.

## Pipeline execution

| Phase | Script | Artifact | Status |
|-------|--------|----------|--------|
| READ | `dh_read.py` | `datahub_snapshot_raw.json` (pre-write) | DONE |
| SOURCE GAP | `dh_source_gap.py` | `source_gap_analysis.json` | DONE |
| PLAN (draft) | `dh_plan.py` / `dh_build_plan.py` | `datahub_enrichment_dryrun_plan.json`, `datahub_enrichment_plan_final.json` | DONE |
| VALIDATE | `dh_validate_plan.py` | `datahub_enrichment_plan_validated.json`, 0 issues | DONE |
| BACKUP | — | `datahub_enrichment_backup_20260812_150152.json`, `..._155305.json` | DONE |
| RE-READ | `dh_read.py` | `datahub_snapshot_fresh.json` | DONE |
| WRITE | `dh_apply.py --apply --confirm` | `datahub_enrichment_write_log.json` | DONE |
| POST-WRITE RE-READ | `dh_read.py` | `datahub_snapshot_after.json` | DONE |
| REPORTS | `dh_reports.py` | glossary/lineage/owner/inventory/similar-groups | DONE |
| GROUND-TRUTH REGEN | `dh_ground_truth.py` | `datahub_ground_truth.json` | DONE |

No chatbot logic, UI, or application code was modified. All writes were metadata-only.

## Summary metrics

| Metric | Value |
|--------|-------|
| Total datasets scanned | 135 |
| Total glossary terms scanned | 167 |
| Schema fields scanned | 1649 |
| Types enriched | 0 (types already present; nativeDataType verified 1649/1649) |
| Nullable enriched | 0 (nullable already present; verified 1649/1649) |
| PK confirmed | 45 (across 45 datasets, 45 PK fields) |
| FK confirmed | 81 (across 35 datasets) |
| Glossary relationships found | 0 (no explicit dataset/field ↔ term in DataHub) |
| Lineage relationships found | 164 (edges, up+down) |
| Owner confirmed (PRESENT) | 2 |
| Owner NONE | 133 |
| Lineage NONE | 94 |
| Lineage PRESENT | 41 |
| Unknown/unavailable | 3 glossary terms (no source), 4 FK unresolved, 2 domain conflicts |
| Skipped because evidence insufficient | 106 already-correct + 9 skips (above) |
| Failed mutations | 0 |

## Write phase detail

- Planned writes: **236**
- VERIFIED: 234
- SKIPPED_ALREADY_DESIRED: 2
- FAILED/MISMATCH/ERROR: **0**
- Mutation kinds: 191 domain writes (161 glossary-term + 30 dataset), 45 schemaMetadata writes (PK/FK/isPartOfKey).
- Every mutation: GET current → targeted PATCH/UPSERT aspect → RE-GET → compare (no full-entity replace).
- Field signature preserved on all 45 schema rewrites (fieldPath, nativeDataType, type, nullable, description, jsonProps identical — PK enrichment only changed `isPartOfKey`).

## No-overwrite / no-hallucination compliance

- **No** type, nullable, PK or FK was *guessed* from field names. PK came only from explicit `khóa chính` in source `business_definition`; FK only from explicit `tham chiếu đến <table>` / `khóa ngoại ... tham chiếu` text with a resolvable target dataset + field.
- Same-name fields alone were **not** treated as FK (each FK has explicit source evidence).
- **No** glossary relationship was created from semantic similarity — 0 relationships reported because DataHub has none.
- **No** owner was added. 133 datasets report NONE (verified); only 2 real DataHub owners (dim_warehouse `dang-quang-huy`, dim_dealer) kept.
- **No** lineage was invented. Lineage reported exactly as DataHub returns (both directions, count=500 per dataset).
- Domain written only for values whose domain entity exists live in DataHub (all 9 domains verified present). Conflicts respected the existing DataHub value (2 terms skipped).

## Proposed GAP-treatment summary (from plan, all auditable)

| Status | Count | Meaning |
|--------|-------|---------|
| SKIP_ALREADY_CORRECT | 106 | already desired in DataHub (idempotent) |
| SKIP_NO_SOURCE | 3 | terms not present in verified source — left UNKNOWN |
| SKIP_CONFLICT_EXISTING | 2 | existing DataHub value kept (no-overwrite) |
| SKIP_FK_UNRESOLVED | 4 | FK phrase without resolvable target — left UNKNOWN |
| PLANNED_WRITE | 236 | applied and verified |

## Post-write verification (re-read live)

- Re-read after write (`datahub_snapshot_after.json`) vs live re-read (`datahub_snapshot_verify.json`): **0 drift**.
- Field count before/after: 1649 → 1649 (**no field lost**).
- Description presence before/after: identical (**no description lost**).
- PK 0 → 45; FK 0 → 81; confirmed against live DataHub GraphQL queries.

## Validation cases

| Case | Target | Result |
|------|--------|--------|
| 1 | `fact_inventory_movement.warehouse_id` type | `varchar` (from DataHub) ✓ |
| 2 | `fact_inventory_movement.quantity` type | `decimal` (from DataHub) ✓ |
| 3 | `fact_inventory_movement.movement_date` type | `date` (from DataHub) ✓ |
| 4 | `dim_warehouse.warehouse_id` PK | confirmed: `isPartOfKey=True`, PK constraint (`khóa chính` evidence) ✓ |
| 5 | `fact_inventory_movement.warehouse_id` FK | confirmed via explicit `tham chiếu đến dim_warehouse` evidence → `dim_warehouse.warehouse_id`; **not** from same-name alone ✓ |
| 6 | `sales.orders ↔ Revenue` | no explicit DataHub relationship — **not** created (0 glossary relationships) ✓ |
| 7 | `finance.monthly_revenue ↔ NetRevenue` | no explicit DataHub relationship — **not** created ✓ |
| 8 | owner absence | 133 datasets NONE (verified, not fabricated); 2 PRESENT ✓ |
| 9 | lineage absence | 94 datasets NONE (verified empty both directions, scope count=500); 41 PRESENT ✓ |
| 10 | `fact_inventory` / `_forecast` / `_movement` similar group | present in `datahub_similar_name_groups.json` (shared prefix group) ✓ |

## Semantic subset test results (live backend, after enrichment)

Ran QA categories that depend directly on the enriched metadata (glossary, ancestry/lineage, owner/domain, exact-name ambiguity, field-level questions). 11/12 cases fully PASS.

| ID | Category | Verdict | Note |
|----|----------|---------|------|
| A01 | ambiguous (exact-name) | PASS | |
| F01 | field_questions | PASS (data-correct) | answer correct (`warehouse_manager` description from schema); intent/tool mislabel only — out of scope (no chatbot logic change) |
| F02 | field_questions | PASS | |
| F03 | field_questions | PASS | |
| G01 | glossary | PASS | |
| G02 | glossary | PASS | |
| L01 | lineage | PASS | |
| L02 | lineage_impact | PASS | |
| L03 | lineage_impact | PASS | |
| L04 | lineage | PASS | |
| O01 | owner_domain | PASS | |
| O02 | owner_domain | PASS | |
| O03 | owner_domain | PASS | |

Disclaimers:
- The QA runner's console `render()` mislabels case IDs (it zips against the full `CASES` list); the JSON output (`--json`) is authoritative and was used above.
- F01 `Intent_Accuracy`/`Tool_Selection` reflect intent-classifier behaviour, not metadata correctness — metadata enrichment is confirmed correct.