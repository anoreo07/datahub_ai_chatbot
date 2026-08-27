# Data Quality Check — Phân tích tiêu chí đánh giá

Phân tích toàn bộ feature **Data Quality Check** trong codebase (app/services/action_service.py, app/services/chat/flows.py, app/schemas/quality.py, app/services/quality_report.py, retrieval/intent_resolver.py).

## 1. Kiến trúc

- **Routing**: `retrieval/intent_resolver.py:145` nhận diện intent `quality_check` (kèm clarification "Bạn muốn đánh giá chất lượng metadata (data quality) của dataset nào?") → `chat_service.py:1375` → `app/services/chat/flows.py:207 quality_check_flow` (chọn dataset, gọi `ActionService.quality_check`, render markdown summary/full, ghi evidence).
- **Core**: `app/services/action_service.py:670 quality_check()` — **deterministic, 100% dựa trên metadata trong DataHub, không dùng LLM suy đoán**. Thiếu gì là ghi "không thể đánh giá", không bịa.

## 2. Cách chấm điểm

- **Điểm mỗi section** (`action_service.py:707-714`): khởi đầu 100, mỗi finding **FAILED −45, WARNING −18**, clamp 0–100.
- **Trạng thái section** = finding nặng nhất (có FAILED → FAILED; chỉ WARNING → WARNING; có PASSED → PASSED; trống → NOT_EVALUATED).
- **Overall score** (`action_service.py:1050-1052`): trung bình cộng điểm các section **đã đánh giá được** (section NOT_EVALUATED bị loại — không phạt khi thiếu profiling).
- **Rating** (`app/services/quality_report.py:26`): ≥85 Excellent, ≥70 Good, ≥50 Fair, còn lại Poor.

## 3. Các tiêu chí đánh giá (sections) và ngưỡng

| Section | Tiêu chí | PASSED | WARNING | FAILED |
|---|---|---|---|---|
| **Metadata** | Deprecation | không deprecated | — | deprecated |
| | Business description | ≥50 ký tự | <50 ký tự | thiếu hẳn |
| | Ownership | có owner | — | không owner |
| | Tags | có | không | — |
| | Glossary | có | không | — |
| | Domain | có | không | — |
| | Platform & env | cả 2 | thiếu 1 | — |
| **Schema** | Có schema | có cột | — | không cột |
| | Column types | 100% có type | 1 phần | 0 cột có type |
| | Column docs | ≥80% | <80% | — |
| | Schema drift* | không drift | — | có drift |
| **Completeness*** | Avg NULL% | <5% | <20% | ≥20% |
| | NULL/cột (top 3) | <5% | <20% | ≥20% |
| **Uniqueness*** | Duplicate rate | 0% | <5% | ≥5% |
| **Validity** | Assertions | có | không có | — |
| | Type validity* | mọi cột ≥0.9 | — | có cột <0.9 |
| **Consistency** | Record count anomaly* | \|Δ\|<20% | — | ≥20% |
| | Metadata consistency | có platform+domain | — | — |
| **Freshness** | last_updated | có | — | thiếu → NOT_EVALUATED |
| **Lineage** | upstream/downstream | có | — | không có |

*Chỉ đánh giá được khi có **profiling data** trong payload (`_profiling_stats`, action_service.py:185) — gồm column_stats, duplicate_rate, row_count, schema_drift. Không có profiling → các check này **NOT_EVALUATED**, liệt kê trong `not_evaluated_checks`, không tính vào điểm overall.

## 4. Nguyên tắc quan trọng khi đánh giá

1. **Không trừng phạt thiếu dữ liệu**: check không đánh giá được sẽ bị loại khỏi overall thay vì tính FAILED — tránh report đẹp giả tạo do không có profiling.
2. **Luôn minh bạch**: `not_evaluated_checks` + `profiling_available` cho biết report "thật" (đo từ dữ liệu) hay chỉ "metadata-level".
3. **Recommendations** (`action_service.py:996-1048`) sinh tự động từ các finding xấu, ưu tiên high/medium theo mức độ rủi ro (deprecated, thiếu mô tả/owner/domain/lineage, NULL cao, trùng lặp, biến động row count).

## 5. Giới hạn hiện tại

Trong DB thật (9067 entities: 8542 datasets, 327 dashboards, 177 glossary_terms): đa số dataset không có description/domain/lineage, và **không dataset nào có profiling data** — nên các check Completeness/Uniqueness/Consistency/Type validity/Schema drift gần như luôn NOT_EVALUATED, report chủ yếu rơi về metadata-level checks.

## 6. File tham chiếu

- `app/services/action_service.py` — core `quality_check()` (line 670), `_profiling_stats` (185), `_rating` (222)
- `app/services/chat/flows.py` — `quality_check_flow` (207), render summary/full
- `app/services/quality_report.py` — `_rating_of` (26), nhóm sections, render markdown/TXT/PDF
- `app/schemas/quality.py` — QualityReport / QualitySection / QualityFinding / QualityRecommendation / QualityStatus
- `retrieval/intent_resolver.py` — intent `quality_check` (145)
- `app/services/chat_service.py` — routing (1375)
- `app/api/actions.py` — API endpoint quality_check (92)
- `tests/integration/test_quality_report.py` — integration tests cho feature