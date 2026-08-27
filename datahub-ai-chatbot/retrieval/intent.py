import re
from enum import StrEnum


class QueryIntent(StrEnum):
    # --- user-specified Metadata Intelligence taxonomy -----------------------
    DATASET_LOOKUP = "DATASET_LOOKUP"
    FIELD_LOOKUP = "FIELD_LOOKUP"
    SCHEMA_LOOKUP = "SCHEMA_LOOKUP"
    TERM_DEFINITION = "TERM_DEFINITION"
    OWNER_LOOKUP = "OWNER_LOOKUP"
    DOMAIN_LOOKUP = "DOMAIN_LOOKUP"
    LINEAGE_UPSTREAM = "LINEAGE_UPSTREAM"
    LINEAGE_DOWNSTREAM = "LINEAGE_DOWNSTREAM"
    IMPACT_ANALYSIS = "IMPACT_ANALYSIS"
    RECURSIVE_IMPACT = "RECURSIVE_IMPACT"
    COMPARISON = "COMPARISON"
    COMPOSITE_QUERY = "COMPOSITE_QUERY"
    GRAPH_QUERY = "GRAPH_QUERY"
    RELATED_DATASETS = "RELATED_DATASETS"
    SEMANTIC_SEARCH = "SEMANTIC_SEARCH"
    MULTI_ENTITY_QUERY = "MULTI_ENTITY_QUERY"
    MULTI_HOP_CHAIN = "MULTI_HOP_CHAIN"
    # --- metadata listing intents --------------------------------------------
    MISSING_DESCRIPTION = "MISSING_DESCRIPTION"
    MISSING_OWNER = "MISSING_OWNER"
    MISSING_DOMAIN = "MISSING_DOMAIN"
    # --- field property intent -----------------------------------------------
    FIELD_PROPERTY = "FIELD_PROPERTY"
    # --- legacy intents kept for compatibility with existing routing ---------
    FIND_ENTITY = "FIND_ENTITY"
    TERM_TO_DATASETS = "TERM_TO_DATASETS"
    LINEAGE = "LINEAGE"
    IMPACT = "IMPACT"
    ENTITY_DOMAIN = "ENTITY_DOMAIN"
    COUNT_ENTITIES = "COUNT_ENTITIES"
    DOMAIN_QUERY = "DOMAIN_QUERY"
    TAG_QUERY = "TAG_QUERY"
    PLATFORM_QUERY = "PLATFORM_QUERY"
    ENTITIES_BY_OWNER = "ENTITIES_BY_OWNER"
    CERTIFIED_LIST = "CERTIFIED_LIST"
    DOCUMENT_QA = "DOCUMENT_QA"
    GREETING = "GREETING"
    CHITCHAT = "CHITCHAT"
    GENERAL = "GENERAL"
    DATAHUB_URL = "DATAHUB_URL"
    ENTITY_EXISTS = "ENTITY_EXISTS"
    LISTING = "LISTING"
    SQL_GENERATION = "SQL_GENERATION"
    QUALITY_CHECK = "QUALITY_CHECK"
    METADATA_REPORT = "METADATA_REPORT"


# Mapping from the new taxonomy onto the legacy intents so existing routing
# (chat_service._structured_retrieval etc.) keeps working unchanged.
LEGACY_FOR: dict["QueryIntent", "QueryIntent"] = {
    QueryIntent.DATASET_LOOKUP: QueryIntent.FIND_ENTITY,
    QueryIntent.FIELD_LOOKUP: QueryIntent.SCHEMA_LOOKUP,
    QueryIntent.FIELD_PROPERTY: QueryIntent.SCHEMA_LOOKUP,
    QueryIntent.DOMAIN_LOOKUP: QueryIntent.ENTITY_DOMAIN,
    QueryIntent.LINEAGE_UPSTREAM: QueryIntent.LINEAGE,
    QueryIntent.LINEAGE_DOWNSTREAM: QueryIntent.LINEAGE,
    QueryIntent.IMPACT_ANALYSIS: QueryIntent.IMPACT,
    QueryIntent.RECURSIVE_IMPACT: QueryIntent.IMPACT,
    QueryIntent.COMPARISON: QueryIntent.GENERAL,
    QueryIntent.COMPOSITE_QUERY: QueryIntent.GENERAL,
    QueryIntent.GRAPH_QUERY: QueryIntent.GENERAL,
    QueryIntent.RELATED_DATASETS: QueryIntent.FIND_ENTITY,
    QueryIntent.SEMANTIC_SEARCH: QueryIntent.GENERAL,
    QueryIntent.MULTI_ENTITY_QUERY: QueryIntent.GENERAL,
    QueryIntent.MULTI_HOP_CHAIN: QueryIntent.GENERAL,
}


_GREETINGS = {
    "xin chào", "xin chao", "chào", "chao", "hello", "hi", "hey",
    "chào bạn", "chao ban", "xin chào bạn", "xin chao ban", "chào bot", "chao bot",
    "hello bot", "hi there",
}

_CHITCHAT = {
    "bạn khỏe không", "bạn khoẻ không", "ban khoe khong",
    "bạn có khỏe không", "bạn có khoẻ không", "ban co khoe khong",
    "how are you",
    "bạn tên gì", "ban ten gi",
    "bạn là ai", "ban la ai", "who are you",
    "bạn làm gì", "ban lam gi",
    "cảm ơn", "cám ơn", "cam on",
    "thank", "thanks",
    "ok", "okay", "good", "tốt", "tot", "tuyệt", "tuyet", "great",
}


def _norm_vn(s: str) -> str:
    import unicodedata
    s = s.lower()
    s = s.replace("đ", "d").replace("Đ", "d")
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    return s


_RULE_STRINGS: list[tuple[str, QueryIntent]] = [
    # Composite / multi-step questions — checked high so they win over subsets.
    (r"(?:đồng thời|dong thoi|cũng như|cung nhu|sau đó|sau do)\b", QueryIntent.COMPOSITE_QUERY),
    (r"(?:và (?:ai|cái gì|what|của|do)? (?:ai|what|cái gì|nào|sau))|(?:and then|and what|and who|and its)",
     QueryIntent.COMPOSITE_QUERY),
    (r"(?:nhiều|nhieu|một số|mot so|several)\s+(?:dataset|bảng|table|entity)(?:s|es)?\b", QueryIntent.MULTI_ENTITY_QUERY),
    # Multi-hop chain: "từ report capacity → định nghĩa → cột → công thức →
    # nguồn dữ liệu thô" (arrow chain) or "trong domain X, tìm report về Y,
    # term liên quan, dataset nguồn và lineage" (comma chain). The answer walks
    # each hop and marks missing data UNKNOWN. Must win over SCHEMA_LOOKUP /
    # LINEAGE / TERM_DEFINITION, which would each grab just one hop.
    (r"(?:->|\u2192|\u2794|\u21d2|arrow|chuỗi|chained|hop\b)",
     QueryIntent.MULTI_HOP_CHAIN),
    (r"(?:từ|tu|from)\s+[\w\.\- ]{1,40}\s*(?:->|\u2192|\u2794|\u21d2)",
     QueryIntent.MULTI_HOP_CHAIN),
    (r"(?:tìm|tim|find)\s+(?:report|báo cáo|bao cao)\b[^\n]{0,120}\b"
     r"(?:term|thuật ngữ|thuat ngu|lineage|nguồn|nguon|dataset nguồn)",
     QueryIntent.MULTI_HOP_CHAIN),
    (r"(?:từ|tu|from)\s+(?:báo cáo|bao cao|report|dataset|bảng|bang)\s+[^\n]{1,60}?\b"
     r"(?:cho tôi biết|cho toi biet|xem|tìm|tim|biết|biet|hướng dẫn)\s+[^\n]{1,80}?\b"
     r"(?:công thức|cong thuc|lineage|nguồn|nguon|dữ liệu thô|du lieu tho)",
     QueryIntent.MULTI_HOP_CHAIN),
    # Explicit term definition phrases
    (r"(?:giải thích|giai thich|cho biết|cho biet|tìm hiểu|tim hieu)\s+(?:khái niệm|khai niem|thuật ngữ|thuat ngu|term)\b",
     QueryIntent.TERM_DEFINITION),
    (r"(?:khái niệm|khai niem|thuật ngữ|thuat ngu)\s+[^\n]{1,60}?\s+"
     r"(?:là gì|la gi|được định nghĩa|duoc dinh nghia|có ý nghĩa gì|co y nghia gi|nghĩa là gì|nghia la gi)",
     QueryIntent.TERM_DEFINITION),
    # Formula / Column calculation property queries
    (r"(?:công thức|cong thuc|cách tính|cach tinh|formula)\s+(?:tính\s+)?(?:của\s+)?(?:column|cột|cot|trường|truong|field)?",
     QueryIntent.FIELD_PROPERTY),

    # Comparison: "so sánh A và B", "compare X with Y", "A khác B thế nào"
    # Must win over SCHEMA_LOOKUP / LINEAGE / TERM_DEFINITION which would each
    # grab just one entity from a multi-entity comparison question.
    (r"(?:so sánh|so sanh|so với|so voi|compare|comparison|comparing|"
     r"khác|khac|đ khác|d khac|difference|versus|\bvs\.?|"
     r"nên dùng|nen dung|phù hợp|phu hop|suitable|recommend|"
     r"tốt hơn|tot hon|better|best|ưu tiên|uu tien|"
     r"đánh giá|danh gia|evaluate|assessment)\b"
     r"[^\n]{0,120}?"
     r"(?:\b(?:và|va|with|với|voi|hay|or|hoặc|hoac|,)\b"
     r"[^\n]{0,60}?)?"
     r"(?:\b(?:về|ve|about|trên|tren|in|of)\b"
     r"[^\n]{0,60}?)?"
     r"(?:dataset|bảng|bang|dashboard|report|báo cáo|term|thuật ngữ|schema)",
     QueryIntent.COMPARISON),
    # Broader comparison pattern: just "so sánh" + any entity type mention
    (r"(?:so sánh|so sanh|compare|comparison|versus|\bvs\.?)\b"
     r"[^\n]{0,200}?"
     r"(?:\b(?:và|va|with|với|voi|,)\b"
     r"[^\n]{0,100}?)",
     QueryIntent.COMPARISON),
    # Graph / traversal questions (shortest/longest path, cycle, reachability).
    (r"(?:đường ngắn nhất|duong ngan nhat|shortest path|longest path|chuỗi dài nhất|duong di dai nhat|"
     r"mối quan hệ|moi quan he|relationship|chu kỳ|chu ky|cycle|phụ thuộc lẫn nhau|circular|loop\b)",
     QueryIntent.GRAPH_QUERY),
    # Related datasets / semantic search (business concept, "dataset nào liên quan").
    (r"(?:dataset nào liên quan|datasets related|related datasets|liên quan nhất|lien quan nhat|"
     r"tương tự|tuong tu|most relevant)\b", QueryIntent.RELATED_DATASETS),
    (r"(?:tìm.*theo.*ý|find.*similar|semantic|ngữ nghĩa|nghia tuong tu|concept)", QueryIntent.SEMANTIC_SEARCH),
    # Recursive impact: every descendant / deep traversal — must win before the
    # plain IMPACT_ANALYSIS rules (which also match the bare word "impact").
    (r"(?:recursive|recursiv|tất cả tiêu thụ|xuyên sâu|into depth|deeper|"
     r"tất cả|all|toàn bộ|toan bo|mọi)\s+.*(?:downstream|hậu duệ|con cháu|tiêu thụ|impact)",
     QueryIntent.RECURSIVE_IMPACT),
    # Impact analysis: removal/change affects who. Must win before LINEAGE.
    (r"(?:nếu (?:thay đổi|thay doi|xóa|tắt|có|bỏ|change|delete|drop|remov)|remove|and\s+then?)",
     QueryIntent.IMPACT_ANALYSIS),
    (r"(?:ai bị ảnh hưởng|ảnh huong nghiêm|sẽ bị|bi tac dong hang loat|impact|blast radius|dây chuyền ảnh hưởng|"
     r"chiếu xuống|ảnh hưởng lan truyền|affected|who (?:is|are) affected|what breaks|bị ảnh hưởng|bi anh huong)",
     QueryIntent.IMPACT_ANALYSIS),
    # "Xóa dim_X thì những bảng nào bị ảnh hưởng?" — verb-first removal without
    # "nếu" prefix, and entity names that look like data assets.
    (r"(?:xóa|xoa|xoá|delete|drop|remove|thay đổi|thay doi)\b[^\n]{0,80}?(?:ảnh hưởng|anh huong|impact|affected)",
     QueryIntent.IMPACT_ANALYSIS),
    # Implicit impact: removing/changing an asset while asking about the outcome,
    # WITHOUT the literal word "ảnh hưởng". "Xóa dataset X thì sao?", "delete dataset
    # X what happens", "thay đổi X ra sao" all imply impact analysis (blast radius).
    (r"(?:xóa|xoá|xoa|delete|drop|remove|disable|thay đổi|thay doi|ảnh hưởng|anh huong|impact)\b"
     r"[^\n]{0,90}?(?:thì sao|thi sao|thế nào|the nao|ra gì|ra gi|sẽ ra sao|se ra sao|ra sẽ|ra se|"
     r"what happens|what would happen|whats? next|consequence|xảy ra gì|xay ra gi)",
     QueryIntent.IMPACT_ANALYSIS),
    # Reverse order: "ảnh hưởng của việc xóa dataset X?" — the impact word comes
    # BEFORE the removal verb, which the verb-first rules above cannot catch.
    (r"(?:ảnh hưởng|anh huong|impact|affected|effect)\b[^\n]{0,90}?(?:của việc xóa|cua viec xoa|"
     r"của việc delete|cua viec delete|of (?:deleting|dropping|removing)|khi (?:xóa|xoa|delete))",
     QueryIntent.IMPACT_ANALYSIS),
    # Relationship / membership queries FIRST so they win over generic TERM_DEFINITION ("là gì").
    (r"(?:thuộc|thuoc|nằm|nam|được chia|belong|belongs|belonging|in)\s+(?:về|ve|trong|to|in)?\s*(?:domain|lĩnh vực|linh vuc|miền|mien)\s+(?:nào|nao|what|which)", QueryIntent.ENTITY_DOMAIN),
    (r"(?:which|what)\s+(?:domain|lĩnh vực|linh vuc|miền|mien)\b", QueryIntent.ENTITY_DOMAIN),
    # Schema/field + domain/owner composite ("schema X, field chứa số lượng,
    # và domain của dataset này") is a SCHEMA_LOOKUP answer with the domain
    # appended — wins over the bare "domain của" rule below.
    (r"(?:schema|field|trường|truong|column|cột|cot|cấu trúc)\b[^\n]{0,90}\b"
     r"(?:và|va|vao)\b[^\n]{0,90}\b"
     r"(?:domain|lĩnh vực|linh vuc|miền|mien|owner)\b",
     QueryIntent.SCHEMA_LOOKUP),
    (r"(?:domain|lĩnh vực|linh vuc|miền|mien)\s+(?:của|cua|of|thuộc|belongs? to)\b", QueryIntent.ENTITY_DOMAIN),
    # Owner membership questions
    # Role + domain / owner ("vai trò, domain và owner của X") is a composite
    # metadata question answered from the domain payload — wins over the single
    # OWNER_LOOKUP rule below so both domain and owner are reported.
    (r"(?:vai trò|vai tro|role)\b[^\n]{0,60}?\b"
     r"(?:domain|lĩnh vực|linh vuc|miền|mien|owner)\b",
     QueryIntent.ENTITY_DOMAIN),
    (r"(?:domain|lĩnh vực|linh vuc|miền|mien)\b[^\n]{0,60}?\bowner\b|\bowner\b"
     r"[^\n]{0,60}?\b(?:domain|lĩnh vực|linh vuc|miền|mien)\b",
     QueryIntent.ENTITY_DOMAIN),
    (r"(?:thuộc về ai|thuộc ai|thuộc sở hữu|sở hữu của ai|so huu cua ai|người sở hữu|nguoi so huu|chủ sở hữu|chu so huu|belongs to whom|owned by whom|whose)", QueryIntent.OWNER_LOOKUP),
    (r"(ai sở hữu|ai so huu|ai là chủ|ai la chu|\bowner\b\s+(of|la|is|của|cua|nào|nao|nà|na)|the\s+owner|của ai|cua ai|who (owns|is the owner)|của owner nào|cua owner nao|owner của ai|owner cua ai)", QueryIntent.OWNER_LOOKUP),
    # Schema / field queries must win over the generic "là gì" definition rule:
    # "trường uom_name là gì?" asks about a column, not a glossary term.
    (r"(field|column|cột|trường|schema|columns?|fields?|thuộc tính|cấu trúc bảng|co nhung field|co nhung truong|co nhung cot)", QueryIntent.SCHEMA_LOOKUP),
    # Dataset content lookup — "dataset X lưu trữ thông tin gì", "X chứa dữ liệu gì".
    (r"(dataset|bảng|bang)\s+[\w\.\- ]{1,60}\s+(lưu trữ|luu tru|chứa|chua|chứa dữ liệu|lưu thông tin|chứa những dữ liệu)\s", QueryIntent.DATASET_LOOKUP),
    (r"(lưu trữ thông tin gì|luu tru thong tin gi|chứa những dữ liệu gì|chua nhung du lieu gi|stores? what|contains what data)", QueryIntent.DATASET_LOOKUP),
    # Generic definition lookups — kept after the schema rules above.
    (r"(nghĩa là gì|nghia la gi|định nghĩa|dinh nghia|definition|la gi|meaning|meaning of|define|"
     r"ý nghĩa là gì|y nghia la gi|ý nghĩa gì|y nghia gi|có ý nghĩa gì|co y nghia gi|có nghĩa là gì|co nghia la gi)", QueryIntent.TERM_DEFINITION),
    (r"(lấy dữ liệu từ đâu|lấy từ đâu|upstream|downstream|lineage|linage|nguồn|source.*data|phụ thuộc|luồng dữ liệu|dòng dữ liệu|data flow|flow of data|nguôn)", QueryIntent.LINEAGE),
    # Count queries — "có bao nhiêu datasets?", "lĩnh vực tài chính có bao nhiêu datasets"
    (r"(có bao nhiêu|co bao nhieu|bao nhiêu|bao nhieu|how many|số lượng|so luong|count|tổng cộng|tong cong)\s+(dataset|dashboard|glossary(?:\s+term)?|asset|entity)s?", QueryIntent.COUNT_ENTITIES),
    (r"(dataset|dashboard|glossary(?:\s+term)?|asset|entity)s?\s+(có bao nhiêu|co bao nhieu|bao nhiêu|how many|số lượng|so luong|count)", QueryIntent.COUNT_ENTITIES),
    # Total-count phrasing — "tính tổng số dataset", "tổng số dashboard trong hệ thống".
    (r"(tính tổng số|tinh tong so|tổng số|tong so|tổng cộng|tong cong)\s+(dataset|dashboard|glossary(?:\s+term)?|asset|entity)s?", QueryIntent.COUNT_ENTITIES),
    (r"(dataset|dashboard|glossary(?:\s+term)?|asset|entity)s?\s+(tính tổng số|tinh tong so|tổng số|tong so)", QueryIntent.COUNT_ENTITIES),
    # Domain queries — "domain vgreen bao gồm những asset nào", "những asset thuộc domain X", "lĩnh vực tài chính gồm những dataset nào"
    (r"(domain|miền|lĩnh vực)\s+[\w\.\- ]{1,60}?\s+(bao gồm|gồm|có (những|các|asset|entity|dataset)|chứa|include|includes?|has|have|contain)", QueryIntent.DOMAIN_QUERY),
    (r"(assets?|entities?|datasets?|dashboards?|bảng|bang)\s+(?:(that\s+are|are|which\s+are|which|nào|nao)\s+)?(trong|thuộc|thuoc|in|belonging to|belong to)\s+(the\s+)?(domain|miền|lĩnh vực)\s+[\w\.\- ]{1,60}", QueryIntent.DOMAIN_QUERY),
    (r"(domain|miền|lĩnh vực)\s*[:=]\s*[\w\.\- ]{1,60}", QueryIntent.DOMAIN_QUERY),
    # Listing all domains — "có các domain nào?", "liệt kê domain", "danh sách domain",
    # "domain trong hệ thống", "có bao nhiêu domain" -> answered deterministically from DB.
    (r"(có những domain nào|có các domain nào|co nhung domain nao|co cac domain nao|"
     r"liệt kê (các )?domain|liệt kê (các )?lĩnh vực|liệt kê (các )?miền|"
     r"liet ke domain|liet ke linh vuc|liet ke cac linh vuc|liet ke mien|"
     r"danh sách (các )?domain|danh sách (các )?lĩnh vực|danh sach domain|danh sach cac domain|danh sach linh vuc|"
     r"domain nào trong hệ thống|domain trong hệ thống|các domain trong hệ thống|"
     r"domain nao trong he thong|domain trong he thong|"
     r"có bao nhiêu domain|có bao nhiêu lĩnh vực|co bao nhieu domain|"
     r"how many domain)", QueryIntent.DOMAIN_QUERY),
    # Platform queries — "những dataset trên sap", "platform mysql có những asset gì"
    (r"(dataset|asset|entity|dashboard)s?\s+(trên|trong|in|on)\s+(platform|nền tảng)\s+[\w\.\- ]{1,60}", QueryIntent.PLATFORM_QUERY),
    (r"(platform|nền tảng)\s+[\w\.\- ]{1,60}?\s+(bao gồm|gồm|có (những|các|dataset|asset|entity)|chứa|include|has|contain)", QueryIntent.PLATFORM_QUERY),
    (r"(những|which|what|all)\s+(dataset|asset|entity|dashboard)s?\s+(trên|on|in)\s+[\w\.\- ]{1,60}", QueryIntent.PLATFORM_QUERY),
    (r"(dataset|asset|entity)s?\s+on\s+(sap|powerbi|snowflake|mysql|hive|kafka|s3|looker|mode|bigquery|redshift|postgres)", QueryIntent.PLATFORM_QUERY),
    # Tag queries — "dataset nào có tag PII", "assets tagged Gold"
    (r"(dataset|asset|entity|dashboard)s?\s+(nào|which)?\s*(có tag|được gắn tag|với tag|tagged|with tag)\s+[\w\.\- ]{1,60}", QueryIntent.TAG_QUERY),
    (r"tag\s+[\w\.\- ]{1,40}?\s+(bao gồm|gồm|có (những|các|dataset|asset|entity)|liên quan|chứa)", QueryIntent.TAG_QUERY),
    (r"(list|liệt kê|danh sách)\s+(datasets?|assets?|entities?)\s+(with|by|có)\s+tag\s+[\w\.\- ]{1,60}", QueryIntent.TAG_QUERY),
    (r"(assets?|entities?|datasets?)\s+tagged\s+[\w\.\- ]{1,60}", QueryIntent.TAG_QUERY),
    # Entities owned by someone — "dataset nào do Sales Analytics sở hữu", "what does X own"
    (r"(dataset|asset|entity|dashboard)s?\s+(nào|which|mà)\s+(do|bởi|owned by)\s+[\w\.\- ]{1,60}\s+(sở hữu|own)", QueryIntent.ENTITIES_BY_OWNER),
    (r"(dataset|asset|entity|dashboard)s?\s+(của|owned by)\s+[\w\.\- ]{1,60}", QueryIntent.ENTITIES_BY_OWNER),
    (r"(do|bởi|owned by)\s+[\w\.\- ]{1,60}\s+(sở hữu|own)", QueryIntent.ENTITIES_BY_OWNER),
    (r"what does\s+[\w\.\- ]{1,60}\s+own", QueryIntent.ENTITIES_BY_OWNER),
    (r"(những|which)\s+(dataset|asset|entity)s?\s+(của|do)\s+[\w\.\- ]{1,60}", QueryIntent.ENTITIES_BY_OWNER),
    # Certified entities — "những dataset certified", "list certified assets"
    (r"(dataset|asset|entity)s?\s+(đã\s+)?(được\s+)?(xác nhận|certified)", QueryIntent.CERTIFIED_LIST),
    (r"certified\s+(dataset|asset|entity)s?", QueryIntent.CERTIFIED_LIST),
    (r"danh sách\s+(đã\s+)?certified", QueryIntent.CERTIFIED_LIST),
    (r"(?:dataset|asset|entity|dashboard)s?\s+(?:nào|which|mà)\s+(?:được\s+)?gắn\s+term|"
     r"(?:dataset|asset|entity)s?\s+.*\bgắn\s+với\b|"
     r"(?:dataset|asset|entity)s?\s+.*\bglossary\b|"
     r"entity.*associated|find dataset", QueryIntent.TERM_TO_DATASETS),
    (r"(term nào liên quan|terms? (?:related to|liên quan đến|about)\s|terms?.*(?:doanh thu|tồn kho|liên quan|chứa|liệt kê))", QueryIntent.TERM_TO_DATASETS),
    (r"terms?\s+(?:nào|nao|which|what)\s+(?:liên quan|lien quan|related|theo)\s", QueryIntent.TERM_TO_DATASETS),
    # Document QA — bare "tài liệu X mô tả điều gì" (not necessarily "theo tài liệu").
    (r"(tài liệu|tai lieu|documents?|reports?)\s+[\w\.\- ]{1,80}?\s+"
     r"(mô tả|mo ta|nói về|noi ve|nội dung|noi dung|describe|explain|giải thích|"
     r"nói gì|noi gi|bao gồm gì|about)", QueryIntent.DOCUMENT_QA),
    # Dashboard / report description — "mô tả chi tiết của dashboard X",
    # "X là dashboard gì" -> TERM_DEFINITION so the exact-name dashboard is
    # resolved (not a hybrid whole-sentence query that arbitrarily picks one
    # of several same-named dashboards).
    (r"(dashboard|report|báo cáo|bao cao)\s+[\w\.\- ]{1,80}?\s+"
     r"(mô tả|mo ta|miêu tả|mieu ta|chi tiết|chi tiet|nội dung|noi dung|"
     r"describe|description|explain|giải thích|giai thich)", QueryIntent.TERM_DEFINITION),
    (r"(mô tả|mo ta|miêu tả|mieu ta|chi tiết|chi tiet)\s+(của|cua|of|về|ve)\s+"
     r"(dashboard|report|báo cáo|bao cao)\b", QueryIntent.TERM_DEFINITION),
    (r"(theo tài liệu|document|report nói gì|theo document)", QueryIntent.DOCUMENT_QA),
    (r"(link|url|đường dẫn|datahub.*link)", QueryIntent.DATAHUB_URL),
    (r"(có tồn tại|tồn tại không|exist|có\s+không|co khong|có\s+\S+(?:\s+\S+)?\s+không)", QueryIntent.ENTITY_EXISTS),
    # SQL / query generation: "viết SQL", "truy vấn ... field", "sinh câu query",
    # "tạo câu lệnh truy vấn", "select ... from". Explicit SQL requests must
    # route to the SQL generator, never to generic entity search.
    (r"\b(sql|query)\b|viết\s+sql|viet\s+sql|tạo\s+sql|tao\s+sql|sinh\s+sql|"
     r"truy vấn|truy van|câu lệnh truy vấn|cau lenh truy van|lệnh để truy cập|"
     r"viết câu lệnh|viet cau lenh|trả về một câu sql|tra ve mot cau sql|"
     r"ghi\s+sql|ghi lenh truy van|select\s+|from\s+", QueryIntent.SQL_GENERATION),
    # Natural-language record queries that name a filter column and a value
    # ("lấy các bản ghi có warehouse_id = 123", "cho tôi bản ghi customer_id 5").
    # These select rows from a dataset, so they belong to the SQL generator even
    # without the literal words "sql"/"truy vấn".
    (r"(?:các\s+)?bản\s+ghi|ban\s+ghi|bản tin|ban tin|bản ghi|records?\b",
     QueryIntent.SQL_GENERATION),
    (r"(?:lấy|lay|cho tôi|cho toi|get|fetch|gắ|dieu).{0,25}\b(?:có|cot|co)\s+"
     r"\w+[_]\w+(\s*[=<>]?\s*['\"]?[a-z0-9_]+['\"]?)?", QueryIntent.SQL_GENERATION),
    # Missing metadata queries — deterministic answers from DB
    (r"(dataset|asset|entity|dashboard)s?\s+(chưa có|chua co|thiếu|thieu|missing|without)\s+"
     r"(mô\s+tả|mo ta|description|giới thiệu|gioi thieu)", QueryIntent.MISSING_DESCRIPTION),
    (r"(chưa có|chua co|thiếu|thieu|missing|without)\s+"
     r"(mô\s+tả|mo ta|description|giới thiệu|gioi thieu)\s+"
     r"(của|cua|cho|cho|các|cac|những|nhung)?\s*(dataset|asset|entity|dashboard)s?",
     QueryIntent.MISSING_DESCRIPTION),
    (r"(dataset|asset|entity|dashboard)s?\s+(chưa có|chua co|thiếu|thieu|missing|without)\s+"
     r"(chủ\s+sở\s+hữu|chu so huu|owner|người\s+quản\s+lý|nguoi quan ly)",
     QueryIntent.MISSING_OWNER),
    (r"(chưa có|chua co|thiếu|thieu|missing|without)\s+"
     r"(chủ\s+sở\s+hữu|chu so huu|owner|người\s+quản\s+lý|nguoi quan ly)\s+"
     r"(của|cua|cho|cho|các|cac|những|nhung)?\s*(dataset|asset|entity|dashboard)s?",
     QueryIntent.MISSING_OWNER),
    (r"(dataset|asset|entity|dashboard)s?\s+(chưa có|chua co|thiếu|thieu|missing|without)\s+"
     r"(domain|lĩnh vực|linh vuc|miền|mien)",
     QueryIntent.MISSING_DOMAIN),
    (r"(chưa có|chua co|thiếu|thieu|missing|without)\s+"
     r"(domain|lĩnh vực|linh vuc|miền|mien)\s+"
     r"(của|cua|cho|cho|các|cac|những|nhung)?\s*(dataset|asset|entity|dashboard)s?",
     QueryIntent.MISSING_DOMAIN),
    # Field property queries — "field X có bao nhiêu kiểu dữ liệu?", "kiểu dữ liệu của cột Y",
    # "field X có description không?", "mô tả của field Y".
    (r"(field|column|cột|trường)\s+[\w\.\- ]{1,60}\s+"
     r"(kiểu|kieu|type|dtype|data\s*type|mô\s*tả|mo ta|description|"
     r"là gì|la gi|thuộc tính|thuoc tinh|property|metadata)",
     QueryIntent.FIELD_PROPERTY),
    (r"(kiểu|kieu|type|dtype|data\s*type|mô\s*tả|mo ta|description|"
     r"thuộc tính|thuoc tinh|property)\s+"
     r"(của|cua|cho|for)\s+(field|column|cột|trường)\s+[\w\.\- ]{1,60}",
     QueryIntent.FIELD_PROPERTY),
]

_RULES: list[tuple[re.Pattern[str], QueryIntent]] = [
    (re.compile(p, re.I), intent) for p, intent in _RULE_STRINGS
]

_RULES_ASCII: list[tuple[re.Pattern[str], QueryIntent]] = [
    (re.compile(_norm_vn(p), re.I), intent) for p, intent in _RULE_STRINGS
]


def classify_intent(query: str) -> QueryIntent:
    cleaned = query.lower().strip().rstrip("?!.")
    _q_norm = _norm_vn(query)
    if re.search(
        r"^(?:làm thế nào|lam the nao|làm sao|lam sao|hướng dẫn|huong dan|cách nào|cach nao|như thế nào|nhu the nao|bằng cách nào|bang cach nao)\b",
        _q_norm,
        re.I,
    ) and not re.search(r"[A-Za-z0-9]{2,}_[A-Za-z0-9_]+|[A-Za-z0-9_]+\.[A-Za-z0-9_]+|[\"“”'`][A-Za-z0-9_]+[\"“”'`]", query):
        return QueryIntent.GENERAL

    for pattern, intent in _RULES:
        if pattern.search(query):
            return intent

    ascii_query = _norm_vn(query)
    for pattern, intent in _RULES_ASCII:
        if pattern.search(ascii_query):
            return intent

    return QueryIntent.GENERAL


def normalize_intent(intent: "QueryIntent") -> "QueryIntent":
    """Map the new Metadata Intelligence taxonomy onto the legacy vocabulary.

    Existing routing (``chat_service``) was built around the legacy intents
    (``FIND_ENTITY``, ``LINEAGE``, ``IMPACT``, ...). New intents subclass those
    concepts; this returns the legacy intent a route can act on, or the intent
    unchanged when it already belongs to the legacy set.
    """
    return LEGACY_FOR.get(intent, intent)
