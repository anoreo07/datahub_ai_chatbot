"""Thinking Mode: an independent planning/reasoning layer.

Pipeline:  Question -> Context Resolver -> Complexity Classifier
           -> (simple: fall through) | (complex: Thinking Planner
           -> Executor -> Synthesizer -> structured answer).

Exposed for wiring (chat_service) and tests:
- ``ThinkingModeOrchestrator`` : controller returning a final markdown answer
- ``evaluate_complexity``      : the complexity gate
"""

from __future__ import annotations

from retrieval.thinking.complexity import (
    ComplexityClassifier,
    ComplexityVerdict,
    evaluate_complexity,
)
from retrieval.thinking.models import (
    EffortResult,
    EvidenceRecord,
    ExecutionPlan,
    KnowledgeSource,
    PlanStep,
    ThinkingContext,
)
from retrieval.thinking.orchestrator import ThinkingModeOrchestrator

__all__ = [
    "ComplexityClassifier",
    "ComplexityVerdict",
    "EffortResult",
    "EvidenceRecord",
    "ExecutionPlan",
    "KnowledgeSource",
    "PlanStep",
    "ThinkingContext",
    "ThinkingModeOrchestrator",
    "evaluate_complexity",
]
