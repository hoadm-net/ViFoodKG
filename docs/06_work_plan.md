# Kế Hoạch Xây Dựng ViFoodKG

## Tổng quan

```
Bước 1: Crawl nguồn cố định
    └─→ [Schema Validation & Điều chỉnh]
Bước 2: Crawl trang web nhà sản xuất VN
    └─→ [Deduplication & Merge]
Bước 3: Ground truth từ ảnh bao bì (ViFoodLabel)
    └─→ [Đánh giá KG]
```

---

## Bước 1 — Crawl nguồn dữ liệu cố định

**Mục tiêu:** Xây dựng skeleton KG với dữ liệu chuẩn, ổn định làm nền tảng.

### 1.1 Open Food Facts

| Hạng mục | Chi tiết |
|---|---|
| Input | Export CSV toàn bộ, filter `countries_tags=en:vietnam` |
| Output | Danh sách sản phẩm VN với tên, barcode, thành phần, dinh dưỡng thô |
| Lọc | Giữ lại entries có `ingredients_text` không rỗng và ≥ 3 chỉ số dinh dưỡng |
| Ước tính | 1,500–2,000 sản phẩm sau lọc |

### 1.2 Codex Alimentarius + Thông tư 24/2019 → Additive Lookup Table

Đây là task xây dựng bảng tra cứu phụ gia — reference dùng xuyên suốt toàn pipeline.

**Input:**
- `data/raw/codex/openfoodfacts_additives_taxonomy.txt` — 645 entries, E-number + tên Anh + Wikidata
- [Thông tư 24/2019/TT-BYT](https://thuvienphapluat.vn/van-ban/The-thao-Y-te/Thong-tu-24-2019-TT-BYT-quy-dinh-ve-quan-ly-va-su-dung-phu-gia-thuc-pham-360857.aspx) — ~400 phụ gia được phép tại VN, kèm tên tiếng Việt chính thức

**Output:** `data/processed/codex_additives.json` + `.csv`

**Sub-tasks chi tiết:**

| ST | Công việc | Approach |
|---|---|---|
| ST-1.1 | Parse taxonomy file → structured dict | Python parser theo block E-number |
| ST-1.2 | Map `additives_classes` → `AdditiveFunction` vocabulary | Dict mapping cố định (gồm SEQUESTRANT, HUMECTANT mới bổ sung) |
| ST-1.3 | Lấy tên tiếng Việt chính thức | Scrape TT24/2019 từ thuvienphapluat.vn → tên VN cho entries có trong TT24; entries còn lại giữ nguyên tên tiếng Anh |
| ST-1.4 | Điền `permitted_in_vn` | `true` nếu có trong TT24, `false` nếu không |
| ST-1.5 | Export JSON + CSV | Output cuối, index theo E-number |

> **Lưu ý ST-1.3:** Source: `data/raw/regulations/phu-luc-24-2019-TT-BYT.docx` (Table 0, 400 entries). Tên tiếng Việt trong TT24 là tên **chính thức trên nhãn hàng VN** (mix loanword và Việt hóa). Nếu không có trong TT24 → dùng tên tiếng Anh làm fallback.

### 1.3 USDA FoodData Central

| Hạng mục | Chi tiết |
|---|---|
| Input | REST API, lấy SR Legacy và Foundation Foods |
| Output | Giá trị dinh dưỡng tham chiếu cho các nguyên liệu thô phổ biến |
| Vai trò | Chuẩn hóa và validate giá trị dinh dưỡng của `Ingredient` nodes |

**Đầu ra Bước 1:**
- KG skeleton với ~1,500–2,000 product nodes
- `data/processed/codex_additives.json` — lookup table đầy đủ cho toàn dự án
- Bảng danh mục phụ gia được phép tại VN (từ TT24/2019)

---

### Schema Validation sau Bước 1

Trước khi chuyển sang Bước 2, chạy kiểm tra nhanh trên dữ liệu thực:

- Tỷ lệ điền đủ 5 chỉ số dinh dưỡng bắt buộc đạt bao nhiêu %?
- Có entity type nào thiếu dữ liệu nghiêm trọng không?
- Các constraint ontology (mục 7, [01_ontology.md](01_ontology.md)) có vi phạm nhiều không?

Kết quả kiểm tra này có thể dẫn đến **điều chỉnh nhỏ schema** trước khi crawl quy mô lớn ở Bước 2 — tránh tốn công re-populate sau.

---

## Bước 2 — Crawl trang web nhà sản xuất

**Mục tiêu:** Làm giàu KG với sản phẩm tiêu dùng thực tế tại VN, đặc biệt các sản phẩm trẻ em phổ biến không có trong Open Food Facts.

### 2.1 Danh sách nguồn

Các trang web cụ thể sẽ được cung cấp bởi tác giả (bổ sung vào đây khi có). Nhóm mục tiêu ban đầu:

| Nhóm sản phẩm | Thương hiệu ưu tiên |
|---|---|
| Sữa & sản phẩm từ sữa | Vinamilk, TH True Milk, Nestle VN, Abbott, Friso |
| Bánh kẹo | Kinh Đô (Mondelēz), Bibica, Orion, Lotte VN |
| Thực phẩm ăn liền | Acecook, Masan (Omachi, Kokomi), Vifon, Asia Foods |

### 2.2 Quy trình crawl

```
Playwright/BeautifulSoup
    ↓
Trích xuất raw text trang sản phẩm
    ↓
GPT-5.4 nano extraction (prompt từ 03_pipeline.md)
    ↓
Entity normalization & linking (Codex, FoodOn)
    ↓
Deduplication với dữ liệu Bước 1 (match barcode → fuzzy name+brand)
    ↓
Merge: ưu tiên giữ nguồn chất lượng cao hơn (web hãng > Open Food Facts)
```

### 2.3 Kiểm soát chất lượng

- Mỗi domain crawl xong → chạy ngay constraint check trước khi merge vào KG chính
- Ghi log rõ nguồn (`source` field) để truy vết khi cần

**Đầu ra Bước 2:**
- KG mở rộng ~3,000–4,500 product nodes
- Coverage tốt cho top brands thị trường VN

---

## Bước 3 — Ground Truth từ ảnh bao bì (ViFoodLabel)

**Mục tiêu:** Lọc từ tập ảnh ViFoodLabel lấy ~100–150 ảnh có đủ thông tin để làm ground truth đánh giá KG.

### 3.1 Tiêu chí chọn ảnh

Từ ~300 ảnh ViFoodLabel, chọn những ảnh thỏa mãn **đồng thời**:

| Tiêu chí | Yêu cầu |
|---|---|
| Tên sản phẩm | Đọc được rõ ràng |
| Thương hiệu | Xác định được |
| Danh sách thành phần | Có và đọc được (≥ 3 thành phần) |
| Bảng dinh dưỡng | Có ít nhất 3 trong 5 chỉ số bắt buộc |

Ảnh chỉ có một phần (ví dụ chỉ bảng dinh dưỡng, không có tên SP) → loại khỏi GT.

**Phân bố mục tiêu (~150 ảnh):**

| Nhóm | Số ảnh |
|---|---|
| Bánh kẹo | ~50 |
| Sữa & sản phẩm từ sữa | ~50 |
| Thực phẩm ăn liền | ~50 |

### 3.2 Quy trình xử lý

```
~300 ảnh ViFoodLabel
    ↓
Lọc theo tiêu chí → ~100–150 ảnh đủ điều kiện
    ↓
OCR: PaddleOCR (model tiếng Việt)
    ↓
Annotate thủ công → JSON theo schema KG (2 annotators, resolve conflict)
    ↓
Ground Truth hoàn chỉnh
```

### 3.3 Mapping BIO annotation → KG schema

Annotation BIO có sẵn trong ViFoodLabel có thể tận dụng để giảm công annotate:

| BIO label (ViFoodLabel) | Field trong ViFoodKG |
|---|---|
| `B-ING / I-ING` | `Ingredient.name_vi` |
| `B-ADD / I-ADD` | `Additive.name_vi` |
| `B-NUT / I-NUT` | `Nutrient.nutrient_type` |
| `B-VAL / I-VAL` | `Nutrient.value_per_100g` |

> Cần xác nhận tên BIO label thực tế khi có dữ liệu.

### 3.4 Dùng GT để đánh giá

GT ~100–150 sản phẩm đủ để tính toàn bộ metrics trong [04_evaluation.md](04_evaluation.md):
- Triple Precision / Recall / F1
- Schema Completeness, Nutrient Fill Rate
- Ablation study (rule-based vs zero-shot vs few-shot)

---

## Tóm tắt đầu ra của từng bước

| Bước | Đầu ra chính |
|---|---|
| Bước 1 | KG skeleton ~1,500–2,000 nodes + bảng tra cứu Codex/QCVN |
| Schema Validation | Schema ổn định, sẵn sàng scale |
| Bước 2 | KG đầy đủ ~3,000–4,500 nodes, coverage tốt thị trường VN |
| Bước 3 | GT ~100–150 sản phẩm + kết quả đánh giá đầy đủ |
