"""Scope restriction guardrail.

The assistant is a grounded metadata assistant: it only answers questions
about DataHub metadata. Requests for SQL optimization, coding help,
infrastructure, business consulting, or general world knowledge are outside
the supported scope and get a canned out-of-scope response.
"""

import re

import structlog

log = structlog.get_logger()

_OUT_OF_SCOPE_PATTERNS: list[re.Pattern[str]] = [
    # SQL optimization / query tuning (either word order)
    re.compile(
        r"\b(?:sql|query|câu\s+lệnh|cau lenh)\b[^.\n]{0,60}"
        r"\b(?:tối\s*ưu|toi uu|optimize|optimisation|performance|faster|improve|chậm|cham|index)\b",
        re.I,
    ),
    re.compile(
        r"\b(?:tối\s*ưu|toi uu|optimize|optimisation|performance|faster|improve|chậm|cham|index)\b"
        r"[^.\n]{0,60}\b(?:sql|query)\b",
        re.I,
    ),
    # General programming / coding help
    re.compile(
        r"\b(?:write\s+me|viết giúp|viet giup|cách viết|cach viet|implement|refactor)\b[^.\n]{0,60}"
        r"\b(?:code|function|class|script|python|java|javascript|typescript|golang|go\s+lang|rust|sql)\b",
        re.I,
    ),
    # Coding requests phrased with "code/viết code ... bằng X"
    re.compile(
        r"\b(?:code|viết\s+code|viet code|tạo\s+code|tao code|chạy\s+code)\b[^.\n]{0,60}"
        r"\b(?:thuật\s*toán|thuat toan|algorithm|python|javascript|java|golang|rust|"
        r"sort|sắp\s*xếp|sap xep)\b",
        re.I,
    ),
    # Algorithm/sorting questions without an explicit "write" verb
    re.compile(
        r"\b(?:bubble\s*sort|quick\s*sort|merge\s*sort|insertion\s*sort|heap\s*sort|"
        r"sorting\s*algorithm|thuật\s*toán\s*(?:sắp\s*xếp|sap xep|bubble|quick|merge))\b",
        re.I,
    ),
    re.compile(
        r"\b(?:thuật\s*toán|thuat toan|algorithm)\b[^.\n]{0,60}\b(?:python|javascript|code|sort)\b",
        re.I,
    ),
    re.compile(
        r"\b(?:viết\s+(?:một\s+)?(?:chương\s*trình|chuong trinh|script|hàm|ham|function)|"
        r"write\s+(?:a\s+)?(?:program|script|function|class))\b",
        re.I,
    ),
    # Debugging / errors / performance tuning of code
    re.compile(
        r"\b(?:debug|lỗi\s+compile|compile\s+error|stack\s+trace|traceback|"
        r"segfault|null\s+pointer|deadlock)\b",
        re.I,
    ),
    # Data structures & CS concepts
    re.compile(
        r"\b(?:linked\s*list|binary\s*tree|hash\s*table|dynamic\s*programming|"
        r"recursion|đệ\s*quy|de quy|time\s+complexity|big\s*o\s*notation|"
        r"độ\s+phức\s+tạp|do phuc tap|space\s+complexity)\b",
        re.I,
    ),
    # Pure math problems (not data/metadata)
    re.compile(
        r"\b(?:giải\s+phương\s*trình|giai phuong trinh|solve\s+(?:this\s+)?equation|"
        r"đạo\s*hàm|dao ham|tích\s*phân|tich phan|derivative|integral|"
        r"phương\s*trình\s+bậc|phuong trinh bac)\b",
        re.I,
    ),
    # Infrastructure / deployment / tooling
    re.compile(
        r"\b(?:docker|kubernetes|k8s|terraform|helm|nginx|ci/cd|pipelines?\s+config)\b",
        re.I,
    ),
    re.compile(r"\bcài\s+đặt|cai dat|deploy\b", re.I),
    # Business consulting / strategy
    re.compile(
        r"\b(?:business\s+plan|chiến\s+lược|chien luoc|roi\s*\(?\s*investment|"
        r"marketing\s+strategy)\b",
        re.I,
    ),
    # General world knowledge / off-topic
    re.compile(
        r"\b(?:weather|thời\s+tiết|thoi tiet|football\s+match|trận\s+bóng|tran bong|"
        r"recipe|công\s+thức\s+nấu|cong thuc nau|horoscope|bói)\b",
        re.I,
    ),
    re.compile(r"\b(?:translate\s+to|dịch\s+sang|dich sang)\b", re.I),
    # Geography / politics / history / entertainment / trivia
    re.compile(
        r"\b(?:thủ\s+đô\s+(?:của|of)\b|capital\s+of|năm\s+(?:sinh|ra\s+đời)|"
        r"tổng\s+thống|tong thong|president\s+of|diện\s+tích|dien tich|"
        r"dân\s+số|dan so|population\s+of)\b",
        re.I,
    ),
    re.compile(
        r"\b(?:cúp\s+thế\s+giới|cup the gioi|world\s+cup|thời\s+sự|thoi su|"
        r"tin\s+tức|tin tuc|news\s+about|latest\s+(?:news|score))\b",
        re.I,
    ),
    # Health / medical / lifestyle advice (outside business domain)
    re.compile(
        r"\b(?:triệu\s+chứng|trieu chung|symptom|chế\s+độ\s+ăn|che do an|"
        r"giảm\s+cân|giam can|lose\s+weight|bài\s+tập\s+thể\s+dục|bai tap the duc|"
        r"workout\s+routine|sleep\s+better)\b",
        re.I,
    ),
    # Finance/investment advice not tied to metadata
    re.compile(
        r"\b(?:giá\s+chứng\s+khoán|gia chung khoan|stock\s+price|bitcoin\s+price|"
        r"nên\s+mua\s+cổ\s+phiếu|nen mua co phieu|buy\s+this\s+stock|"
        r"forecast\s+(?:the\s+)?(?:stock|market))\b",
        re.I,
    ),
    # Writing essays / resumes / letters / creative writing
    re.compile(
        r"\b(?:viết\s+(?:một\s+)?(?:bài\s+luận|bai luan|thư\s+xin\s+việc|thu xin viec|"
        r"resume|cv\b|đơn\s+xin\s+việc|don xin viec)|write\s+(?:an?\s+)?(?:essay|resume|"
        r"cover\s+letter|cv))\b",
        re.I,
    ),
    # Date/time/calendar trivia unrelated to metadata
    re.compile(
        r"\b(?:hôm\s+nay\s+(?:là\s+)?(?:thứ\s+mấy|ngày\s+(?:bao\s+nhiêu|mấy))|"
        r"thứ\s+mấy\s+hôm\s+nay|today\s+(?:is\s+)?(?:what|which)\s+(?:day|date)|"
        r"what\s+(?:day|date)\s+is\s+(?:it\s+)?today|mấy\s+giờ|may gio|what\s+time\s+is\s+it)\b",
        re.I,
    ),
    # Numeric comparison / arithmetic puzzles (e.g. "9.11 vs 9.8 lớn hơn?")
    re.compile(
        r"\b(?:số\s+nào\s+lớn\s+hơn|so nao lon hon|"
        r"which\s+(?:number|is)\s+(?:larger|bigger)|"
        r"which\s+number\s+is\s+larger|which\s+is\s+(?:larger|bigger)|"
        r"lớn\s+hơn\b|lon hon\b|math\s+problem|bài\s+toán|bai toan)\b",
        re.I,
    ),
    # Jokes / entertainment / creative content
    re.compile(
        r"\b(?:kể\s+chuyện\s+cười|ke chuyen cuoi|tell\s+(?:me\s+)?a\s+joke|"
        r"kể\s+một\s+câu\s+chuyện|ke mot cau chuyen|write\s+(?:a\s+)?(?:poem|song|story))\b",
        re.I,
    ),
    # Trivia / general factual questions not about DataHub
    re.compile(
        r"\b(?:capital\s+of|thủ\s+đô\s+của|largest\s+country|biggest\s+city|"
        r"highest\s+mountain|chiều\s+cao\s+của|can nang cua|birth\s+date\s+of)\b",
        re.I,
    ),
]

_OUT_OF_SCOPE_RESPONSE = (
    "Câu hỏi này nằm ngoài phạm vi hỗ trợ của tôi. Tôi chỉ trả lời các câu hỏi về "
    "metadata trong DataHub (datasets, dashboards, glossary terms, schema, ownership, "
    "lineage, tags, domains)."
)

_OUT_OF_SCOPE_RESPONSE_EN = (
    "This request is outside the supported metadata scope. I can only answer "
    "questions about DataHub metadata (datasets, dashboards, glossary terms, schema, "
    "ownership, lineage, tags, domains)."
)


def _is_vietnamese(text: str) -> bool:
    return bool(re.search(r"[\u00E0-\u1EF9]", text, re.I)) or "đ" in text.lower()


def classify_scope(query: str) -> str:
    """Return ``"metadata"`` when in scope, ``"out_of_scope"`` otherwise."""
    if not query:
        return "out_of_scope"
    for pattern in _OUT_OF_SCOPE_PATTERNS:
        if pattern.search(query):
            log.info("scope_out_of_scope", pattern=pattern.pattern)
            return "out_of_scope"
    return "metadata"


def is_out_of_scope(query: str) -> bool:
    """True when the query clearly targets a domain outside metadata."""
    return classify_scope(query) == "out_of_scope"


def out_of_scope_response(query: str) -> str:
    """Canned response explaining the request is outside metadata scope."""
    if _is_vietnamese(query):
        return _OUT_OF_SCOPE_RESPONSE
    return _OUT_OF_SCOPE_RESPONSE_EN
