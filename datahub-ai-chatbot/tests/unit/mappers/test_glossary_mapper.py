from ingestion.mappers.glossary import GlossaryTermMapper
from ingestion.models import CanonicalEntity

RAW_TERM = {
    "urn": "urn:li:glossaryTerm:Revenue",
    "name": "Revenue",
    "description": "Doanh thu tổng từ hoạt động kinh doanh.",
    "ownership": {
        "owners": [
            {
                "type": "DATA_OWNER",
                "owner": {
                    "username": "finance_team",
                    "info": {"displayName": "Finance Team"},
                },
            }
        ]
    },
    "domain": {
        "domains": [
            {"domain": {"urn": "urn:li:domain:Finance", "properties": {"name": "Finance"}}}
        ]
    },
    "relatedEntities": {
        "total": 2,
        "relationships": [
            {"entity": {"urn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,sales.orders,PROD)", "type": "dataset"}},
        ],
    },
}


def test_glossary_term_mapper():
    mapper = GlossaryTermMapper()
    result = mapper.to_canonical(RAW_TERM)
    assert isinstance(result, CanonicalEntity)
    assert result.entity_type == "glossary_term"
    assert result.name == "Revenue"
    assert result.domain == "Finance"
    assert len(result.owners) == 1
    assert len(result.downstreams) == 1
    assert "sales.orders" in result.downstreams[0]
