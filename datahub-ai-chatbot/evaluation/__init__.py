"""RAG quality evaluation package.

Framework components:
  - models: Evaluation data models (RootCause, PipelineTrace, SystemMetrics, ReferenceDataset)
  - diagnostics: Root-cause classifier (WHERE/WHY failures occur)
  - system_metrics: Deterministic metrics (entity accuracy, retrieval hit, citation)
  - reference_model: Structured ground truth with provenance/versioning
  - benchmark_generator: Auto-generate evaluation scenarios from DataHub
  - pipeline_evaluator: Full pipeline evaluator with trace capture
  - retrospective_evaluator: Evaluate existing interaction logs
  - multi_turn: Multi-turn conversation evaluation
  - regression: Before/after comparison framework
"""
