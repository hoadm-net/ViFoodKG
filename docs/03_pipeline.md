# Pipeline Xây Dựng KG Tự Động

## 1. Kiến trúc tổng thể

```
┌─────────────────────────────────────────────────────────────────┐
│  BƯỚC 1: Thu thập & Tiền xử lý                                  │
│  Crawl / Export → OCR (nếu cần) → Text normalization → Chunk    │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│  BƯỚC 2: LLM Extraction (GPT-5.4 nano)                          │
│  Ontology-guided prompting → Structured JSON output             │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│  BƯỚC 3: Entity Normalization & Linking                         │
│  Chuẩn hóa tên → Map Codex/FoodOn/Wikidata IRI                 │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│  BƯỚC 4: KG Population                                          │
│  Deduplication → Neo4j insert → RDF/Turtle export               │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│  BƯỚC 5: Validation Loop                                        │
│  Consistency check (LLM) → Flag → Human review → Refine prompt │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Bước 1 — Thu thập & Tiền xử lý

### 2.1 Thu thập
- **Dữ liệu có cấu trúc** (Open Food Facts CSV, USDA API): parse trực tiếp
- **Trang web nhà sản xuất**: crawl bằng Playwright → lấy raw HTML
- **Ảnh nhãn sản phẩm** (ground truth): OCR bằng PaddleOCR (model tiếng Việt)

### 2.2 Tiền xử lý văn bản
```
1. Chuẩn hóa encoding: NFD → NFC (xử lý tiếng Việt)
2. Xóa HTML tags, ký tự thừa
3. Tách text theo sản phẩm (1 product = 1 document)
4. Giới hạn độ dài: nếu > 2,000 token thì chia chunk theo section
   (thành phần / dinh dưỡng / thông tin chung)
```

---

## 3. Bước 2 — LLM Extraction với GPT-5.4 nano

### 3.1 Lý do chọn GPT-5.4 nano

| Tiêu chí | Lý do |
|---|---|
| Chi phí thấp | Xử lý batch ~4,000 sản phẩm trong ngân sách hợp lý |
| Không cần reasoning chain | Tác vụ extraction có schema rõ ràng, không cần suy luận phức tạp |
| JSON mode | Hỗ trợ structured output, giảm lỗi parse |
| Đa ngữ | Xử lý tốt tiếng Việt lẫn tiếng Anh trên cùng nhãn |

### 3.2 Prompt Design — Ontology-Guided

Chiến lược: **Schema injection + Few-shot examples + Output constraints**

```
SYSTEM PROMPT:
"""
Bạn là hệ thống trích xuất thông tin thực phẩm có cấu trúc.
Trích xuất thông tin từ nhãn sản phẩm theo đúng schema JSON sau.
Chỉ trích xuất những gì được ghi rõ trên nhãn. Trả về null nếu thiếu.

SCHEMA:
{
  "product": {
    "name_vi": "string",
    "name_en": "string | null",
    "brand": "string",
    "category": "CANDY|BISCUIT|SNACK|DAIRY|INSTANT",
    "serving_size_g": "number | null",
    "net_weight_g": "number | null"
  },
  "ingredients": [
    {
      "name_vi": "string (tên chuẩn hóa, không viết tắt)",
      "order": "number (thứ tự trong danh sách)"
    }
  ],
  "additives": [
    {
      "name_vi": "string",
      "codex_code": "string | null (vd: E471, INS322)",
      "function_type": "PRESERVATIVE|ANTIOXIDANT|EMULSIFIER|STABILIZER|
                        THICKENER|COLOR|FLAVOR_ENHANCER|SWEETENER|
                        ACIDITY_REGULATOR|RAISING_AGENT|OTHER"
    }
  ],
  "nutrients": {
    "energy_kcal": "number | null",
    "protein_g": "number | null",
    "fat_total_g": "number | null",
    "fat_saturated_g": "number | null",
    "carbohydrate_g": "number | null",
    "sugar_g": "number | null",
    "sodium_mg": "number | null",
    "fiber_g": "number | null"
  },
  "allergens": ["MILK", "GLUTEN", "SOY", "EGG", "PEANUT",
                "TREENUT", "FISH", "SHELLFISH", "SESAME"],
  "extraction_confidence": "HIGH|MEDIUM|LOW"
}

QUY TẮC CHUẨN HÓA:
- Tên thành phần: viết đầy đủ, không viết tắt
  Ví dụ: "TFO" → "dầu thực vật tinh luyện"
- Phụ gia: nếu nhãn ghi "(E471)" thì codex_code = "E471"
- Dinh dưỡng: quy đổi về giá trị trên 100g nếu nhãn ghi theo khẩu phần
- Dị ứng: bao gồm cả "có thể chứa vết" (trace)
- confidence = LOW nếu văn bản OCR kém, MEDIUM nếu thiếu một số trường,
  HIGH nếu đầy đủ và rõ ràng
"""

FEW-SHOT EXAMPLES: (2-3 ví dụ đầy đủ)

USER: [product label text]
```

### 3.3 Xử lý lỗi & retry

```python
# Logic xử lý lỗi
for product in batch:
    result = call_gpt(product, prompt)
    
    if not valid_json(result):
        result = retry_with_repair_prompt(product, result)  # 1 lần retry
    
    if result["extraction_confidence"] == "LOW":
        flag_for_human_review(product)
    
    save_to_staging(result)
```

---

## 4. Bước 3 — Entity Normalization & Linking

### 4.1 Chuẩn hóa tên thành phần (Ingredient Normalization)

**Vấn đề:** Cùng một nguyên liệu có thể xuất hiện dưới nhiều dạng:
- "đường" / "đường kính" / "đường trắng" / "sucrose" / "cane sugar"

**Giải pháp — 2 bước:**

```
Bước 1: LLM normalization
  → GPT-5.4 nano map về tên chuẩn tiếng Việt (in-context list)

Bước 2: Embedding similarity
  → Encode tên bằng multilingual-e5-large
  → Cosine similarity với canonical ingredient list
  → Ngưỡng: ≥ 0.85 → auto-link; 0.70–0.85 → flag review; < 0.70 → new entity
```

### 4.2 Chuẩn hóa phụ gia (Additive Normalization)

```
Nếu codex_code đã có (vd: E471) → lookup trực tiếp bảng Codex GSFA
Nếu chỉ có tên:
  1. Exact match trong bảng Codex (tên Việt / tên Anh)
  2. Fuzzy match (Levenshtein ≤ 2)
  3. Embedding similarity (multilingual-e5-large)
  4. Không tìm được → tạo node mới với flag `unlinked=true`
```

### 4.3 Entity Linking sang KG bên ngoài

| Thực thể | Liên kết sang |
|---|---|
| `Ingredient` | FoodOn IRI, Wikidata Q-number |
| `Additive` | Codex INS number, Wikidata Q-number |
| `Brand` | Wikidata Q-number |

---

## 5. Bước 4 — KG Population

### 5.1 Deduplication

```
Product:    Match theo barcode (ưu tiên) hoặc (name_vi + brand) exact match
Ingredient: Match theo canonical_id (sau normalization)
Additive:   Match theo codex_code (primary key)
Brand:      Match theo tên chuẩn hóa (lowercase + strip diacritics)
```

**Merge strategy:** Nếu cùng entity từ nhiều nguồn → merge thuộc tính, ưu tiên nguồn có độ tin cậy cao hơn (ground truth > crawl hãng > Open Food Facts).

### 5.2 Neo4j Population

```cypher
-- Ví dụ tạo Product node
MERGE (p:Product {product_id: $product_id})
SET p.name_vi = $name_vi,
    p.brand   = $brand,
    p.category = $category,
    p.source  = $source

-- Tạo quan hệ HAS_INGREDIENT
MATCH (p:Product {product_id: $product_id})
MERGE (i:Ingredient {ingredient_id: $ingredient_id})
SET i.name_vi = $name_vi
MERGE (p)-[r:HAS_INGREDIENT]->(i)
SET r.order = $order
```

### 5.3 Export RDF/Turtle

Dùng thư viện `rdflib` để export KG sang định dạng Turtle (`.ttl`) cho khả năng tương thích Semantic Web và công bố mở.

---

## 6. Bước 5 — Validation Loop

### 6.1 Consistency Check tự động (LLM)

Sau khi population, chạy LLM check các vi phạm:

| Loại vi phạm | Câu hỏi check |
|---|---|
| Missing bắt buộc | Sản phẩm thiếu ENERGY/PROTEIN/FAT/CARB/SODIUM? |
| Giá trị bất hợp lý | Energy < 0 hoặc > 900 kcal/100g? |
| Phụ gia không rõ chức năng | `function_type = OTHER` quá nhiều? |
| Thành phần trùng | Cùng sản phẩm có 2 ingredient giống nhau? |

### 6.2 Human Review

- Flag tất cả entities có `extraction_confidence = LOW`
- Random sample 10–15% entities `confidence = MEDIUM`
- 100% ground truth set (dùng để tính metrics)

### 6.3 Prompt Refinement

Dựa trên lỗi từ human review → cập nhật few-shot examples và quy tắc chuẩn hóa → chạy lại batch bị lỗi.

---

## 7. Tổng quan chi phí tính toán

| Bước | Công cụ | Ước tính |
|---|---|---|
| Crawl | Playwright + BS4 | ~8–12 giờ cho toàn bộ web sources |
| OCR | PaddleOCR | ~2–4 giây/ảnh |
| LLM extraction | GPT-5.4 nano | ~0.5–1 giây/sản phẩm (batch API) |
| Entity linking | multilingual-e5-large | ~0.1 giây/entity |
| Neo4j population | neo4j-python-driver | ~0.01 giây/triple |
