"""Synonym expander and natural language query normalizer."""

from __future__ import annotations

import re
import unicodedata


class SynonymExpander:
    """Expands business/technical synonyms and abbreviations for BM25 and hybrid search."""

    ABBREVIATION_MAP: dict[str, list[str]] = {
        "bc": ["baocao", "bao cao", "report", "dashboard"],
        "dt": ["doanhthu", "doanh thu", "revenue"],
        "kh": ["khachhang", "khach hang", "customer"],
        "sl": ["soluong", "so luong", "quantity"],
        "gt": ["giatri", "gia tri", "value"],
        "nv": ["nhanvien", "nhan vien", "employee", "staff"],
        "sp": ["sanpham", "san pham", "product"],
        "dh": ["donhang", "don hang", "order", "sales order"],
        "ql": ["quanly", "quan ly", "manager", "management"],
        "tc": ["taichinh", "tai chinh", "finance"],
        "kd": ["kinhdoanh", "kinh doanh", "sales", "business"],
        "ns": ["nhansu", "nhan su", "hr", "human resources"],
        "kho": ["warehouse", "inventory", "ton kho"],
        "don hang": ["sales_order", "orders", "order_details"],
        "khach hang": ["customer", "dim_customer"],
        "nhan vien": ["employee", "dim_employee", "staff"],
        "san pham": ["product", "dim_product", "item"],
        "kho hang": ["warehouse", "dim_warehouse"],
    }

    CONCEPT_SYNONYMS: dict[str, list[str]] = {
        "lineage": [
            "nguồn", "upstream", "downstream", "data flow", "feed", "phụ thuộc",
            "dữ liệu từ đâu", "bảng nguồn", "bảng đích"
        ],
        "schema": [
            "cột", "trường", "field", "column", "cấu trúc", "thuộc tính", "metadata"
        ],
        "quality": [
            "chất lượng", "độ chính xác", "null", "freshness", "tin cậy", "completeness"
        ],
        "owner": [
            "chủ sở hữu", "người quản lý", "team phụ trách", "ai quản lý", "chịu trách nhiệm"
        ],
        "domain": [
            "lĩnh vực", "miền dữ liệu", "nghiệp vụ"
        ],
    }

    @staticmethod
    def _norm(s: str) -> str:
        s = s.lower().strip()
        s = s.replace("đ", "d").replace("Đ", "d")
        s = unicodedata.normalize("NFKD", s)
        return s.encode("ascii", "ignore").decode("ascii")

    def normalize_query(self, query: str) -> str:
        """Strip conversational fillers and normalize characters."""
        q = re.sub(r"[?!.,;:\"']+", " ", query)
        q = re.sub(r"\s+", " ", q).strip()
        return q

    def expand_query(self, query: str) -> list[str]:
        """Generate expanded search terms including synonyms and abbreviations."""
        normalized = self.normalize_query(query)
        q_ascii = self._norm(normalized)
        tokens = q_ascii.split()

        expansions: list[str] = [normalized]
        added_terms: set[str] = {normalized.lower(), q_ascii}

        # 1. Expand single token abbreviations
        for tok in tokens:
            if tok in self.ABBREVIATION_MAP:
                for replacement in self.ABBREVIATION_MAP[tok]:
                    candidate = re.sub(rf"\b{re.escape(tok)}\b", replacement, q_ascii, flags=re.I)
                    if candidate.lower() not in added_terms:
                        expansions.append(candidate)
                        added_terms.add(candidate.lower())

        # 2. Multi-word phrase expansions
        for phrase, replacements in self.ABBREVIATION_MAP.items():
            if " " in phrase and phrase in q_ascii:
                for rep in replacements:
                    candidate = q_ascii.replace(phrase, rep)
                    if candidate.lower() not in added_terms:
                        expansions.append(candidate)
                        added_terms.add(candidate.lower())

        return expansions[:6]
