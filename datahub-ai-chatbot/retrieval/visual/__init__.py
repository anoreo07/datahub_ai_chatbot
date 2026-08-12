"""Visual Understanding layer.

An independent image-analysis capability (Qwen2.5-VL via Fireworks) that reads
data-related images — dashboards, ERD / data-model diagrams, SQL, errors,
metadata / catalog, requirements / data dictionaries, Excel / tables, lineage,
workflow, access / permission — and returns structured JSON evidence that the
existing router / skills can reuse. It never answers the user directly and never
over-infers on low-quality or unrelated images.
"""

from retrieval.visual.client import (
    FireworksVisionClient,
    MockVisionClient,
    VisionClient,
    create_vision_client,
    parse_data_url,
)
from retrieval.visual.models import (
    VisionCandidate,
    VisionEntity,
    VisionImageType,
    VisionQuality,
    VisionResult,
)
from retrieval.visual.parser import build_result, parse_vision_json
from retrieval.visual.skill import VisualUnderstandingSkill

__all__ = [
    "FireworksVisionClient",
    "MockVisionClient",
    "VisionCandidate",
    "VisionClient",
    "VisionEntity",
    "VisionImageType",
    "VisionQuality",
    "VisionResult",
    "VisualUnderstandingSkill",
    "build_result",
    "create_vision_client",
    "parse_data_url",
    "parse_vision_json",
]
