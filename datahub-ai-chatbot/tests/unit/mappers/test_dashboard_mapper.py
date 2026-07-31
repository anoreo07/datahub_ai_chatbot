from ingestion.mappers.dashboard import DashboardMapper
from ingestion.models import CanonicalEntity

RAW_DASHBOARD = {
    "urn": "urn:li:dashboard:(mode,MonthlyRevenue)",
    "name": "Monthly Revenue",
    "description": "Dashboard theo dõi doanh thu theo tháng.",
    "properties": {"customProperties": {}},
    "platform": {"name": "mode"},
    "ownership": {
        "owners": [
            {
                "type": "DATA_OWNER",
                "owner": {
                    "username": "finance_analytics",
                    "info": {"displayName": "Finance Analytics"},
                },
            }
        ]
    },
    "domain": {
        "domains": [
            {"domain": {"urn": "urn:li:domain:Finance", "properties": {"name": "Finance"}}}
        ]
    },
}


def test_dashboard_mapper():
    mapper = DashboardMapper()
    result = mapper.to_canonical(RAW_DASHBOARD)
    assert isinstance(result, CanonicalEntity)
    assert result.entity_type == "dashboard"
    assert result.name == "Monthly Revenue"
    assert result.platform == "mode"
    assert result.domain == "Finance"
    assert len(result.owners) == 1
    assert result.owners[0].name == "finance_analytics"
