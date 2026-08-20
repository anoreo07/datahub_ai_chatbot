# ROOT CAUSE MAP

Grouping of baseline failures by shared root cause. One fix area per RC, no per-dataset tickets.

## RC1b: Fuzzy name-matching resolves the wrong entity

- **Description**: resolver_name_query returns db_rows=0 for the exact name; the fuzzy fallback then resolves an unrelated entity that happens to share tokens, sending wrong URN downstream (tools run on wrong entity, sometimes yielding UNKNOWN).
- **First incorrect state**: `entity_resolution`
- **Affected tests (7)**: B-001, CASE3-001, G-002, O-002, T-001, V-001, X-001
- **Failure types**: ENTITY_RESOLUTION_FAILURE
- **Evidence**: B-001/G-002/O-002/T-001/X-001: db_rows=0 then fuzzy match to unrelated entity. V-001: fact_mcr unresolved -> chat_not_found. CASE3-001: fuzzy resolved '[VN] Dealer OUT' instead of intended entity.
- **Fix area**: Fuzzy fallback must require a minimum score threshold per entity-type and optionally trigger abstention/UNKNOWN instead of returning a low-confidence wrong entity.

## RC2: Intent keyword router misroutes NL discovery & reverses linkage direction

- **Description**: Keyword-based intent router picks the wrong tool for natural-language discovery and dataset<->term linkage queries; for F-series the linkage direction is reversed, for B-series NL discovery is routed to TERM_TO_DATASETS.
- **First incorrect state**: `intent`
- **Affected tests (5)**: B-002, B-003, F-001, F-002, F-003
- **Failure types**: INTENT_FAILURE
- **Evidence**: B-002/B-003: NL discovery routed to TERM_TO_DATASETS, wrong tool, no entity context. F-001/F-002/F-003: dataset->term linkage reversed; resolved '[VN] Dealer OUT'.
- **Fix area**: Intent classification should use the LLM intent classifier (or hybrid) instead of hard keyword rules for discovery/linkage; linkage direction must respect query subject-object.

## RC6: Report / dashboard discovery fails

- **Description**: Queries targeting report/dashboard entities resolve to datasets (or are blocked by the ambiguity gate) because report-type entities are not surfaced/discovered; sometimes the correct dashboard is in candidates but not chosen.
- **First incorrect state**: `report_discovery`
- **Affected tests (5)**: CASE2-001, CASE2-002, H-001, H-002, H-003
- **Failure types**: REPORT_DISCOVERY_FAILURE
- **Evidence**: H-001: resolved dataset 'Mapping Supplier & Buyer Report' instead of report. H-002/CASE2-001: dashboard in candidates but ambiguity gate blocked. CASE2-002: rpt_survey_weekly_supply_capacity not discovered.
- **Fix area**: Discovery must include report/dashboard entity types and route report-intent queries to them; ambiguity gate must not hide report entities.

## RC7: Lineage queries resolve wrong entity before lineage tool runs

- **Description**: For lineage questions the resolver returns the wrong dataset (e.g. complaint daily report instead of the supply-capacity report), so the lineage tool correctly returns UNKNOWN but on the wrong entity.
- **First incorrect state**: `entity_resolution`
- **Affected tests (5)**: CASE4-001, CASE6-001, J-001, M-001, N-001
- **Failure types**: ENTITY_RESOLUTION_FAILURE
- **Evidence**: CASE4-001: resolved '[CSKH]_Daily Report_Báo cáo khiếu nại KH...' instead of Report_Supply_Capacity. J-001/M-001/N-001/CASE6-001: lineage UNKNOWN on wrong entity.
- **Fix area**: Resolve the exact lineage source entity (match by report name, not fuzzy dataset tokens) before invoking the lineage tool; feed resolved URN explicitly.

## RC4: Glossary resolution lacks domain scoping & duplicate-term surfacing

- **Description**: Glossary-term queries are resolved to datasets with similar names (Demand -> 'Demand check'), domain context is dropped, and terms with multiple URNs (Coverage Date x2) surface only one definition.
- **First incorrect state**: `entity_resolution`
- **Affected tests (4)**: CASE1-001, CASE1-002, E-001, L-001
- **Failure types**: DOMAIN_DISAMBIGUATION_FAILURE, ENTITY_RESOLUTION_FAILURE
- **Evidence**: CASE1-001: 'Demand là gì?' -> dataset 'Demand check'. CASE1-002: domain SẢN XUẤT dropped -> ambiguous clarify 'CP sản xuất bình quân/xe SOP'. E-001/L-001: Coverage Date 2 URNs only 1 surfaced.
- **Fix area**: Glossary resolver must prefer glossaryTerm type, apply domain filter, and surface all duplicate-term URNs with disambiguation.

## RC5: Composite / multi-hop / comparison queries not decomposed

- **Description**: Thinking/planning mode attempts comparisons across many datasets in one turn, collapses multi-hop lineage chains into a single schema lookup, and answers only part of two-part / two-dataset questions.
- **First incorrect state**: `planner_decomposition`
- **Affected tests (4)**: CASE1-003, CASE5-001, R-001, S-001
- **Failure types**: PLANNER_DECOMPOSITION_FAILURE
- **Evidence**: CASE1-003: comparison across 6 datasets in one turn. CASE5-001: 5-hop chain collapsed to SCHEMA_LOOKUP. R-001: only 1 of 2 datasets resolved. S-001: only 1 of 2 parts answered.
- **Fix area**: Planner must decompose composite queries into per-entity sub-tasks with intermediate results; multi-hop lineage must be planned as a chain of hops.

## RC3: Count tool invoked without entity/domain filter

- **Description**: count_entities is called with entity_hint=None, so it returns the global dataset count ('Có tổng cộng 500 datasets') instead of counting the scoped subset the user asked about.
- **First incorrect state**: `tool_arguments`
- **Affected tests (3)**: C-001, C-002, C-003
- **Failure types**: TOOL_ARGUMENT_FAILURE
- **Evidence**: C-001/2/3: count tool output global total 500; expected a scoped count for the queried entity/domain.
- **Fix area**: Tool selector must propagate resolved entity/domain into count_entities arguments; validate argument non-null before invocation.

## RC8: Field-property / formula evidence not injected into context

- **Description**: Field-level description/owner and metric formula from the ground-truth entity description are not assembled into the evidence/context, so the answer lists fields without explaining the target field or claims no formula exists.
- **First incorrect state**: `evidence_selection`
- **Affected tests (3)**: G-001, G-003, K-001
- **Failure types**: EVIDENCE_SELECTION_FAILURE, METRIC_FORMULA_DISCOVERY_FAILURE
- **Evidence**: G-001/G-003: fields listed but target field not explained. K-001: formula exists in description but answer said 'không có công thức'.
- **Fix area**: Evidence builder must extract field definitions/owners and metric formulas from entity metadata and include them in the context sent to the LLM.

## RC1a: False-positive ambiguity gate

- **Description**: Resolver returns ambiguous=False with a single clear top candidate, but response surfaces an ambiguous clarification because a runner-up candidate (different entity type) passes the ambiguity threshold.
- **First incorrect state**: `entity_resolution`
- **Affected tests (2)**: A-001, O-001
- **Failure types**: ENTITY_RESOLUTION_FAILURE
- **Evidence**: A-001: resolver_result ambiguous=False exact=False top_score=0.7628 candidates=2, runner-up is a glossary term; response ambiguous=True. O-001: same pattern (ambiguous=True clarify with runner-up of different type).
- **Fix area**: Ambiguity gate must consider top-score margin and entity-type consistency; only trigger clarification when top candidates share the same type or score gap is small.

## RC10: Term->datasets reverse-linkage retrieval misses linked datasets

- **Description**: Queries 'term X thuộc về datasets nào' return empty even though ground-truth edge map has many dataset<->term edges; reverse edges are not retrieved.
- **First incorrect state**: `retrieval`
- **Affected tests (1)**: U-001
- **Failure types**: RETRIEVAL_FAILURE
- **Evidence**: U-001: PII term->datasets returned empty; ground truth has 23 edges incl. stg_contact<->PII, stg_pbed<->PII.
- **Fix area**: Reverse-linkage retrieval must query edges in both directions and fall back to the dataset/term edge map when candidate search is empty.

## RC11: Domain constraint not applied as a filter

- **Description**: When the query states a domain (e.g. TÀI CHÍNH), the resolver ignores it and returns an ambiguous clarification instead of using the domain to scope candidates.
- **First incorrect state**: `domain_resolution`
- **Affected tests (1)**: W-001
- **Failure types**: DOMAIN_DISAMBIGUATION_FAILURE
- **Evidence**: W-001: domain TÀI CHÍNH dropped -> ambiguous clarify instead of domain-scoped resolution.
- **Fix area**: Extract domain constraint from query and pass it to resolver/retrieval as a candidate filter before ambiguity decision.

## RC9: Multi-turn context / anaphora not propagated

- **Description**: In a follow-up turn the whole query is fuzzy-matched as an entity name instead of resolving the anaphoric reference (e.g. 'công thức của nó') against the prior turn's entity; OWNER_LOOKUP runs on the wrong target.
- **First incorrect state**: `context_propagation`
- **Affected tests (1)**: Q-001
- **Failure types**: CONTEXT_PROPAGATION_FAILURE
- **Evidence**: Q-001: follow-up 'công thức của nó' treated as entity name; context from conversation history not propagated to resolver.
- **Fix area**: Resolver must merge conversation history references before name matching; anaphora resolution should substitute the prior entity URN.
