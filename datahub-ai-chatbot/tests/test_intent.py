from retrieval.intent import QueryIntent, classify_intent


def test_term_definition_vietnamese() -> None:
    assert classify_intent("Term Revenue nghĩa là gì?") == QueryIntent.TERM_DEFINITION
    assert classify_intent("định nghĩa Net Revenue") == QueryIntent.TERM_DEFINITION
    assert classify_intent("Revenue là gì") == QueryIntent.TERM_DEFINITION


def test_term_definition_english() -> None:
    assert classify_intent("What is the meaning of Revenue?") == QueryIntent.TERM_DEFINITION
    assert classify_intent("define Net Revenue") == QueryIntent.TERM_DEFINITION


def test_owner_lookup_vietnamese() -> None:
    assert classify_intent("Ai sở hữu dataset sales.orders?") == QueryIntent.OWNER_LOOKUP
    assert classify_intent("dataset sales.orders của ai?") == QueryIntent.OWNER_LOOKUP


def test_owner_lookup_english() -> None:
    assert classify_intent("Who owns sales.orders?") == QueryIntent.OWNER_LOOKUP
    assert classify_intent("who is the owner of finance.monthly_revenue") == QueryIntent.OWNER_LOOKUP


def test_term_to_datasets() -> None:
    assert classify_intent("Dataset nào gắn term Customer?") == QueryIntent.TERM_TO_DATASETS
    assert classify_intent("find dataset associated with Revenue") == QueryIntent.TERM_TO_DATASETS


def test_lineage() -> None:
    assert classify_intent("Dataset finance.monthly_revenue lấy dữ liệu từ đâu?") == QueryIntent.LINEAGE
    assert classify_intent("upstream of sales.orders") == QueryIntent.LINEAGE
    assert classify_intent("what are the downstream dependencies") == QueryIntent.LINEAGE
    assert classify_intent("nguồn dữ liệu của dataset") == QueryIntent.LINEAGE
    assert classify_intent("thông tin về lineage của dataset dim_inventory_category") == QueryIntent.LINEAGE
    assert classify_intent("thông tin về linage của dataset dim_inventory_category") == QueryIntent.LINEAGE
    assert classify_intent("lineage của dim_inventory_category") == QueryIntent.LINEAGE


def test_schema_lookup() -> None:
    assert classify_intent("Dataset sales.orders có những field nào?") == QueryIntent.SCHEMA_LOOKUP
    assert classify_intent("schema of finance.monthly_revenue") == QueryIntent.SCHEMA_LOOKUP
    assert classify_intent("các cột của dataset") == QueryIntent.SCHEMA_LOOKUP


def test_document_qa() -> None:
    assert classify_intent("Theo tài liệu, Net Revenue được tính như thế nào?") == QueryIntent.DOCUMENT_QA
    assert classify_intent("document nói gì về revenue?") == QueryIntent.DOCUMENT_QA
    assert classify_intent("theo document monthly revenue report") == QueryIntent.DOCUMENT_QA


def test_datahub_url() -> None:
    assert classify_intent("Cho tôi link DataHub của dataset sales.orders.") == QueryIntent.DATAHUB_URL
    assert classify_intent("url của sales.orders") == QueryIntent.DATAHUB_URL
    assert classify_intent("đường dẫn datahub") == QueryIntent.DATAHUB_URL


def test_entity_exists() -> None:
    assert classify_intent("Dataset abc.xyz có tồn tại không?") == QueryIntent.ENTITY_EXISTS
    assert classify_intent("sales.orders có không?") == QueryIntent.ENTITY_EXISTS
    assert classify_intent("does finance.monthly_revenue exist?") == QueryIntent.ENTITY_EXISTS


def test_domain_query_vietnamese() -> None:
    assert classify_intent("Domain vgreen bao gồm những asset nào?") == QueryIntent.DOMAIN_QUERY
    assert classify_intent("domain Finance gồm những dataset nào") == QueryIntent.DOMAIN_QUERY
    assert classify_intent("những asset thuộc domain Logistics") == QueryIntent.DOMAIN_QUERY
    assert classify_intent("domain vgreen có những entity nào?") == QueryIntent.DOMAIN_QUERY


def test_domain_query_linh_vuc_synonym() -> None:
    assert classify_intent("Lĩnh vực tài chính gồm những dataset nào") == QueryIntent.DOMAIN_QUERY
    assert classify_intent("lĩnh vực Logistics có những asset nào?") == QueryIntent.DOMAIN_QUERY
    assert classify_intent("những asset thuộc lĩnh vực Sản xuất") == QueryIntent.DOMAIN_QUERY
    assert classify_intent("linh vuc tai chinh gom nhung dataset nao") == QueryIntent.DOMAIN_QUERY


def test_count_entities_vietnamese() -> None:
    assert classify_intent("Có bao nhiêu datasets?") == QueryIntent.COUNT_ENTITIES
    assert classify_intent("Lĩnh vực tài chính có bao nhiêu datasets?") == QueryIntent.COUNT_ENTITIES
    assert classify_intent("domain Finance có bao nhiêu datasets") == QueryIntent.COUNT_ENTITIES
    assert classify_intent("có bao nhiêu glossary terms?") == QueryIntent.COUNT_ENTITIES
    assert classify_intent("tổng cộng có bao nhiêu dashboard?") == QueryIntent.COUNT_ENTITIES


def test_count_entities_english() -> None:
    assert classify_intent("How many datasets are in domain Finance?") == QueryIntent.COUNT_ENTITIES
    assert classify_intent("count datasets in domain Finance") == QueryIntent.COUNT_ENTITIES
    assert classify_intent("how many dashboards exist?") == QueryIntent.COUNT_ENTITIES


def test_count_does_not_steal_other_intents() -> None:
    assert classify_intent("Dataset sales.orders có bao nhiêu field?") != QueryIntent.COUNT_ENTITIES
    assert classify_intent("Revenue là gì") == QueryIntent.TERM_DEFINITION
    assert classify_intent("Dataset nào gắn term Customer?") == QueryIntent.TERM_TO_DATASETS
    assert classify_intent("Ai sở hữu dataset sales.orders?") == QueryIntent.OWNER_LOOKUP


def test_domain_query_english() -> None:
    assert classify_intent("What assets are in domain VGreen?") == QueryIntent.DOMAIN_QUERY
    assert classify_intent("datasets belonging to domain Sales") == QueryIntent.DOMAIN_QUERY
    assert classify_intent("domain: Sales") == QueryIntent.DOMAIN_QUERY


def test_domain_listing_intent() -> None:
    assert classify_intent("có các domain nào?") == QueryIntent.DOMAIN_QUERY
    assert classify_intent("Có những domain nào?") == QueryIntent.DOMAIN_QUERY
    assert classify_intent("liệt kê các domain") == QueryIntent.DOMAIN_QUERY
    assert classify_intent("liệt kê domain") == QueryIntent.DOMAIN_QUERY
    assert classify_intent("danh sách các domain") == QueryIntent.DOMAIN_QUERY
    assert classify_intent("danh sách domain") == QueryIntent.DOMAIN_QUERY
    assert classify_intent("domain nào trong hệ thống?") == QueryIntent.DOMAIN_QUERY
    assert classify_intent("các domain trong hệ thống") == QueryIntent.DOMAIN_QUERY
    assert classify_intent("liệt kê các lĩnh vực") == QueryIntent.DOMAIN_QUERY
    assert classify_intent("danh sách lĩnh vực") == QueryIntent.DOMAIN_QUERY
    assert classify_intent("liệt kê miền") == QueryIntent.DOMAIN_QUERY
    assert classify_intent("co cac domain nao?") == QueryIntent.DOMAIN_QUERY
    assert classify_intent("liet ke linh vuc") == QueryIntent.DOMAIN_QUERY


def test_domain_listing_does_not_steal_entity_domain() -> None:
    assert classify_intent("fact_inventory thuộc domain nào?") == QueryIntent.ENTITY_DOMAIN
    assert classify_intent("sales.orders thuộc lĩnh vực nào?") == QueryIntent.ENTITY_DOMAIN
    assert classify_intent("lĩnh vực tài chính gồm những dataset nào") == QueryIntent.DOMAIN_QUERY
    assert classify_intent("có bao nhiêu datasets?") == QueryIntent.COUNT_ENTITIES


def test_platform_query() -> None:
    assert classify_intent("Những dataset trên platform sap?") == QueryIntent.PLATFORM_QUERY
    assert classify_intent("platform powerbi có những asset gì?") == QueryIntent.PLATFORM_QUERY
    assert classify_intent("datasets on snowflake") == QueryIntent.PLATFORM_QUERY
    assert classify_intent("assets on sap") == QueryIntent.PLATFORM_QUERY


def test_tag_query() -> None:
    assert classify_intent("Dataset nào có tag Gold?") == QueryIntent.TAG_QUERY
    assert classify_intent("assets tagged PII") == QueryIntent.TAG_QUERY
    assert classify_intent("list datasets with tag MasterData") == QueryIntent.TAG_QUERY


def test_entities_by_owner() -> None:
    assert classify_intent("Dataset nào do Sales Analytics sở hữu?") == QueryIntent.ENTITIES_BY_OWNER
    assert classify_intent("what does Finance Analytics own") == QueryIntent.ENTITIES_BY_OWNER
    assert classify_intent("datasets owned by Sales Analytics") == QueryIntent.ENTITIES_BY_OWNER
    assert classify_intent("những dataset của Finance Analytics") == QueryIntent.ENTITIES_BY_OWNER


def test_certified_list() -> None:
    assert classify_intent("Những dataset certified nào?") == QueryIntent.CERTIFIED_LIST
    assert classify_intent("list certified assets") == QueryIntent.CERTIFIED_LIST
    assert classify_intent("danh sách certified dataset") == QueryIntent.CERTIFIED_LIST


def test_term_to_datasets_still_works() -> None:
    assert classify_intent("Dataset nào gắn term Customer?") == QueryIntent.TERM_TO_DATASETS
    assert classify_intent("find dataset associated with Revenue") == QueryIntent.TERM_TO_DATASETS


def test_general_fallback() -> None:
    assert classify_intent("Bạn có thể giúp gì?") == QueryIntent.GENERAL
    assert classify_intent("hello") == QueryIntent.GREETING
    assert classify_intent("nội dung của datahub") == QueryIntent.GENERAL


def test_entity_domain_membership() -> None:
    assert classify_intent("dataset sales.orders thuộc về domain nào?") == QueryIntent.ENTITY_DOMAIN
    assert classify_intent("sales.orders thuộc domain nào") == QueryIntent.ENTITY_DOMAIN
    assert classify_intent("domain của dataset sales.orders là gì?") == QueryIntent.ENTITY_DOMAIN
    assert classify_intent("sales.orders thuộc lĩnh vực nào?") == QueryIntent.ENTITY_DOMAIN
    assert classify_intent("which domain does sales.orders belong to") == QueryIntent.ENTITY_DOMAIN
    assert classify_intent("domain of finance.monthly_revenue") == QueryIntent.ENTITY_DOMAIN


def test_owner_lookup_alternate_phrasing() -> None:
    assert classify_intent("dataset sales.orders thuộc về ai?") == QueryIntent.OWNER_LOOKUP
    assert classify_intent("sales.orders thuộc về ai") == QueryIntent.OWNER_LOOKUP
    assert classify_intent("chủ sở hữu của dataset sales.orders") == QueryIntent.OWNER_LOOKUP
    assert classify_intent("belongs to whom sales.orders") == QueryIntent.OWNER_LOOKUP
