"""Mock LLM that generates deterministic responses based on structured evidence.
No API key required. No network calls."""

import re
from typing import Any

import structlog

from llm.base import BaseLLM

log = structlog.get_logger()


class MockLLM(BaseLLM):
    def __init__(self) -> None:
        self._model = "mock-llm-v1"

    async def generate(
        self,
        prompt: str,
        *,
        context: list[str] | None = None,
        history: list[tuple[str, str]] | None = None,
    ) -> str:
        context_str = "\n".join(context) if context else ""

        history_context = ""
        if history:
            history_lines = []
            for q, a in reversed(history[-3:]):
                history_lines.append(f"Previous Q: {q}")
                history_lines.append(f"Previous A: {a}")
            history_context = "\n".join(history_lines)

        intent = self._detect_intent(prompt)
        evidence = self._parse_evidence(context_str)

        referenced_entity = ""
        if not evidence and history:
            referenced_entity = self._resolve_from_history(prompt, history)
            if referenced_entity:
                return f"Theo ngữ cảnh trước đó, bạn đang nói về '{referenced_entity}'. Tuy nhiên, tôi không tìm thấy thông tin chi tiết từ metadata hiện có."

        if not evidence:
            return "Không tìm thấy thông tin này trong metadata mẫu hiện có."

        answer = self._build_answer(evidence, intent)
        return answer

    async def healthcheck(self) -> bool:
        return True

    async def generate_structured(self, prompt: str, context_xml: str = "",
                                  history: list[tuple[str, str]] | None = None) -> dict[str, Any]:
        answer = await self.generate(prompt, context=[context_xml] if context_xml else None, history=history)
        citation_ids: list[str] = []
        for m in re.finditer(r"urn:li:[^\s<>\"]+", context_xml):
            citation_ids.append(m.group())
        return {
            "answer": answer,
            "citation_ids": citation_ids,
            "confidence": "high" if citation_ids else "medium",
            "insufficient_context": not bool(citation_ids),
        }

    @staticmethod
    def _resolve_from_history(query: str, history: list[tuple[str, str]]) -> str:
        query_lower = query.lower().strip()
        for q_prev, a_prev in reversed(history):
            if "không tìm thấy" in a_prev.lower():
                continue
            q_lower = q_prev.lower().strip()
            name_match = re.search(r"(?:entity|')([^']+)'", a_prev)
            if name_match:
                return name_match.group(1)

            entity_in_q = re.sub(r"[^a-z0-9_\s]", " ", q_lower)
            for word in ["cho", "tôi", "biết", "về", "của", "nào", "gì",
                         "có", "không", "và", "hoặc", "là", "các",
                         "những", "được", "bạn", "thông", "tin",
                         "này", "đó", "nó", "ấy", "con"]:
                entity_in_q = entity_in_q.replace(word, " ")
            entity_in_q = re.sub(r"\s+", " ", entity_in_q).strip()
            if entity_in_q and len(entity_in_q) > 3:
                return entity_in_q
        return ""

    @staticmethod
    def _detect_intent(prompt: str) -> str:
        prompt_lower = prompt.lower()
        if "owner" in prompt_lower or "sở hữu" in prompt_lower:
            return "OWNER_LOOKUP"
        if "schema" in prompt_lower or "column" in prompt_lower or "cột" in prompt_lower or "field" in prompt_lower:
            return "SCHEMA_LOOKUP"
        if "definition" in prompt_lower or "nghĩa" in prompt_lower or "glossary" in prompt_lower:
            return "GLOSSARY_DEFINITION"
        if "upstream" in prompt_lower or "lineage" in prompt_lower or "lấy dữ liệu" in prompt_lower:
            return "UPSTREAM_LINEAGE"
        if "downstream" in prompt_lower or "ảnh hưởng" in prompt_lower:
            return "DOWNSTREAM_LINEAGE"
        if "domain" in prompt_lower:
            return "DOMAIN_LOOKUP"
        return "GENERAL"

    @staticmethod
    def _parse_evidence(context_str: str) -> list[dict]:
        if not context_str.strip():
            return []
        lines = context_str.split("\n")
        evidence = []
        current: dict[str, Any] = {}
        for line in lines:
            line = line.strip()
            if line.startswith("<entity") or line.startswith("<chunk"):
                if current:
                    evidence.append(current)
                current = {"raw": line}
            elif "urn:" in line:
                urns = re.findall(r"urn:li:[^\s<>\"]+", line)
                if urns:
                    current["urn"] = urns[0]
            elif "name:" in line.lower() and ":" in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    key = parts[0].strip().lower()
                    val = parts[1].strip()
                    current[key] = val
        if current:
            evidence.append(current)
        if not evidence:
            for line in lines[:20]:
                evidence.append({"raw": line})
        return evidence

    @staticmethod
    def _build_answer(evidence: list[dict], intent: str) -> str:
        parts = []
        for item in evidence[:3]:
            name = item.get("name", item.get("entity_name", item.get("raw", "")))[:80]
            if intent == "OWNER_LOOKUP" and item.get("urn"):
                parts.append(f"Entity {name} (URN: {item['urn'][:60]}) có thông tin trong hệ thống.")
            elif intent == "SCHEMA_LOOKUP":
                parts.append(f"Thông tin schema cho {name} có trong metadata mẫu.")
            elif intent == "GLOSSARY_DEFINITION":
                if name:
                    parts.append(f"Glossary term {name} được định nghĩa trong hệ thống.")
            else:
                parts.append(f"{name}: thông tin có trong dữ liệu mẫu.")
        if not parts:
            return "Không tìm thấy thông tin này trong metadata mẫu hiện có."
        return " ".join(parts)
