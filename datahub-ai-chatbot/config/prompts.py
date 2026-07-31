SYSTEM_PROMPT = """You are a helpful assistant for DataHub.
Answer questions based on the provided context about data entities,
glossary terms, and data lineage.

If you cannot answer from the context, say so clearly.
Do NOT make up entities, names, URNs, or data that is not in the context.
"""

CHAT_PROMPT_TEMPLATE = """Context:
{context}

Question: {query}

Answer concisely based on the context above.
If the context does not contain enough information to answer, say "I don't have enough information to answer this question."
"""

NO_ANSWER_RESPONSE = "Xin lỗi, tôi không có đủ thông tin để trả lời câu hỏi này. Vui lòng thử hỏi lại với câu hỏi khác hoặc cung cấp thêm chi tiết."

ACCESS_DENIED_RESPONSE = "Thông tin này không thể truy cập bởi phòng ban của bạn. Vui lòng đăng nhập bằng tài khoản có quyền truy cập phù hợp hoặc liên hệ quản trị viên để được cấp quyền."

NO_ANSWER_FALLBACKS = [
    "không tìm thấy dữ liệu phù hợp",
    "không có đủ thông tin",
    "I don't have enough information",
    "không thể trả lời",
]

INTENT_CLASSIFICATION_PROMPT = """Classify the user query into one of:
- TERM_DEFINITION
- FIND_ENTITY
- OWNER_LOOKUP
- TERM_TO_DATASETS
- LINEAGE
- SCHEMA_LOOKUP
- DOCUMENT_QA
- GENERAL

Query: {query}

Intent:
"""
