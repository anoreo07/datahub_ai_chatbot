"""Mapper + normalizer name-cleaning tests (P0 data normalization)."""
from ingestion.mappers.dashboard import DashboardMapper
from ingestion.mappers.dataset import DatasetMapper
from ingestion.mappers.glossary import GlossaryTermMapper
from ingestion.normalizer import clean_name


def test_clean_name_trims_and_collapses():
    assert clean_name("  EV VIN Battery Report") == "EV VIN Battery Report"
    assert clean_name("Báo cáo chi tiết cấu hình xe ") == "Báo cáo chi tiết cấu hình xe"
    assert clean_name("a   b  c") == "a b c"
    assert clean_name(None) is None
    assert clean_name("   ") is None
    assert clean_name("") is None


def test_dataset_mapper_cleans_name():
    raw = {
        "urn": "urn:li:dataset:(urn:li:dataPlatform:redshift,ev_vin_battery,PROD)",
        "name": "  EV VIN Battery Report ",
        "displayName": " EV VIN Battery Report ",
        "platform": {"name": " redshift "},
        "properties": {},
    }
    ent = DatasetMapper().to_canonical(raw, url_builder=None)
    assert ent.name == "EV VIN Battery Report"
    assert ent.display_name == "EV VIN Battery Report"
    assert ent.platform == "redshift"


def test_dashboard_mapper_cleans_name():
    raw = {
        "urn": "urn:li:dashboard:(powerbi,reports.x)",
        "name": "  Báo cáo PFEP  ",
        "displayName": " Báo cáo PFEP  ",
        "platform": {"name": "powerbi"},
        "properties": {},
    }
    ent = DashboardMapper().to_canonical(raw, url_builder=None)
    assert ent.name == "Báo cáo PFEP"
    assert ent.display_name == "Báo cáo PFEP"


def test_glossary_mapper_cleans_name():
    raw = {
        "urn": "urn:li:glossaryTerm:abc",
        "name": "  Premium Shipment Car- Actual  ",
        "displayName": "  Premium Shipment Car- Actual ",
        "properties": {},
    }
    ent = GlossaryTermMapper().to_canonical(raw, url_builder=None)
    assert ent.name == "Premium Shipment Car- Actual"
    assert ent.display_name == "Premium Shipment Car- Actual"
