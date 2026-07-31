import re

from config.constants import CHUNK_OVERLAP_TOKENS, CHUNK_TARGET_TOKENS


def _estimate_tokens(text: str) -> int:
    return len(text) // 4 + 1


def chunk_text(text: str, max_tokens: int = CHUNK_TARGET_TOKENS, overlap: int = CHUNK_OVERLAP_TOKENS) -> list[str]:
    if _estimate_tokens(text) <= max_tokens:
        return [text]

    chunks: list[str] = []
    paragraphs = re.split(r"\n\s*\n", text)
    current: list[str] = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = _estimate_tokens(para)
        if para_tokens > max_tokens:
            if current:
                chunks.append("\n\n".join(current))
                current = []
                current_tokens = 0
            sentences = re.split(r"(?<=[.?!])\s+", para)
            for sent in sentences:
                sent_tokens = _estimate_tokens(sent)
                if current_tokens + sent_tokens > max_tokens and current:
                    chunks.append("\n\n".join(current))
                    overlap_text = _get_overlap(current, overlap)
                    current = [overlap_text] if overlap_text else []
                    current_tokens = _estimate_tokens(overlap_text) if overlap_text else 0
                current.append(sent)
                current_tokens += sent_tokens
        elif current_tokens + para_tokens > max_tokens:
            chunks.append("\n\n".join(current))
            overlap_text = _get_overlap(current, overlap)
            current = [overlap_text] if overlap_text else []
            current_tokens = _estimate_tokens(overlap_text) if overlap_text else 0
            current.append(para)
            current_tokens += para_tokens
        else:
            current.append(para)
            current_tokens += para_tokens

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def _get_overlap(segments: list[str], overlap_tokens: int) -> str:
    combined = "\n\n".join(segments)
    tokens = combined.split()
    overlap_words = min(len(tokens), overlap_tokens * 4)
    if overlap_words <= 0:
        return ""
    return " ".join(tokens[-overlap_words:])
