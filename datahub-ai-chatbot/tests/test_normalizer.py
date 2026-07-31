from ingestion.models import CanonicalEntity
from ingestion.normalizer import compute_content_hash


def test_content_hash_is_deterministic(sample_dataset: CanonicalEntity) -> None:
    hash1 = compute_content_hash(sample_dataset)
    hash2 = compute_content_hash(sample_dataset)
    assert hash1 == hash2


def test_content_hash_changes_on_change(sample_dataset: CanonicalEntity) -> None:
    hash1 = compute_content_hash(sample_dataset)
    modified = sample_dataset.model_copy(update={"description": "Changed description"})
    hash2 = compute_content_hash(modified)
    assert hash1 != hash2


def test_content_hash_excludes_raw_payload(sample_dataset: CanonicalEntity) -> None:
    with_payload = sample_dataset.model_copy(update={"raw_payload": {"extra": "data"}})
    without = sample_dataset.model_copy(update={"raw_payload": None})
    assert compute_content_hash(with_payload) == compute_content_hash(without)


def test_content_hash_format(sample_dataset: CanonicalEntity) -> None:
    h = compute_content_hash(sample_dataset)
    assert isinstance(h, str)
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)
