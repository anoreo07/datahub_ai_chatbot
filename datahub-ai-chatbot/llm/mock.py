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
        system_prompt: str | None = None,
    ) -> str:
        context_str = "\n".join(context) if context else ""

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
        if "domain" in prompt_lower or "lĩnh vực" in prompt_lower \
                or "linh vuc" in prompt_lower or "miền" in prompt_lower:
            return "DOMAIN_LOOKUP"
        if ("owner" in prompt_lower or "sở hữu" in prompt_lower or "so huu" in prompt_lower
                or "của ai" in prompt_lower or "cua ai" in prompt_lower
                or "thuộc về ai" in prompt_lower or "thuộc ai" in prompt_lower):
            return "OWNER_LOOKUP"
        if "schema" in prompt_lower or "column" in prompt_lower or "cột" in prompt_lower or "field" in prompt_lower:
            return "SCHEMA_LOOKUP"
        if "definition" in prompt_lower or "nghĩa" in prompt_lower or "glossary" in prompt_lower:
            return "GLOSSARY_DEFINITION"
        if ("upstream" in prompt_lower or "lineage" in prompt_lower
                or "lấy dữ liệu" in prompt_lower or "lấy từ đâu" in prompt_lower
                or "nguồn" in prompt_lower or "nguon" in prompt_lower):
            return "UPSTREAM_LINEAGE"
        if "downstream" in prompt_lower or "ảnh hưởng" in prompt_lower:
            return "DOWNSTREAM_LINEAGE"
        return "GENERAL"

    @staticmethod
    def _parse_evidence(context_str: str) -> list[dict[str, Any]]:
        if not context_str.strip():
            return []
        evidence = []
        for m in re.finditer(r"<entity[^>]*>(.*?)</entity>", context_str, re.S):
            block = m.group(1)
            entry: dict[str, Any] = {}
            name = re.search(r"<name>(.*?)</name>", block, re.S)
            if name:
                entry["name"] = name.group(1).strip()
            content = re.search(r"<content>(.*?)</content>", block, re.S)
            if content:
                entry["content"] = content.group(1).strip()
            urn = re.search(r"urn:li:[^\s<>\"]+", block)
            if urn:
                entry["urn"] = urn.group(0)
            if entry:
                evidence.append(entry)
        if not evidence:
            for line in context_str.splitlines()[:20]:
                if line.strip():
                    evidence.append({"raw": line.strip()})
        return evidence

    @staticmethod
    def _extract_content_fields(content: str) -> dict[str, str]:
        """Parse 'Key: value | Key: value' blocks produced by the context builder."""
        fields: dict[str, str] = {}
        if not content:
            return fields
        pattern = re.compile(
            r"\b(Name|Description|Domain|Platform|Owners|Glossary terms|Upstream|Downstream)\s*:\s*([^|]*)",
            re.I,
        )
        for m in pattern.finditer(content):
            key = m.group(1).strip().lower()
            value = m.group(2).strip()
            if key not in fields or value:
                fields[key] = value
        return fields

    @staticmethod
    def _build_answer(evidence: list[dict[str, Any]], intent: str) -> str:
        parts = []
        for item in evidence[:3]:
            content = item.get("content", "")
            fields = MockLLM._extract_content_fields(content)
            name = fields.get("name") or item.get("name") or item.get("raw", "")
            if intent == "OWNER_LOOKUP":
                owners = fields.get("owners")
                if owners:
                    parts.append(f"{name} được sở hữu bởi {owners}.")
                else:
                    parts.append(f"{name} hiện chưa có thông tin owner trong hệ thống.")
            elif intent == "DOMAIN_LOOKUP":
                domain = fields.get("domain")
                if domain:
                    parts.append(f"{name} thuộc về domain {domain}.")
                else:
                    parts.append(f"{name} không có thông tin domain được ghi nhận.")
            elif intent == "SCHEMA_LOOKUP":
                if "Schema fields" in content:
                    parts.append(f"Thông tin schema của {name} đã có trong metadata mẫu.")
                else:
                    parts.append(f"Chưa có thông tin schema cho {name}.")
            elif intent in ("UPSTREAM_LINEAGE", "DOWNSTREAM_LINEAGE"):
                if "Upstream" in content or "Downstream" in content:
                    parts.append(f"Thông tin lineage của {name} đã có trong metadata.")
                else:
                    parts.append(f"{name} hiện chưa có thông tin lineage được ghi nhận.")
            elif intent == "GLOSSARY_DEFINITION":
                desc = fields.get("description")
                if desc:
                    parts.append(f"{name}: {desc}")
                else:
                    parts.append(f"Glossary term {name} được định nghĩa trong hệ thống.")
            else:
                desc = fields.get("description")
                if desc:
                    parts.append(f"{name}: {desc}")
                else:
                    parts.append(f"{name}: thông tin có trong dữ liệu mẫu.")
        if not parts:
            return "Không tìm thấy thông tin này trong metadata mẫu hiện có."
        return " ".join(parts)
