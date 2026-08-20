# ROLLING FIX BASELINE — Phase 0

Baseline snapshot before the P0→P2 implementation cycle. Captured 2026-08-20 against the
DataAtlas backend running the latest committed-round code (backend9, health `/health` = ok).

## 1. Corpus / runtime facts (verified this phase)

- Runtime: real mode; LLM = Fireworks `deepseek-v4-flash-0731`; `QU_ENABLED=False` →
  `understanding` is `None`; `THINKING_MODE_ENABLED=True`, `INTENT_CLASSIFIER_ENABLED=True`,
  `QUERY_PLANNER_ENABLED=True`; trust threshold 0.85 (`settings.ENTITY_RESOLVER_TRUST_THRESHOLD`).
- DB `postgresql+asyncpg://postgres:postgres@localhost:5433/chatbot`: **9067 entities** =
  8542 datasets, 327 dashboards, 177 glossary_terms, 21 glossary_nodes, 0 documents.
- 7838 datasets lack description; 7581/8542 (88.8%) lack domain. chart/container/data_flow/
  data_platform/corp_user/domain/tag/corp_group pulled to `datahub_pull/` but NOT loaded to DB/index.

## 2. Research claims verified against code (file:line)

| Claim | Verdict | Evidence |
|---|---|---|
| Entity resolution has an ambiguity gate prone to false-positives across types (RC1a) | **CONFIRMED** | `retrieval/entity_resolver.py:106-116` — ambiguity if top1-top2 gap < 0.2 AND runner-up ≥ 0.7; **no entity-type check**, so a runner-up of a different type can force a clarification |
| Domain does NOT propagate from question into entity resolution | **CONFIRMED** | `EntityResolver.resolve(name, entity_type)` has no domain param (`entity_resolver.py:36-37`); `EntityRepository.search_by_name` filters by entity_type only (`entity_repository.py:50-65`); all 52 `resolve()` call sites pass only name/type/trace_id. Domain is used only for RBAC gating (`chat_service.py:754`), post-retrieval filter (`chat_service.py:1896`), and `list_by_domain` listings (`structured_retrieval.py:638`, `listing.py:177`) |
| Entity-type is mostly enforced in structured retrieval | **CONFIRMED** | `resolve_dataset` (`action_service.py:255`) and `structured_retrieval.py` pass `entity_type` into resolver at lines 143/167/206/213/230/299/339/454/472/604/816/847/1094; **exception**: `structured_retrieval.py:604` uses `entity_type="dataset"` but the generic `resolve_entity` path (`retrieval/tools.py`) and `try_explicit_entity_lookup` (`entity_resolution.py:97-132`) only enforce "dataset" |
| Thinking gate exists, gates GENERAL intent, threshold score ≥ 3 | **CONFIRMED** | `chat_service.py:1265-1276`; `retrieval/thinking/complexity.py:180` (`complex = score >= 3`); THINKING_OVERVIEW response carries NO citations (`chat_service.py:1309-1314`) |
| Planner returns SearchResults, not citations | **CONFIRMED** | `retrieval/planner_executor.py:100-121`; citations built later by generator (`llm/generator.py:94-98`) |
| Citations attached only to generative RAG + lineage paths | **CONFIRMED** | attached at `chat_service.py:2646`; deterministic branches set `citations=[]` (lines 2132/2256/2277/2308/2342/2383/2453/2492/2566); Thinking path returns none |
| Report/document discovery partial: CASE2 resolves report entities but hits ambiguity gate | **CONFIRMED** | `retrieval/discovery.py` TokenDiscovery (synonym table `discovery.py:37-85`, score `score_entity:131-146`, dedup by name `:190-201`) merged in hybrid search `hybrid_search.py:175-204`; dashboards indexed but 0 documents in DB |
| Same-name entities across platforms tie at score 1.0 and trigger clarify | **CONFIRMED** | `entity_resolver.py:103-116` (no tie-breaking beyond first candidate); `resolve_all_exact_to_results` (`entity_resolution.py:348-389`) surfaces all ties only for glossary terms, not datasets |
| Lineage/relationship data largely absent from payloads | **CONFIRMED** (prior audit) | 0 upstreams/downstreams verified on several fact tables; document entities = 0 → P2 relationship layer gated on data availability |

## 3. Baseline numbers (recorded this phase)

| Suite | Result |
|---|---|
| `pytest tests` | **622 passed** (187s) |
| `audit/harness26.py` (26-case focused harness) | **26/26 PASS** |
| Golden regression strict tool (`/tmp/opencode/regression_golden.py`) | **37/48 PASS** |
| Ruff on touched-core files | 11 pre-existing errors (E501 line-lengths, I001 unused imports, N806 `EXACT` entity_resolution.py:359, F841 `named` chat_service.py:431) — no new issues from last round |
| Backend health | `/health` ok (pid 3639230, backend9.log) |

### Golden regression remaining strict fails (37/48 → 11 fails)

- Artifact / name-form (grounded but normalized differently): **G-001/002/003** (FIELD_PROPERTY missing_entity), **O-001** (amb), **X-001** (amb).
- Pre-existing hard core: **B-002** (amb), **B-003** (TERM_TO_DATASETS abstained), **C-003** (COUNT missing_fact), **CASE5-001** (SCHEMA missing_entity), **CASE6-001** (LINEAGE missing_entity), **Q-001** (FIND_ENTITY abstained).
- A-002 and B-001 are now PASSING (fixed last round); net regression delta vs prior session: **0**.

## 4. Priority plan for the implementation cycle (P0 → P2)

1. **P0 #1 Entity Resolution Confidence Framework** — refactor `ResolutionResult` into explicit
   states (RESOLVED / NEED_CLARIFICATION / LOW_CONFIDENCE / NOT_FOUND) with features (exact,
   entity-type compat, domain compat, platform, top1/top2, score gap, candidate count, source
   confidence, ambiguity state). Runner-up of a *different* entity type must NOT auto-clarify;
   exact match must outrank fuzzy. Add tests (exact / near-name / duplicate-name /
   same-name-different-platform / same-name-different-domain / glossary dup / report ambiguity /
   false-positive clarify / false-negative fuzzy).
2. **P0 #2 QueryScope/domain propagation** — carry a `QueryScope` (entity_type + domain + platform)
   extracted from the question into resolution (`resolve(..., scope=...)`); scope-filter candidates
   and scoring so "term X trong domain Y" resolves within Y.
3. **P0 #3 Data normalization quick wins** — trim/case-normalize platform + dataset names on ingest;
   verify impact on fuzzy/exact matches (tests).
4. **P1 #4-#9** — glossary/domain disambiguation, type-aware retrieval (report/dashboard/document vs
   dataset), metadata-quality-aware retrieval (description/domain presence), complexity/Thinking gate
   hardening, report/document discovery, structured citation plumbing.
5. **P2 #10** — multi-turn/context stability; relationship layer ONLY if real lineage data verified.
6. **Final** — full regression (unit + harness26 + golden + ruff) + write `docs/rolling_fix_report.md`.

## 5. Hard constraints governing every change (from user directive)

- No hard-coding of entity/term names; no per-question if/else; no editing ground truth; no dropping
  failing tests; HTTP 200 ≠ PASS; abstention > fabrication; every change needs a regression test;
  verify claims before implementing; no new GraphRAG/graph DB; no new relationship layer without
  verifying real lineage/relationship data.