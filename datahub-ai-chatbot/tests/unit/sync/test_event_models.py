"""Test MetadataChangeEvent model."""
from sync.models import EventType, MetadataChangeEvent


def test_event_create():
    event = MetadataChangeEvent.create(
        event_type=EventType.CREATE,
        entity_urn="urn:li:dataset:test",
    )
    assert event.event_id
    assert event.event_type == EventType.CREATE
    assert event.entity_urn == "urn:li:dataset:test"


def test_event_infer_type_dataset():
    event = MetadataChangeEvent.create(
        EventType.UPDATE,
        "urn:li:dataset:(urn:li:dataPlatform:snowflake,test,PROD)",
    )
    assert event.entity_type == "dataset"


def test_event_infer_type_glossary():
    event = MetadataChangeEvent.create(
        EventType.UPDATE,
        "urn:li:glossaryTerm:Revenue",
    )
    assert event.entity_type == "glossary_term"


def test_event_infer_type_dashboard():
    event = MetadataChangeEvent.create(
        EventType.UPDATE,
        "urn:li:dashboard:MonthlyRevenue",
    )
    assert event.entity_type == "dashboard"


def test_event_infer_type_unknown():
    event = MetadataChangeEvent.create(
        EventType.UPDATE,
        "urn:li:unknown:Test",
    )
    assert event.entity_type == "unknown"
