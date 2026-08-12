from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.authorization import AuthorizationService
from app.services.conversation import get_conversation_memory
from app.services.conversation_context import ConversationContextManager
from database.repositories.entity_repository import EntityRepository
from database.session import async_session_factory as _async_session_factory
from guardrails.service import GuardrailService
from ingestion import create_datahub_source
from ingestion.source import DataHubSource
from llm.client import create_llm_client
from llm.generator import AnswerGenerator
from retrieval.entity_extraction import EntityExtractor
from retrieval.entity_resolver import EntityResolver
from retrieval.hybrid_search import HybridSearch
from retrieval.intent_resolver import IntentResolver
from retrieval.planner_executor import PlannerExecutor
from retrieval.reranker import Reranker
from retrieval.semantic_expansion import SemanticExpander
from retrieval.thinking import ThinkingModeOrchestrator
from retrieval.tools import ToolRegistry
from retrieval.visual import VisualUnderstandingSkill

if TYPE_CHECKING:
    from app.services.chat.access import DomainAccessService
    from app.services.chat.entity_resolution import EntityResolutionService
    from app.services.chat.evidence import EvidenceService
    from app.services.chat.flows import ChatFlowsService
    from app.services.chat.lineage import LineageService
    from app.services.chat.listing import ListingService
    from app.services.chat.structured_retrieval import StructuredRetrievalService
    from app.services.chat.vision import VisionContextService


class ChatContext:
    """Shared collaborators for the chat domain services.

    Built once by ``ChatService`` and passed to every domain service; the
    service references (entities/retrieval/evidence/...) are assigned after
    construction because they depend on this context.
    """
    def __init__(
        self, session: AsyncSession,
        auth_service: AuthorizationService | None = None,
    ) -> None:
        self.session = session
        self.auth_service = auth_service
        self.entity_resolver = EntityResolver(session)
        self.entity_repo = EntityRepository(session)
        self.entity_extractor = EntityExtractor(session)
        self.semantic = SemanticExpander()
        self.hybrid_search = HybridSearch(session)
        self.planner = PlannerExecutor(session, session_factory=_async_session_factory)
        self.reranker = Reranker()
        self.tools = ToolRegistry(session)
        self.generator = AnswerGenerator()
        self.llm = create_llm_client()
        self.intent_resolver = IntentResolver(self.llm)
        self.source: DataHubSource = create_datahub_source()
        self.memory = get_conversation_memory()
        self.guardrails = GuardrailService()
        self.thinking = ThinkingModeOrchestrator(session)
        self.vision_skill = VisualUnderstandingSkill(session)
        from app.services.vision_service import VisionService

        self.conversation_vision = VisionService(session, skill=self.vision_skill)
        from app.services.image_upload import ImageUploadService
        self.conv_context = ConversationContextManager(
            session, upload_service=ImageUploadService(
                session, vision_service=self.conversation_vision,
            )
        )
        # Domain service refs, assigned by ChatService after construction.
        self.entities: EntityResolutionService = None  # type: ignore[assignment]
        self.retrieval: StructuredRetrievalService = None  # type: ignore[assignment]
        self.evidence: EvidenceService = None  # type: ignore[assignment]
        self.listing: ListingService = None  # type: ignore[assignment]
        self.lineage: LineageService = None  # type: ignore[assignment]
        self.flows: ChatFlowsService = None  # type: ignore[assignment]
        self.access: DomainAccessService = None  # type: ignore[assignment]
        self.vision: VisionContextService = None  # type: ignore[assignment]
