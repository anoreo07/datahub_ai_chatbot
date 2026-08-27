# RAGAS Trace Report — Tại sao không thấy UI kiểm tra Chatbot Response

> Trace toàn diện codebase, dựa trên code thực tế, không suy đoán.

---

## 1. RAGAS Hiện trạng

| Thành phần | Trạng thái | Ghi chú |
|---|---|---|
| `ragas` pip package | **KHÔNG CÀI** | Không có trong `pyproject.toml` |
| `evaluation/ragas_evaluator.py` | **KHÔNG TỒN TẠI** | Plan đề cập nhưng chưa tạo |
| `evaluation/ragas_dataset.json` | **KHÔNG TỒN TẠI** | Plan đề cập nhưng chưa tạo |
| `evaluation/metrics.py::compute_faithfulness()` | Tồn tại | Tự implement, keyword-overlap, **không phải RAGAS library** |
| `evaluation/evaluator.py` | Tồn tại | Chạy qua CLI script, có bug (answer vs context) |
| `evaluation/golden_dataset.py` | Tồn tại | 21 samples tiếng Việt |
| `scripts/evaluate.py` | Tồn tại | CLI manual, không tự động |
| `workers/scheduler.py` | Stub | `NotImplementedError` |

**Kết luận:** Thư viện `ragas` thực tế không được dùng. Dự án tự implement simplified faithfulness metric bằng keyword overlap.

---

## 2. End-to-End Data Flow

### Flow hiện tại (có tồn tại trong code):

```
Chat Question
    │
    ▼
ChatService.answer()                    ← chat_service.py
    │
    ├─ InteractionLogger.log_request()  ← interaction_logger.py:30  ✅ wired
    │       │
    │       ▼
    │   INSERT INTO interaction_logs    ← ❌ BẢNG CHƯA TỒN TẠI (không có migration)
    │
    ├─ InteractionLogger.log_response() ← interaction_logger.py:56  ✅ wired
    │       │
    │       ▼
    │   UPDATE interaction_logs SET ... ← ❌ BẢNG CHƯA TỒN TẠI
    │
    └─ return ChatResponse

    ❌ KHÔNG CÓ BƯỚC: InteractionLogger.update_ragas_scores()
```

### Flow cần thiết nhưng CHƯA CÓ:

```
ChatService.answer()
    │
    ├─ ✅ log_request()
    ├─ ✅ log_response()
    │
    ├─ ❌ evaluate_response()          ← KHÔNG TỒN TẠI trong chat pipeline
    │       │
    │       ├─ compute_faithfulness()  ← có trong evaluation/metrics.py, nhưng không được gọi
    │       ├─ compute_answer_relevancy()  ← KHÔNG TỒN TẠI
    │       ├─ compute_context_precision() ← KHÔNG TỒN TẠI
    │       └─ compute_context_recall()    ← KHÔNG TỒN TẠI
    │
    └─ ❌ InteractionLogger.update_ragas_scores()  ← DEAD CODE, không có caller
```

### API flow:

```
GET /api/v1/admin/interactions        ← ✅ tồn tại, admin.py:14
    │
    ├─ Query interaction_logs table   ← ❌ BẢNG CHƯA TỒN TẠI
    └─ Return faithfulness scores     ← Luôn NULL vì không có evaluator

GET /api/v1/admin/interactions/{id}   ← ✅ tồn tại, admin.py:33
    │
    └─ Return single interaction      ← Luôn NULL RAGAS scores
```

### Frontend flow:

```
Admin Page (/admin)                   ← ✅ tồn tại
    │
    ├─ Tab "Sync"                     ✅
    ├─ Tab "Index"                    ✅
    ├─ Tab "Documents"                ✅
    ├─ Tab "DataHub"                  ✅
    ├─ Tab "Roles"                    ✅
    │
    ├─ ❌ KHÔNG CÓ Tab "Interactions"
    ├─ ❌ KHÔNG CÓ Tab "RAGAS"  
    ├─ ❌ KHÔNG CÓ Tab "Evaluation"
    └─ ❌ KHÔNG CÓ Component hiển thị interaction logs
```

---

## 3. Các File/Function/API Liên quan

### Backend

| File | Dòng | Function | Trạng thái |
|---|---|---|---|
| `database/models.py` | 304-357 | `InteractionLog` | Model tồn tại, **không có migration** |
| `app/services/interaction_logger.py` | 17 | `InteractionLogger` | Class tồn tại |
| `app/services/interaction_logger.py` | 30 | `log_request()` | ✅ Wired vào ChatService |
| `app/services/interaction_logger.py` | 56 | `log_response()` | ✅ Wired vào ChatService |
| `app/services/interaction_logger.py` | 107 | `update_ragas_scores()` | ❌ **DEAD CODE** — không có caller |
| `app/services/interaction_logger.py` | 145 | `get_interactions()` | ✅ Gọi từ admin API |
| `app/services/interaction_logger.py` | 187 | `get_interaction()` | ✅ Gọi từ admin API |
| `app/api/admin.py` | 14 | `GET /interactions` | ✅ Wired vào router |
| `app/api/admin.py` | 33 | `GET /interactions/{trace_id}` | ✅ Wired vào router |
| `app/services/chat_service.py` | 485 | `self._interaction_logger = InteractionLogger()` | ✅ |
| `app/services/chat_service.py` | 551 | `self._interaction_logger.log_request()` | ✅ |
| `app/services/chat_service.py` | 648,682,782,798,... | `self._interaction_logger.log_response()` | ✅ |

### Evaluation (offline only)

| File | Dòng | Function | Trạng thái |
|---|---|---|---|
| `evaluation/metrics.py` | 61 | `compute_faithfulness()` | Tự implement keyword-overlap |
| `evaluation/evaluator.py` | 129 | `Evaluator` | Chỉ dùng qua CLI |
| `evaluation/evaluator.py` | 175 | faithfulness call | **BUG** — answer vs answer (không phải context) |
| `evaluation/golden_dataset.py` | 25 | `BUILTIN_SAMPLES` | 21 samples |
| `scripts/evaluate.py` | 11 | `_run_evaluation()` | CLI manual |

### Frontend

| File | Dòng | Component | Trạng thái |
|---|---|---|---|
| `frontend/app/(app)/admin/page.tsx` | 16 | Tabs | ❌ Không có tab Interactions/RAGAS |
| `frontend/components/chat/quality-report-card.tsx` | all | QualityReportCard | ❌ Đây là data quality, KHÔNG PHẢI RAGAS |

### Infrastructure

| File | Dòng | Item | Trạng thái |
|---|---|---|---|
| `database/migrations/versions/` | all | Migration cho `interaction_logs` | ❌ **KHÔNG TỒN TẠI** |
| `workers/scheduler.py` | 4 | `Scheduler` | ❌ Stub (`NotImplementedError`) |
| `deploy/helm/.../cronjob-sync.yaml` | all | Cron job | ❌ Chỉ sync, không evaluation |
| `pyproject.toml` | -- | `ragas` dependency | ❌ Không có |

---

## 4. Root Cause

**Tại sao không thấy giao diện kiểm tra RAGAS?**

**4 nguyên nhân đồng thời:**

### RC1: Bảng `interaction_logs` chưa tồn tại (không có migration)
- `database/models.py:307` define `InteractionLog` nhưng **không có Alembic migration** nào tạo bảng này
- Tất cả 6 migration files (initial → 6_add_image_storage) đều không mention `interaction_logs`
- Khi backend chạy, SQLAlchemy `create_all()` có thể tạo bảng, nhưng altar `update_ragas_scores()` **không bao giờ được gọi** nên scores luôn NULL

### RC2: `update_ragas_scores()` là dead code
- `interaction_logger.py:107` define method nhưng **zero callers** trong toàn bộ codebase
- Không có evaluator nào chạy trong live chat pipeline
- Không có background task/cron nào trigger evaluation

### RC3: Không có evaluator trong chat pipeline
- `evaluation/evaluator.py` chỉ chạy qua CLI (`scripts/evaluate.py`)
- `ChatService.answer()` **không import hay gọi** bất kỳ evaluation function nào
- RAGAS scores luôn NULL ngay cả khi bảng tồn tại

### RC4: Frontend không có tab/panel hiển thị interactions
- `frontend/app/(app)/admin/page.tsx:16` chỉ có 5 tabs: Sync, Index, Documents, DataHub, Roles
- **Không có tab "Interactions" hay "RAGAS"**
- Admin API endpoints (`/api/v1/admin/interactions`) tồn tại nhưng **không có frontend consumer**

---

## 5. Những Phần Còn thiếu

### Backend thiếu:
1. **Alembic migration** cho `interaction_logs` table
2. **RAGAS evaluator trong chat pipeline** — gọi `compute_faithfulness()` sau mỗi response
3. **Các metric còn thiếu**: `answer_relevancy`, `context_precision`, `context_recall` — hiện chỉ có `faithfulness` (keyword-overlap)
4. **Background task** chạy evaluation async sau response
5. **`evaluation/ragas_evaluator.py`** — file được plan nhưng chưa tạo
6. **`ragas` pip dependency** — nếu muốn dùng RAGAS library thay vì tự implement

### Frontend thiếu:
1. **Tab "Interactions"** trong Admin page
2. **Component hiển thị interaction list** với RAGAS scores
3. **Component hiển thị interaction detail** khi click
4. **Filter/sort** theo RAGAS scores (faithfulness thấp → cần review)
5. **Dashboard/chart** tổng quan RAGAS scores

### Infra thiếu:
1. **Cron job** chạy `evaluate.py` định kỳ
2. **Scheduler** thực sự hoạt động (hiện là stub)

---

## 6. Implementation Plan Ngắn gọn

### Bước 1: Tạo migration cho `interaction_logs` (5 phút)
```
alembic revision --autogenerate -m "add interaction_logs"
alembic upgrade head
```

### Bước 2: Tạo `evaluation/ragas_evaluator.py` (30 phút)
- Class `RAGASEvaluator` với các method:
  - `evaluate_faithfulness(answer, context)` 
  - `evaluate_answer_relevancy(question, answer)`
  - `evaluate_context_precision(question, context)`
  - `evaluate_context_recall(question, context, ground_truth)`
- Có thể dùng RAGAS library hoặc tự implement

### Bước 3: Wire evaluator vào ChatService (20 phút)
- Trong `ChatService.answer()`, sau `log_response()`:
  ```python
  # Async evaluation
  asyncio.create_task(self._evaluate_and_store(response, context))
  ```
- Gọi `InteractionLogger.update_ragas_scores()`

### Bước 4: Tạo Admin Frontend Tab (45 phút)
- Thêm tab "Interactions" vào `admin/page.tsx`
- Tạo component `InteractionList` fetch `/api/v1/admin/interactions`
- Tạo component `InteractionDetail` hiển thị khi click
- Hiển thị RAGAS scores với color coding

### Bước 5: Background Evaluation (optional, 15 phút)
- Cron job chạy `evaluate.py` trên golden dataset
- Hoặc async task sau mỗi chat response

**Tổng estimated time: ~2 giờ**
