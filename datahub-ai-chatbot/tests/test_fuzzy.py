from retrieval.fuzzy import ascii_fold, fuzzy_score, normalize, tokenize


def test_ascii_fold_strips_vietnamese_accents() -> None:
    assert ascii_fold("Tồn kho Min Max") == "ton kho min max"
    assert ascii_fold("Đơn hàng") == "don hang"
    assert ascii_fold("Doanh thu") == "doanh thu"


def test_normalize_collapses_separators() -> None:
    assert normalize("sales.orders") == "sales orders"
    assert normalize("dim_material") == "dim material"
    assert normalize("  finance.monthly_revenue  ") == "finance monthly revenue"


def test_tokenize_skips_short_tokens() -> None:
    assert tokenize("sales orders") == ["sales", "orders"]
    assert tokenize("do") == []


def test_fuzzy_exact_and_typos() -> None:
    assert fuzzy_score("sales.orders", "sales.orders") == 1.0
    assert fuzzy_score("sales orderz", "sales.orders") > 0.9
    assert fuzzy_score("finace.monthly_revenue", "finance.monthly_revenue") > 0.9
    assert fuzzy_score("monthly revnue", "monthly_revenue") > 0.9


def test_fuzzy_vietnamese_phonetic() -> None:
    # Accent-free query still matches accented entity names.
    assert fuzzy_score("ton kho", "Tồn kho Min Max") > 0.9
    assert fuzzy_score("doanh thu", "Doanh thu") == 1.0


def test_fuzzy_does_not_match_unrelated() -> None:
    assert fuzzy_score("revenue", "sales.orders") < 0.5
    assert fuzzy_score("xyzabc", "sales.orders") < 0.3
