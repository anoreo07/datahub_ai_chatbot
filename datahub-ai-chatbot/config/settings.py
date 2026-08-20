from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "DataHub AI Chatbot"
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    USE_MOCK_DATAHUB: bool = False
    MOCK_DATAHUB_FIXTURES_PATH: str = "app/data/mock_datahub"
    MOCK_DATA_PATH: str = "app/data/mock_datahub"
    DATAHUB_GMS_URL: str = "http://localhost:8080"
    DATAHUB_FRONTEND_URL: str = "http://localhost:9002"
    DATAHUB_TOKEN: str = ""
    DATAHUB_PAGE_SIZE: int = 100
    DATAHUB_REQUEST_TIMEOUT_SECONDS: int = 30
    DATAHUB_MAX_RETRIES: int = 3
    DATAHUB_SYNC_DRY_RUN: bool = False

    USE_MOCK_LLM: bool = False
    USE_MOCK_EMBEDDING: bool = False
    USE_FAKE_OPENSEARCH: bool = False
    USE_IN_MEMORY_DATABASE: bool = False
    USE_IN_MEMORY_QUEUE: bool = False
    ENABLE_NETWORK_ACCESS: bool = True

    AUTH_MODE: str = "jwt"
    AUTH_REQUIRED: bool = True
    JWT_SECRET_KEY: str = ""
    ENABLE_DEV_ENDPOINTS: bool = True

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/chatbot"
    REDIS_URL: str = "redis://localhost:6380/0"

    OPENSEARCH_URL: str = "http://localhost:9201"
    OPENSEARCH_INDEX: str = "datahub-rag-chunks-v1"
    OPENSEARCH_USERNAME: str = ""
    OPENSEARCH_PASSWORD: str = ""

    EMBEDDING_PROVIDER: str = "ollama"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    EMBEDDING_DIMENSION: int = 768
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"

    LLM_PROVIDER: str = "fireworks"
    LLM_MODEL: str = "accounts/fireworks/models/deepseek-v4-flash-0731"

    COHERE_API_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    OPENAI_API_KEY: str = ""

    FIREWORKS_API_KEY: str = ""
    FIREWORKS_MODEL_ID: str = "accounts/fireworks/models/deepseek-v4-flash-0731"

    NVIDIA_API_KEY: str = ""
    NVIDIA_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_MODEL_ID: str = "meta/llama-3.3-70b-instruct"

    SEARCH_CACHE_TTL_SECONDS: int = 300
    INDEX_MAX_RETRIES: int = 3
    INDEX_BATCH_SIZE: int = 20
    INDEX_POLL_INTERVAL_SECONDS: int = 2
    HEALTHCHECK_INTERVAL_SECONDS: int = 300
    HEALTHCHECK_LOG_TTL_SECONDS: int = 86400
    HEALTHCHECK_MAX_LOGS: int = 200

    LLM_TIMEOUT_SECONDS: int = 60
    LLM_MAX_RETRIES: int = 2

    MAX_CONTEXT_CHUNKS: int = 8
    MAX_CONTEXT_CHARACTERS: int = 24000

    EVALUATION_GOLDEN_DATASET_PATH: str = ""
    EVALUATION_SIMILARITY_THRESHOLD: float = 0.5
    ENTITY_RESOLVER_EXACT_THRESHOLD: float = 1.0
    ENTITY_RESOLVER_HIGH_THRESHOLD: float = 0.9
    ENTITY_RESOLVER_SUBSTRING_THRESHOLD: float = 0.7
    ENTITY_RESOLVER_AMBIGUITY_MARGIN: float = 0.2
    # Minimum score required to trust an entity resolution without asking the
    # user to confirm. Below this, TERM_DEFINITION returns no results so the
    # suggestion flow (Ý bạn là X?) kicks in instead of generating off a
    # low-confidence fuzzy/substring match (e.g. "ABV Matching" -> "3-Way Matching").
    ENTITY_RESOLVER_TRUST_THRESHOLD: float = 0.85
    ENTITY_RESOLVER_FUZZY_MIN_THRESHOLD: float = 0.6
    ENTITY_RESOLVER_FUZZY_MAX_CANDIDATES: int = 8

    RATE_LIMIT_MAX_REQUESTS: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_ENABLED: bool = True
    CACHE_ENABLED: bool = True
    CACHE_DEFAULT_TTL_SECONDS: int = 300

    # Graph reasoning / recursive impact analysis.
    GRAPH_MAX_DEPTH: int = 3
    GRAPH_DIRECT_DEPTH: int = 1
    IMPACT_MAX_NODES: int = 200
    IMPACT_DEFAULT_DEPTH: int = 3
    INTENT_CLASSIFIER_ENABLED: bool = True
    QUERY_PLANNER_ENABLED: bool = True
    PLANNER_FALLBACK_TO_REGEX: bool = True

    # Thinking Mode: an independent planning/reasoning layer for complex /
    # system-level / multi-hop questions (see retrieval/thinking/).
    THINKING_MODE_ENABLED: bool = True
    THINKING_MAX_STEPS: int = 8

    # Query Understanding: an optional LLM layer that reads a question into a
    # structured JSON contract (focus_field / property, needs_thinking,
    # needs_decomposition + sub_questions, anaphora_target). When disabled
    # (default) the keyword/regex + coreference pipeline runs unchanged, so
    # enabling it is a strict behavioural opt-in. See retrieval/query_understanding.py.
    QU_ENABLED: bool = False
    # Shadow mode: run QU + Validator and log everything, but never apply its
    # routing decisions. Used to measure the contract against the regex fallback
    # before flipping QU_ENABLED on.
    QU_SHADOW_MODE: bool = False

    # Visual Understanding: an independent image-analysis layer (Qwen2.5-VL via
    # Fireworks) that performs OCR + structured extraction of data-related images
    # (dashboard, ERD, SQL, error, metadata, requirement, table, lineage,
    # workflow, access/permission). Its JSON output feeds the existing router /
    # skills; it never answers the user directly (see retrieval/visual/).
    VISION_ENABLED: bool = True
    USE_MOCK_VISION: bool = False
    FIREWORKS_VISION_MODEL_ID: str = "accounts/fireworks/models/qwen3p7-plus"
    VISION_MAX_IMAGES: int = 4
    VISION_MAX_IMAGE_BYTES: int = 15 * 1024 * 1024  # 15 MB
    VISION_TIMEOUT_SECONDS: int = 60

    LOCAL_STORAGE_PATH: str = "./data/documents"

    # Image Storage: real local/object storage for uploaded images. The database
    # only keeps metadata; binary payloads live under IMAGE_STORAGE_PATH.
    IMAGE_STORAGE_PATH: str = "./data/images"
    IMAGE_THUMBNAIL_SIZE: int = 320
    IMAGE_THUMBNAIL_QUALITY: int = 80
    # Soft-deleted images are moved to a trash dir until purged.
    IMAGE_TRASH_PATH: str = "./data/images/.trash"
    IMAGE_RERUN_COOLDOWN_SECONDS: int = 5

    @model_validator(mode="after")
    def _validate_config(self) -> "Settings":
        if self.AUTH_MODE == "jwt" and not self.JWT_SECRET_KEY:
            raise ValueError("JWT_SECRET_KEY must be set when AUTH_MODE=jwt")
        if not self.USE_MOCK_DATAHUB and not self.DATAHUB_GMS_URL:
            raise ValueError("DATAHUB_GMS_URL must be set when USE_MOCK_DATAHUB=false")
        if (
            not self.USE_MOCK_LLM
            and not self.FIREWORKS_API_KEY
            and self.LLM_PROVIDER in ("fireworks",)
        ):
            raise ValueError(
                "FIREWORKS_API_KEY must be set when USE_MOCK_LLM=false "
                "and LLM_PROVIDER=fireworks"
            )
        return self

    @property
    def datahub_frontend_url_clean(self) -> str:
        return self.DATAHUB_FRONTEND_URL.rstrip("/")

    def datahub_entity_url(self, entity_type: str, urn: str) -> str:
        base = self.datahub_frontend_url_clean
        type_path = {
            "dataset": "dataset",
            "dashboard": "dashboard",
            "glossary_term": "glossary",
            "glossary_node": "glossaryNode",
            "document": "document",
        }.get(entity_type, "entity")
        return f"{base}/{type_path}/{urn}"


settings = Settings()
