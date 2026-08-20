# DataAtlas — Constraints & Goals

## 1. Ràng buộc (constraints)

### 1.1 Kỹ thuật `[VERIFIED]`

1. **Không phụ thuộc corporate DataHub runtime** — GMS bị WAF chặn (`DATAHUB_SKIP_STARTUP_SYNC=1`). Dữ liệu vận hành từ snapshot `datahub_pull/`. `[VERIFIED]`
2. **LLM Fireworks có fallback deterministic** — khi không available, trả answer từ retrieved docs template, không gọi LLM. `[VERIFIED]`
3. **Embedding local Ollama** (`nomic-embed-text` 768 dim). `[VERIFIED]`
4. **Môi trường dev: Postgres :5433, Redis :6380, OpenSearch :9201, API :8000**. `[OBSERVED]`
5. **compose.yaml thiếu service `ollama`** nhưng các service tham chiếu `http://ollama:11434/v1` — gap cấu hình Docker. `[VERIFIED]`
6. **Repo có 56 files modified chưa commit** so với HEAD `8a87be5c`. `[OBSERVED]`

### 1.2 Dữ liệu `[VERIFIED]`

1. **Không dùng LLM để tạo factual metadata** — mọi UNKNOWN = không có bằng chứng (ground rule trong `data_landscape_audit.md`). `[VERIFIED]`
2. **7,838 datasets big-4 không có description**; 7,581 datasets (88.8%) không có domain. `[VERIFIED]`
3. **chart/container/data_flow/tag/domain/corp_user chưa load DB**. `[VERIFIED]`
4. **ACL phủ 884/9,067; RBAC 0 users; audit 0 rows**. `[OBSERVED]`

### 1.3 Quy trình / chất lượng `[VERIFIED]`

1. **Abstention > fabrication** — ưu tiên trả "không tìm thấy" hơn bịa. `[VERIFIED]`
2. **No hard-coded dataset-specific fixes** — fix phải generic (mentor M2). `[VERIFIED]`
3. **Mọi thay đổi phải test-protected** (mentor M11). `[VERIFIED]`
4. **Không regression** — 164 unit tests + 85 regression phải giữ pass. `[VERIFIED]`
5. **Lint/type**: `ruff check .` + `mypy` theo AGENTS.md. `[VERIFIED]`

## 2. Mục tiêu (goals)

### 2.1 Mục tiêu chất lượng (theo mentor) `[VERIFIED]`

| Mục tiêu | Hiện tại | Đích |
|---|---|---|
| Golden suite (first-incorrect-state verdict) | 15/48 (31.3%) | ≥ 75%+ (rolling đã chạm 36/48=75%*) |
| 3 nhóm RC còn mở | RC-A/B/C còn fail | Giải quyết hoàn toàn |
| Intent accuracy | 93.8% | giữ ≥ 90% |
| Hallucination | 0 | giữ 0 |
| Unit tests | 164 pass | giữ pass, tăng coverage |
| Report discovery precision | 0.0 | > 0, đạt mentor CASE2 |
| Glossary resolution accuracy | 0.2292 | ≥ 0.8 |

### 2.2 Mục tiêu chức năng `[VERIFIED]`

1. **Multi-hop decomposition hoạt động** — planner decompose thành chuỗi hops (mentor M3).
2. **Domain-scoped semantic resolution** — term theo domain phân biệt đúng (mentor M5).
3. **Report/dashboard discovery** — resolve đúng loại entity report (mentor M6).
4. **Formula/field evidence injected** — field description, formula, owner trong context (RC8).
5. **Ambiguity gate chính xác** — hết false-positive (RC1a), fuzzy đúng entity (RC1b).
6. **Count tool scoped** — có entity/domain filter (RC3).
7. **LLM-first intent** giữ vững (RC2 đã giảm).

### 2.3 Mục tiêu dữ liệu `[INFERRED]` (đề xuất)

1. Load chart/container/data_flow/tag/domain/corp_user vào DB + OpenSearch.
2. Chuẩn hoá platform names + tên dataset (trim, case).
3. Bổ sung/derive domain cho 7,581 datasets không domain.
4. Seed RBAC users + enable audit logging.
5. Cân nhắc mở rộng ground-truth test ra toàn corpus (không chỉ 135 datasets).

## 3. Non-goals (không nằm trong phạm vi hiện tại) `[INFERRED]`

- Không phải là hệ thống thay thế DataHub — chỉ đọc metadata từ DataHub. `[VERIFIED]` — `USE_MOCK_DATAHUB=false`, nguồn đọc-only.
- Không ghi/write dữ liệu vào DataHub.
- Không hỗ trợ real-time write-back từ chat.
- Vision là tính năng mới (image_records=1) — chưa phải ưu tiên chính.
- Không xử lý tiếng Anh-first; tối ưu cho tiếng Việt.

## 4. Rủi ro chính cần quản lý `[INFERRED]`

| Rủi ro | Mức | Ghi chú |
|---|---|---|
| DataHub WAF chặn → dữ liệu snapshot cũ dần stale | Cao | cần pipeline pull định kỳ khi mở WAF |
| Repo uncommitted nhiều → mất mát nếu không commit | Cao | 56 files modified |
| Benchmark subset nhỏ (135 datasets) → kết quả không đại diện | Trung bình | cần mở rộng golden |
| Ollama service thiếu trong compose | Trung bình | embedding fail khi deploy Docker |
| ACL thưa + không user → RBAC chưa test thật | Trung bình | |

## 5. Nguyên tắc phát triển tiếp theo

1. Ưu tiên fix theo **root cause map** (RC-A/B/C) thay vì per-test.
2. Mọi fix phải kèm test (unit + integration + golden regression).
3. Giữ deterministic path cho phần có thể deterministic (owner/domain/formula-guard).
4. LLM chỉ dùng ở nơi keyword heuristic yếu (intent disambiguation, QU opt-in).
5. Verify bằng lệnh chuẩn (import, pytest, ruff, mypy) sau mỗi thay đổi.