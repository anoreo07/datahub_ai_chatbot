import pytest

from database.models import Entity
from database.repositories.entity_repository import EntityRepository


def _make_dataset(urn: str, name: str, domain: str) -> Entity:
    return Entity(
        urn=urn,
        entity_type="dataset",
        name=name,
        display_name=name,
        platform="redshift",
        environment="PROD",
        domain=domain,
        datahub_url=f"http://localhost:9002/dataset/{urn}",
        payload={"domain": domain},
        content_hash=f"hash-{name}",
    )


def _make_glossary_term(urn: str, name: str) -> Entity:
    return Entity(
        urn=urn,
        entity_type="glossary_term",
        name=name,
        display_name=name,
        platform="",
        environment="PROD",
        domain="",
        datahub_url=f"http://localhost:9002/glossaryTerm/{urn}",
        payload={"description": f"Definition of {name}"},
        content_hash=f"hash-{name}",
    )


def _make_service(db_session):
    from app.services.chat_service import ChatService
    return ChatService(db_session)


@pytest.mark.asyncio
async def test_count_datasets_by_domain_linh_vuc(db_session) -> None:
    repo = EntityRepository(db_session)
    for i in range(15):
        await repo.upsert(_make_dataset(f"urn:test:fin:{i}", f"dim_fin_{i}", "TÀI CHÍNH"))
    for i in range(5):
        await repo.upsert(_make_dataset(f"urn:test:log:{i}", f"dim_log_{i}", "LOGISTIC"))

    service = _make_service(db_session)
    response = await service.answer("Lĩnh vực tài chính có bao nhiêu datasets?")

    assert response.intent == "COUNT_ENTITIES"
    assert response.confidence == "high"
    assert not response.insufficient_context
    assert "15" in response.answer
    assert "TÀI CHÍNH" in response.answer
    assert len(response.entities) == 15
    for i in range(15):
        assert f"dim_fin_{i}" in response.answer
    assert not any(f"dim_log_{i}" in response.answer for i in range(5))


@pytest.mark.asyncio
async def test_count_datasets_by_domain_english_keyword(db_session) -> None:
    repo = EntityRepository(db_session)
    for i in range(15):
        await repo.upsert(_make_dataset(f"urn:test:fin:{i}", f"dim_fin_{i}", "TÀI CHÍNH"))
    for i in range(5):
        await repo.upsert(_make_dataset(f"urn:test:log:{i}", f"dim_log_{i}", "LOGISTIC"))

    service = _make_service(db_session)
    response = await service.answer("How many datasets are in domain TÀI CHÍNH?")

    assert response.intent == "COUNT_ENTITIES"
    assert "15" in response.answer
    assert len(response.entities) == 15


@pytest.mark.asyncio
async def test_list_datasets_by_domain_linh_vuc(db_session) -> None:
    repo = EntityRepository(db_session)
    for i in range(15):
        await repo.upsert(_make_dataset(f"urn:test:fin:{i}", f"dim_fin_{i}", "TÀI CHÍNH"))
    for i in range(5):
        await repo.upsert(_make_dataset(f"urn:test:log:{i}", f"dim_log_{i}", "LOGISTIC"))

    service = _make_service(db_session)
    response = await service.answer("Lĩnh vực tài chính gồm những dataset nào")

    assert response.intent == "DOMAIN_QUERY"
    assert response.confidence == "high"
    assert "15" in response.answer
    assert len(response.entities) == 15
    assert not any(f"dim_log_{i}" in response.answer for i in range(5))


@pytest.mark.asyncio
async def test_count_all_datasets(db_session) -> None:
    repo = EntityRepository(db_session)
    for i in range(15):
        await repo.upsert(_make_dataset(f"urn:test:fin:{i}", f"dim_fin_{i}", "TÀI CHÍNH"))
    for i in range(5):
        await repo.upsert(_make_dataset(f"urn:test:log:{i}", f"dim_log_{i}", "LOGISTIC"))

    service = _make_service(db_session)
    response = await service.answer("Có bao nhiêu datasets?")

    assert response.intent == "COUNT_ENTITIES"
    assert "20" in response.answer
    assert len(response.entities) == 20


@pytest.mark.asyncio
async def test_count_no_match_returns_zero(db_session) -> None:
    repo = EntityRepository(db_session)
    for i in range(15):
        await repo.upsert(_make_dataset(f"urn:test:fin:{i}", f"dim_fin_{i}", "TÀI CHÍNH"))

    service = _make_service(db_session)
    response = await service.answer("Lĩnh vực marketing có bao nhiêu datasets?")

    assert response.intent == "COUNT_ENTITIES"
    assert "0" in response.answer
    assert len(response.entities) == 0


@pytest.mark.asyncio
async def test_list_all_domains_deterministic(db_session) -> None:
    repo = EntityRepository(db_session)
    for i in range(15):
        await repo.upsert(_make_dataset(f"urn:test:fin:{i}", f"dim_fin_{i}", "TÀI CHÍNH"))
    for i in range(5):
        await repo.upsert(_make_dataset(f"urn:test:log:{i}", f"dim_log_{i}", "LOGISTIC"))

    service = _make_service(db_session)
    response = await service.answer("có các domain nào?")

    assert response.intent == "DOMAIN_QUERY"
    assert response.confidence == "high"
    assert not response.insufficient_context
    assert "Có tổng cộng 2 domain" in response.answer
    assert "- TÀI CHÍNH (15 assets)" in response.answer
    assert "- LOGISTIC (5 assets)" in response.answer


@pytest.mark.asyncio
async def test_list_all_domains_vietnamese_variants(db_session) -> None:
    repo = EntityRepository(db_session)
    await repo.upsert(_make_dataset("urn:test:fin:0", "dim_fin_0", "TÀI CHÍNH"))
    await repo.upsert(_make_dataset("urn:test:log:0", "dim_log_0", "LOGISTIC"))

    service = _make_service(db_session)
    for question in [
        "liệt kê các domain",
        "danh sách domain",
        "các domain trong hệ thống",
        "liệt kê các lĩnh vực",
    ]:
        response = await service.answer(question)
        assert response.intent == "DOMAIN_QUERY", question
        assert "Có tổng cộng 2 domain" in response.answer, question


@pytest.mark.asyncio
async def test_count_all_domains(db_session) -> None:
    repo = EntityRepository(db_session)
    for i in range(15):
        await repo.upsert(_make_dataset(f"urn:test:fin:{i}", f"dim_fin_{i}", "TÀI CHÍNH"))
    for i in range(5):
        await repo.upsert(_make_dataset(f"urn:test:log:{i}", f"dim_log_{i}", "LOGISTIC"))

    service = _make_service(db_session)
    response = await service.answer("có bao nhiêu domain?")

    assert response.intent == "DOMAIN_QUERY"
    assert response.answer == "Có tổng cộng 2 domain trong hệ thống."


@pytest.mark.asyncio
async def test_detect_entity_type(db_session) -> None:
    from app.services.chat_service import ChatService

    assert ChatService._detect_entity_type("Có bao nhiêu datasets?") == "dataset"
    assert ChatService._detect_entity_type("có bao nhiêu dashboard?") == "dashboard"
    assert ChatService._detect_entity_type("có bao nhiêu glossary terms?") == "glossary_term"
    assert ChatService._detect_entity_type("có bao nhiêu assets?") is None
    assert ChatService._detect_entity_type("Có bao nhiêu datasets?") == "dataset"


def test_detect_listing_glossary_terms_variants() -> None:
    from app.services.chat_service import ChatService

    for question in [
        "Có những glossary terms nào?",
        "có những glossary term nào?",
        "có các glossary terms",
        "có các glossary terms nào",
        "liệt kê glossary terms",
        "danh sách glossary terms",
        "show glossary terms",
        "list glossary terms",
    ]:
        assert ChatService._detect_listing(question) == "glossary_term", question


@pytest.mark.asyncio
async def test_list_glossary_terms_full_from_db(db_session) -> None:
    repo = EntityRepository(db_session)
    for i in range(20):
        await repo.upsert(_make_glossary_term(f"urn:li:glossaryTerm:gt{i}", f"Term {i}"))
    for i in range(3):
        await repo.upsert(_make_dataset(f"urn:test:ds:{i}", f"dim_other_{i}", "FINANCE"))

    service = _make_service(db_session)
    response = await service.answer("Có những glossary terms nào?")

    assert response.intent == "LISTING"
    assert response.confidence == "high"
    assert "20" in response.answer
    assert len(response.entities) == 20
    assert "Term 0, Term 1, Term 10" in response.answer
    assert "..." in response.answer
    assert not any(f"dim_other_{i}" in response.answer for i in range(3))
    names_in_entities = {e.name for e in response.entities}
    assert len(names_in_entities) == 20


@pytest.mark.asyncio
async def test_list_glossary_terms_lietke(db_session) -> None:
    repo = EntityRepository(db_session)
    for i in range(10):
        await repo.upsert(_make_glossary_term(f"urn:li:glossaryTerm:gt{i}", f"Term {i}"))

    service = _make_service(db_session)
    response = await service.answer("liệt kê glossary terms")

    assert response.intent == "LISTING"
    assert "10" in response.answer
    assert len(response.entities) == 10
