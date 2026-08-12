"""Shared normalization helpers for the authorization / domain layer."""

import unicodedata


def norm_vn(s: str | None) -> str:
    """ASCII-fold a Vietnamese string for accent/case-insensitive matching."""
    if not s:
        return ""
    s = s.lower()
    s = s.replace("đ", "d").replace("Đ", "d")
    s = unicodedata.normalize("NFKD", s)
    return s.encode("ascii", "ignore").decode("ascii")


def domain_key(domain: str | None) -> str:
    """Canonical normalized key for a domain name."""
    return norm_vn(domain)


def domains_match(a: str | None, b: str | None) -> bool:
    key_a = domain_key(a)
    key_b = domain_key(b)
    if not key_a or not key_b:
        return False
    return key_a == key_b or key_a in key_b or key_b in key_a
