import os
from pathlib import Path

os.environ["USE_MOCK_DATAHUB"] = "true"
os.environ["MOCK_DATAHUB_FIXTURES_PATH"] = str(Path(__file__).parent / "fixtures" / "datahub")
os.environ["EMBEDDING_PROVIDER"] = "mock"
os.environ["EMBEDDING_MODEL"] = "mock-hash-v1"
os.environ["EMBEDDING_DIMENSION"] = "384"
os.environ["LLM_PROVIDER"] = "fireworks"
os.environ["USE_MOCK_LLM"] = "true"
os.environ["FIREWORKS_API_KEY"] = ""
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5433/chatbot_test"
os.environ["REDIS_URL"] = "redis://localhost:6380/1"
os.environ["OPENSEARCH_URL"] = "http://localhost:9201"
os.environ["OPENSEARCH_INDEX"] = "datahub-rag-chunks-test-v1"
os.environ["APP_ENV"] = "test"
os.environ["DATAHUB_FRONTEND_URL"] = "http://localhost:9002"
os.environ["LOCAL_STORAGE_PATH"] = "/tmp/datahub_test_storage"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-secure-and-long-enough-32-chars"

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from config.settings import settings
from database.models import Base
from indexing.embedder import MockEmbedder
from ingestion.mock_source import MockDataHubSource
from ingestion.models import CanonicalEntity


@pytest.fixture(scope="session")
def event_loop():
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db() -> AsyncGenerator[None, None]:
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool, echo=False)
    async with engine.connect() as conn:
        transaction = await conn.begin()
        async_session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield async_session
        finally:
            await async_session.close()
            await transaction.rollback()
    await engine.dispose()



@pytest.fixture
def mock_source() -> MockDataHubSource:
    return MockDataHubSource()


@pytest.fixture
def mock_embedder() -> MockEmbedder:
    return MockEmbedder()


@pytest.fixture
def sample_dataset() -> CanonicalEntity:
    return CanonicalEntity(
        urn="urn:li:dataset:(urn:li:dataPlatform:snowflake,sales.orders,PROD)",
        entity_type="dataset",
        name="sales.orders",
        display_name="sales.orders",
        description="Bảng lưu thông tin đơn hàng đã xác nhận.",
        platform="snowflake",
        environment="PROD",
        domain="Sales",
        owners=[{"name": "Sales Analytics", "type": "USER"}],
        glossary_terms=[
            "urn:li:glossaryTerm:Order",
            "urn:li:glossaryTerm:Customer",
            "urn:li:glossaryTerm:Revenue",
        ],
        schema_fields=[
            {"name": "order_id", "type": "string", "description": "Mã đơn hàng duy nhất"},
            {"name": "customer_id", "type": "string", "description": "Mã khách hàng"},
            {"name": "gross_revenue", "type": "decimal", "description": "Doanh thu gộp"},
            {"name": "net_revenue", "type": "decimal", "description": "Doanh thu thuần"},
            {"name": "created_at", "type": "timestamp", "description": "Thời gian tạo"},
        ],
        upstreams=[],
        downstreams=["urn:li:dataset:(urn:li:dataPlatform:snowflake,finance.monthly_revenue,PROD)"],
        linked_documents=[],
        datahub_url="http://localhost:9002/dataset/urn:li:dataset:(urn:li:dataPlatform:snowflake,sales.orders,PROD)",
        raw_payload=None,
    )


@pytest.fixture
def sample_glossary_term() -> CanonicalEntity:
    return CanonicalEntity(
        urn="urn:li:glossaryTerm:NetRevenue",
        entity_type="glossary_term",
        name="NetRevenue",
        display_name="Net Revenue",
        description="Doanh thu còn lại sau khi trừ hoàn tiền, giảm giá và chiết khấu.",
        domain="Finance",
        owners=[{"name": "Finance Analytics", "type": "USER"}],
        glossary_terms=[],
        schema_fields=[],
        upstreams=[],
        downstreams=[],
        linked_documents=[],
        datahub_url="http://localhost:9002/glossary/urn:li:glossaryTerm:NetRevenue",
        raw_payload=None,
    )


@pytest.fixture
def sample_dashboard() -> CanonicalEntity:
    return CanonicalEntity(
        urn="urn:li:dashboard:MonthlyRevenue",
        entity_type="dashboard",
        name="Monthly Revenue",
        display_name="Monthly Revenue",
        description="Dashboard theo dõi doanh thu theo tháng.",
        platform="mode",
        environment="PROD",
        domain="Finance",
        owners=[{"name": "Finance Analytics", "type": "USER"}],
        glossary_terms=[],
        schema_fields=[],
        upstreams=["urn:li:dataset:(urn:li:dataPlatform:snowflake,finance.monthly_revenue,PROD)"],
        downstreams=[],
        linked_documents=[],
        datahub_url="http://localhost:9002/dashboard/urn:li:dashboard:MonthlyRevenue",
        raw_payload=None,
    )


@pytest.fixture
def all_fixture_data(mock_source: MockDataHubSource) -> list[CanonicalEntity]:
    return list(mock_source.list_all())
