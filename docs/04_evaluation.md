# Đánh Giá Chất Lượng Đồ Thị Tri Thức

## 1. Tổng quan

Đánh giá KG được thực hiện theo **4 chiều**: Correctness (độ chính xác), Completeness (độ hoàn chỉnh), Consistency (tính nhất quán), và Coverage (độ phủ). Tất cả đều có thể đo định lượng và so sánh giữa các biến thể pipeline.

**Tập đánh giá:** 300–500 sản phẩm ground truth annotate thủ công (xem [02_data_sources.md](02_data_sources.md)).

---

## 2. Correctness — Độ chính xác trích xuất

So sánh kết quả extraction của pipeline với ground truth tại cấp độ triple.

### 2.1 Triple-level Precision / Recall / F1

Một triple `(subject, predicate, object)` được tính là **đúng** khi:
- Entity matching: tên sau chuẩn hóa giống nhau (exact match hoặc canonical ID match)
- Relation: đúng loại quan hệ

```
Precision = |Triples đúng đã trích xuất| / |Tất cả triples đã trích xuất|
Recall    = |Triples đúng đã trích xuất| / |Tất cả triples trong ground truth|
F1        = 2 × Precision × Recall / (Precision + Recall)
```

Tính riêng cho từng loại triple:

| Loại triple | Ví dụ |
|---|---|
| HAS_INGREDIENT | (Sữa Vinamilk 100ml, HAS_INGREDIENT, đường) |
| HAS_ADDITIVE | (Sữa Vinamilk 100ml, HAS_ADDITIVE, E471) |
| HAS_NUTRIENT | (Sữa Vinamilk 100ml, HAS_NUTRIENT {energy: 67 kcal}) |
| HAS_ALLERGEN | (Sữa Vinamilk 100ml, HAS_ALLERGEN, MILK) |

### 2.2 Entity Linking Accuracy

Tỷ lệ thực thể được map đúng về canonical ID (Codex E-number / FoodOn IRI):

```
EL_Accuracy = |Entities được link đúng| / |Tất cả entities cần link|
```

### 2.3 Ingredient Order Accuracy

Thứ tự thành phần trong danh sách (quan trọng vì QCVN quy định thành phần nhiều nhất đứng đầu):

```
Order_Accuracy = |Products có đúng thứ tự thành phần| / |Tất cả products|
```

---

## 3. Completeness — Độ hoàn chỉnh

### 3.1 Schema Completeness

Tỷ lệ các trường bắt buộc trong ontology được điền có giá trị (không null):

```
Schema_Completeness(entity_type) = 
    Σ (filled_required_fields) / (total_required_fields × entity_count)
```

Tính riêng cho mỗi loại entity: Product, Ingredient, Additive.

### 3.2 Nutrient Fill Rate

Phản ánh mức độ tuân thủ quy định QCVN 2024 (5 chỉ số dinh dưỡng bắt buộc):

```
Nutrient_Fill_Rate = 
    |Products có đủ {ENERGY, PROTEIN, FAT, CARBOHYDRATE, SODIUM}|
    / |Tổng số products|
```

Tính thêm Fill Rate cho từng chỉ số riêng lẻ để xác định chỉ số nào thường bị thiếu.

### 3.3 Additive Coverage

```
Additive_Coverage = 
    |Additives được map thành công sang Codex E-number|
    / |Tổng số additives trong KG|
```

### 3.4 Population Density

Số triple trung bình cho mỗi product node — phản ánh "độ giàu thông tin":

```
Density = Tổng số triples / Số product nodes
```

So sánh với các Food KG tham chiếu (FoodKG, FKG.in).

---

## 4. Consistency — Tính nhất quán

### 4.1 Ontology Constraint Violation Rate

Đếm số vi phạm các ràng buộc được định nghĩa trong ontology:

```
Violation_Rate = |Triples vi phạm ràng buộc| / |Tổng số triples|
```

Các vi phạm cần kiểm tra:

| Loại vi phạm | Kiểm tra bằng |
|---|---|
| Thiếu nutrient bắt buộc | Cypher query |
| Giá trị dinh dưỡng ngoài khoảng hợp lệ | Rule-based validator |
| `function_type` không thuộc vocabulary | Cypher query |
| Duplicate ingredient trong cùng product | Cypher query |
| `HAS_INGREDIENT.order` trùng lặp | Cypher query |

### 4.2 Cross-Source Agreement

Với các sản phẩm xuất hiện trong nhiều nguồn (vd: cùng barcode trong Open Food Facts và web hãng), đo tỷ lệ nhất quán:

```
Agreement(field) = 
    |Cặp sources đồng ý giá trị field|
    / |Tổng số cặp sources có cùng sản phẩm|
```

Tính cho các trường: `name_vi`, `energy_kcal`, `ingredients` (Jaccard similarity).

### 4.3 Duplicate Entity Rate

Sau khi deduplication, đánh giá còn sót entity trùng không:

```
Duplicate_Rate = 
    |Cặp entities được xác nhận là trùng nhau bởi human reviewer|
    / |Tổng số entities trong KG|
```

---

## 5. Coverage — Độ phủ thị trường

### 5.1 Brand Coverage

```
Brand_Coverage = 
    |Thương hiệu có trong KG|
    / |Thương hiệu có trong top-20 thị phần VN|
```

### 5.2 Category Distribution

Phân phối sản phẩm theo category:
- Bánh kẹo, Sữa, Ăn liền (3 nhóm chính)
- Biểu đồ histogram

### 5.3 Additive Completeness vs QCVN

```
QCVN_Coverage = 
    |Phụ gia trong KG có trong danh mục QCVN|
    / |Tổng phụ gia trong danh mục QCVN|
```

---

## 6. Inter-Annotator Agreement (Ground Truth Quality)

Trước khi dùng ground truth để đánh giá pipeline, cần chứng minh ground truth đáng tin cậy:

```
Cohen's Kappa (κ) cho từng field:
- Ingredient list (Jaccard): mục tiêu κ ≥ 0.80
- Additive list (Jaccard): mục tiêu κ ≥ 0.80
- Nutrient values (exact match ±5%): mục tiêu κ ≥ 0.90
- Category: mục tiêu κ ≥ 0.85
```

---

## 7. Thống kê mô tả KG cuối (KG Statistics)

Báo cáo trong phần Results của bài báo:

| Thống kê | Giá trị |
|---|---|
| Tổng số Product nodes | ~ |
| Tổng số Ingredient nodes (unique) | ~ |
| Tổng số Additive nodes (unique) | ~ |
| Tổng số Nutrient values | ~ |
| Tổng số triples | ~ |
| Số thương hiệu (Brand) | ~ |
| % Additive có E-number | ~ |
| % Product có đủ 5 dinh dưỡng bắt buộc | ~ |
| Trung bình ingredients / product | ~ |
| Trung bình additives / product | ~ |
