# Tech Stack & Công Cụ

## 1. Tổng quan

```
┌─────────────────────────────────────────────────────────────────┐
│  Thu thập dữ liệu                                               │
│  Playwright  │  BeautifulSoup  │  PaddleOCR  │  requests        │
├─────────────────────────────────────────────────────────────────┤
│  LLM & NLP                                                      │
│  OpenAI GPT-5.4 nano  │  multilingual-e5-large  │  rdflib       │
├─────────────────────────────────────────────────────────────────┤
│  Knowledge Graph                                                │
│  Neo4j Community  │  neo4j-python-driver  │  Cypher             │
├─────────────────────────────────────────────────────────────────┤
│  Đánh giá & Phân tích                                           │
│  Python  │  pandas  │  scikit-learn  │  matplotlib              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Chi tiết từng thành phần

### 2.1 Thu thập dữ liệu

| Công cụ | Vai trò | Ghi chú |
|---|---|---|
| **Playwright** (Python) | Crawl trang web JavaScript-heavy | Headless Chromium |
| **BeautifulSoup 4** | Parse HTML tĩnh | Kết hợp với `httpx` |
| **PaddleOCR** | OCR ảnh nhãn sản phẩm | Model tiếng Việt (`vi`) |
| **requests / httpx** | Gọi Open Food Facts API, USDA FDC API | Async với httpx |

### 2.2 LLM — GPT-5.4 nano

| Thuộc tính | Chi tiết |
|---|---|
| **Model** | `gpt-5.4-nano` |
| **Provider** | OpenAI |
| **Mode** | Batch API (cho throughput cao, chi phí thấp hơn 50%) |
| **Output format** | JSON mode (`response_format: {"type": "json_object"}`) |
| **Không dùng** | Reasoning / chain-of-thought (không cần thiết cho structured extraction) |
| **Tài liệu** | https://developers.openai.com/api/docs/models/gpt-5.4-nano |

```python
# Ví dụ gọi API
from openai import OpenAI

client = OpenAI()
response = client.chat.completions.create(
    model="gpt-5.4-nano",
    response_format={"type": "json_object"},
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": product_text}
    ]
)
```

### 2.3 Entity Linking & Embedding

| Công cụ | Vai trò |
|---|---|
| **multilingual-e5-large** | Embedding cho entity normalization và linking |
| **sentence-transformers** | Wrapper Python cho e5-large |
| **FAISS** | Vector similarity search cho candidate retrieval |

```python
# Ví dụ entity linking
from sentence_transformers import SentenceTransformer
import faiss

model = SentenceTransformer("intfloat/multilingual-e5-large")
query_emb = model.encode(["query: " + ingredient_name])
# Tìm canonical entity gần nhất trong FAISS index
distances, indices = index.search(query_emb, k=5)
```

### 2.4 Knowledge Graph — Neo4j

| Thuộc tính | Chi tiết |
|---|---|
| **Storage** | Neo4j Community Edition 5.x |
| **Driver** | `neo4j` Python driver (v5.x) |
| **Query language** | Cypher |
| **Export** | RDF/Turtle bằng `rdflib` |

**Lý do chọn Neo4j:**
- Cypher query trực quan cho graph traversal
- Built-in visualization (Neo4j Browser)
- Python driver tốt
- APOC plugin hỗ trợ import/export nhiều định dạng

### 2.5 Ontology & RDF

| Công cụ | Vai trò |
|---|---|
| **Protégé** | Thiết kế và validate ontology (OWL/RDF) |
| **rdflib** (Python) | Tạo và export RDF/Turtle |
| **FoodOn** | Ontology tham chiếu (base classes cho food entities) |

### 2.6 Đánh giá & Phân tích

| Công cụ | Vai trò |
|---|---|
| **pandas** | Xử lý ground truth CSV, tính metrics |
| **scikit-learn** | Tính Precision/Recall/F1, Cohen's Kappa |
| **matplotlib / seaborn** | Visualize phân phối KG, biểu đồ so sánh |
| **Jupyter Notebook** | Môi trường chạy experiments |

---

## 3. Cấu trúc thư mục dự án (đề xuất)

```
ViFoodKG/
├── README.md
├── docs/
│   ├── 01_ontology.md
│   ├── 02_data_sources.md
│   ├── 03_pipeline.md
│   ├── 04_evaluation.md
│   └── 05_tech_stack.md
├── ontology/
│   ├── vifoodkg.owl          # OWL ontology (Protégé)
│   └── vifoodkg_base.ttl     # Base Turtle
├── data/
│   ├── raw/                  # Dữ liệu thô (gitignore)
│   ├── processed/            # Sau tiền xử lý
│   └── ground_truth/         # Ground truth annotate
├── src/
│   ├── collect/
│   │   ├── crawl_web.py      # Playwright crawler
│   │   ├── fetch_off.py      # Open Food Facts
│   │   └── ocr_labels.py     # PaddleOCR pipeline
│   ├── extract/
│   │   ├── llm_extract.py    # GPT-5.4 nano extraction
│   │   └── prompts.py        # Prompt templates
│   ├── normalize/
│   │   ├── ingredient_norm.py
│   │   ├── additive_link.py
│   │   └── entity_linking.py
│   ├── populate/
│   │   ├── neo4j_writer.py
│   │   └── rdf_export.py
│   └── evaluate/
│       ├── metrics.py        # Precision/Recall/F1
│       └── consistency.py    # Ontology violation checks
├── notebooks/
│   ├── 01_exploration.ipynb
│   ├── 02_pipeline_demo.ipynb
│   └── 03_evaluation.ipynb
└── requirements.txt
```

---

## 4. Requirements

```txt
# Web crawling
playwright==1.44.0
beautifulsoup4==4.12.3
httpx==0.27.0

# OCR
paddleocr==2.7.3
paddlepaddle==2.6.1

# LLM
openai>=1.30.0

# Embeddings
sentence-transformers==3.0.0
faiss-cpu==1.8.0

# Knowledge Graph
neo4j==5.20.0
rdflib==7.0.0

# Evaluation & Analysis
pandas==2.2.2
scikit-learn==1.5.0
matplotlib==3.9.0
seaborn==0.13.2
jupyter==1.0.0
```
