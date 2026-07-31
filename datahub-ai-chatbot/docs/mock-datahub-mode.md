# Mock DataHub Mode

## Mục tiêu
Chạy toàn bộ ứng dụng AI Chatbot mà không cần DataHub thật, OpenSearch thật, PostgreSQL thật, Redis thật, hay API key LLM thật.

## Cấu trúc dữ liệu mẫu
Đường dẫn: `app/data/mock_datahub/`

| File | Nội dung |
|------|----------|
| domains.json | 5 domain mẫu (Logistic, Finance, Sản xuất, Cung ứng, Kinh doanh) |
| datasets.json | 8 dataset (logistic.fact_inventory, dim_material, dim_plant, dim_supplier, fact_goods_in_transit, sales.orders, monthly_revenue, raw.payments) |
| dashboards.json | 3 dashboard (Tồn Kho Min Max, Inventory Executive Summary, Monthly Finance Summary) |
| glossary_terms.json | 10 glossary term |
| documents.json | 3 document mẫu |
| lineage.json | 16 lineage edge |
| deleted_entities.json | 1 entity bị deleted, 1 entity DEV |

## Cách chạy

### 1. Copy env file
```bash
cp .env.mock.example .env
```

### 2. Validate mock data
```bash
python -m app.cli.validate_mock_data
```

### 3. Sync mock data (optional, cần PostgreSQL hoặc SQLite)
```bash
python -m app.cli.sync_mock
```

### 4. Chạy API server
```bash
uvicorn app.main:app --reload
```

## Câu hỏi demo

### Owner
- "Ai là Business Owner của dashboard Tồn Kho Min Max?"
- "Ai là System Owner của dim_plant?"

### Schema
- "fact_inventory có những cột nào?"
- "stock_on_hand nghĩa là gì?"

### Glossary
- "Tồn kho Min Max là gì?"
- "Safety Stock là gì?"

### Lineage
- "Dashboard lấy dữ liệu từ đâu?"
- "Nếu fact_inventory lỗi thì dashboard nào bị ảnh hưởng?"

### Domain
- "Có những domain nào?"
- "Dashboard Tồn Kho Min Max thuộc domain nào?"

### Ambiguity
- "Tìm inventory"
- "fact_inventory có mấy environment?"

## Cách thêm dữ liệu mẫu

### Thêm domain
Thêm object vào `app/data/mock_datahub/domains.json`:
```json
{
  "urn": "urn:li:domain:ten_domain",
  "name": "Tên Domain",
  "description": "Mô tả domain"
}
```

### Thêm dataset
Thêm object vào `app/data/mock_datahub/datasets.json`:
```json
{
  "urn": "urn:li:dataset:(platform,schema.table,ENV)",
  "entity_type": "dataset",
  "name": "schema.table",
  "description": "Mô tả dataset",
  "business_purpose": "Mục đích",
  "platform": "postgres",
  "environment": "PROD",
  "domain_urn": "urn:li:domain:ten_domain",
  "domain": "Tên Domain",
  "owners": [],
  "schema_fields": [],
  "upstreams": [],
  "downstreams": [],
  "datahub_url": "http://mock-datahub.local/dataset/..."
}
```

### Thêm dashboard
Thêm vào `app/data/mock_datahub/dashboards.json` tương tự.

### Thêm glossary
Thêm vào `app/data/mock_datahub/glossary_terms.json`.

### Thêm lineage
Thêm edge vào `app/data/mock_datahub/lineage.json`:
```json
{"source": "urn:li:...", "target": "urn:li:..."}
```

## Feature flags

| Flag | Default | Mô tả |
|------|---------|-------|
| USE_MOCK_DATAHUB | true | Dùng mock source thay vì DataHub GraphQL |
| USE_MOCK_LLM | true | Dùng mock LLM thay vì gọi Fireworks/OpenAI |
| USE_MOCK_EMBEDDING | true | Dùng mock embedding deterministic |
| USE_FAKE_OPENSEARCH | true | Dùng in-memory search thay vì OpenSearch |
| USE_IN_MEMORY_DATABASE | true | Dùng SQLite hoặc in-memory DB |
| USE_IN_MEMORY_QUEUE | true | Dùng in-memory queue thay vì Redis |
| ENABLE_NETWORK_ACCESS | false | Chặn mọi network call |

## Giới hạn

Mock mode KHÔNG xác nhận:
- GraphQL schema thật của DataHub
- Permission/ACL thật
- Pagination thật (scrollAcrossEntities)
- DataHub event stream thật
- DataHub version compatibility
- OpenSearch query performance
- LLM response quality
