# Metadata Report — Phân tích cơ chế

Phân tích feature **Metadata Report** (báo cáo tổng quan metadata của dataset) — `app/services/action_service.py:1073` + `app/api/actions.py`.

## 1. Kích hoạt (Trigger / Intent)

- **API**: `POST /api/v1/actions/report` (`app/api/actions.py:144`) với `{dataset}` → `ReportResponse`. `valid=False` → HTTP 404 với message.
- Chat: intent metadata tổng hợp đi qua tool tương ứng (`retrieval/intent_resolver.py` — action `metadata_summary` cho visual mode).

## 2. Pipeline (`action_service.py:1073 metadata_report`)

1. **Resolve dataset** (`resolve_dataset`) → không tìm thấy → `valid=False` "Không tìm thấy dataset trong metadata DataHub."
2. **Gom dữ liệu payload** (`:1082-1093`): description, business_purpose, owners (`_owner_names`), tags, glossary_terms, domain, platform, environment, certified, schema (`_schema_columns`), lineage (`_lineage_urns` live).
3. **Xây 10 section** (`:1095-1144`):
   - Dataset Overview (name/platform/environment/domain/URN)
   - Business Description (business_purpose > description; "(chưa có mô tả business)")
   - Technical Summary (số cột, upstream/downstream, certified)
   - Schema Summary (≤30 cột: name + type + description)
   - Ownership, Glossary, Tags (mỗi cái "(chưa có ...)" nếu rỗng)
   - Lineage (liệt kê URN upstream/downstream; "(không có)")
   - Data Quality (assertions count, profiling/freshness có/không)
   - Documentation Quality (độ dài mô tả)
4. **Đánh giá 6 chiều** (`:1149-1179`, hàm `_assess` = `_rating` → score/rating/stars):
   - **Metadata Completeness**: 100/0 (mô tả) + 50 (độ dài).
   - **Documentation Quality**: ≥50 ký tự → 100; có mô tả → 60; không → 0.
   - **Governance Readiness**: trung bình của {domain, owners, tags, glossary}.
   - **Discoverability**: trung bình của {mô tả, tags, glossary}.
   - **Lineage Completeness**: 100 nếu có upstream hoặc downstream.
   - **Overall Metadata Maturity**: trung bình của {description, owners, domain, tags, lineage}.
5. **Overall** (`:1181-1182`): score chiều Overall → `_rating` (điểm → rating, xem `dataQualityCheck.md`).
6. **Recommendations** (`:1184-1200`): conditional — thiếu description/owners/glossary/tags/assertions/profiling/lineage → mỗi cái một khuyến nghị; đầy đủ → "Metadata đã đầy đủ. Duy trì cập nhật định kỳ."

## 3. Response (`ReportResponse`)

- `dataset`, `urn`, `valid`
- `sections`: list `ReportSection(title, lines)` — trình bày được
- `assessment`: list `ReportAssessment(dimension, score, rating, stars)`
- `overall_score`, `overall_rating`
- `recommendations`: các bước cải thiện

## 4. Nguyên tắc cốt lõi

1. **Deterministic 100%**: không LLM — mọi điểm số là phép toán trên metadata thật.
2. **Trung thực về thiếu hụt**: luôn đánh dấu "(chưa có ...)" thay vì bỏ qua.
3. **Tách bạch overview/assessment/recommendation**: mô tả → chấm điểm → hành động.
4. **Điểm overall phản ánh mức trưởng thành metadata** (description/owners/domain/tags/lineage), không phải chất lượng dữ liệu.

## 5. Giới hạn / phụ thuộc hiện tại

- Schema Summary giới hạn 30 cột đầu.
- Lineage cần live DataHub (nếu source lỗi → rỗng, vẫn ra report nhưng Lineage Completeness = 0).
- Không phát hiện trùng lặp cột/không đánh giá chất lượng dữ liệu (đó là Data Quality Check — xem `dataQualityCheck.md`).

## 6. File tham chiếu

- `app/services/action_service.py` — `metadata_report` (1073), `_assess` (1209), `_owner_names` (177), `_schema_columns`
- `app/api/actions.py` — `POST /actions/report` (144)
- `app/schemas/actions.py` — `ReportResponse`, `ReportSection`, `ReportAssessment`
- `app/services/action_service.py` — `_rating` (222, dùng chung cho report & quality)
- `docs/analyze/dataQualityCheck.md` — feature bổ trợ (chất lượng dữ liệu)