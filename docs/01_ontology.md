# Ontology — Schema Đồ Thị Tri Thức

## 1. Tổng quan thiết kế

Ontology của ViFoodKG được thiết kế theo nguyên tắc:

- **Thực dụng:** chỉ mô hình hóa những gì thực sự có thể trích xuất được từ nhãn sản phẩm và nguồn dữ liệu hiện có
- **Tương thích chuẩn quốc tế:** mở rộng từ [FoodOn](https://foodon.org/) và liên kết với Codex Alimentarius, Wikidata
- **Phù hợp quy định Việt Nam:** tương thích [Thông tư 29/2023/TT-BYT](https://vanban.chinhphu.vn/?pageid=27160&docid=209434) (hiệu lực 01/01/2026), [Nghị định 43/2017/NĐ-CP](https://vanban.chinhphu.vn/default.aspx?pageid=27160&docid=189385) và [Nghị định 111/2021/NĐ-CP](https://vanban.chinhphu.vn/?pageid=27160&docid=204681)

---

## 2. Entities (Nút)

### 2.1 Product
Đại diện cho một sản phẩm thực phẩm đóng gói cụ thể.

| Thuộc tính | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `product_id` | String | Có | ID nội bộ (hash từ tên + thương hiệu) |
| `name_vi` | String | Có | Tên sản phẩm tiếng Việt |
| `name_en` | String | Không | Tên sản phẩm tiếng Anh (nếu có) |
| `barcode` | String | Không | Mã vạch EAN-13 |
| `brand` | String | Có | Thương hiệu |
| `category` | String | Có | Nhóm sản phẩm (xem mục 4) |
| `serving_size_g` | Float | Không | Khẩu phần ăn (gram) |
| `net_weight_g` | Float | Không | Khối lượng tịnh (gram) |
| `source` | String | Có | Nguồn dữ liệu gốc |

### 2.2 Ingredient
Nguyên liệu / thành phần trong sản phẩm.

| Thuộc tính | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `ingredient_id` | String | Có | ID canonical (ưu tiên FoodOn IRI) |
| `name_vi` | String | Có | Tên chuẩn hóa tiếng Việt |
| `name_en` | String | Không | Tên tiếng Anh |
| `foodon_iri` | URI | Không | Liên kết FoodOn |
| `wikidata_id` | String | Không | Liên kết Wikidata (Q-number) |

### 2.3 Additive
Phụ gia thực phẩm, có mã định danh theo hệ thống Codex Alimentarius.

| Thuộc tính | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `additive_id` | String | Có | Codex E-number (vd: E471) hoặc INS number |
| `name_vi` | String | Có | Tên tiếng Việt |
| `name_en` | String | Không | Tên tiếng Anh (INCI) |
| `function_type` | String | Có | Chức năng (xem mục 5) |
| `codex_code` | String | Không | Mã Codex đầy đủ |
| `permitted_in_vn` | Boolean | Không | Có được phép dùng tại VN không |

### 2.4 Nutrient
Chỉ số dinh dưỡng (tính trên 100g/100ml hoặc theo khẩu phần).

| Thuộc tính | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `nutrient_type` | Enum | Có | Loại dinh dưỡng (xem mục 6) |
| `value_per_100g` | Float | Có | Giá trị trên 100g sản phẩm |
| `unit` | String | Có | Đơn vị (kcal, g, mg, µg) |
| `daily_value_pct` | Float | Không | % nhu cầu khuyến nghị hàng ngày |

### 2.5 Allergen
Dị ứng nguyên theo danh mục Codex và quy định ghi nhãn.

| Thuộc tính | Kiểu | Mô tả |
|---|---|---|
| `allergen_id` | String | ID chuẩn (vd: `MILK`, `GLUTEN`, `SOY`) |
| `name_vi` | String | Tên tiếng Việt |
| `codex_code` | String | Mã Codex tương ứng |

### 2.6 Brand
Thương hiệu / nhà sản xuất.

| Thuộc tính | Kiểu | Mô tả |
|---|---|---|
| `brand_id` | String | ID nội bộ |
| `name` | String | Tên thương hiệu |
| `country` | String | Quốc gia (mặc định: VN) |
| `parent_company` | String | Công ty mẹ (nếu có) |

### 2.7 Category
Phân loại sản phẩm theo nhóm thực phẩm.

| Thuộc tính | Kiểu | Mô tả |
|---|---|---|
| `category_id` | String | ID phân cấp (vd: `CANDY.SOFT`) |
| `name_vi` | String | Tên tiếng Việt |
| `parent_category` | String | Danh mục cha |

---

## 3. Relations (Cạnh)

```
Product  ──[HAS_INGREDIENT {order: int}]──►  Ingredient
Product  ──[HAS_ADDITIVE]──────────────────►  Additive
Product  ──[HAS_NUTRIENT {value, unit}]────►  Nutrient
Product  ──[HAS_ALLERGEN {declared: bool}]─►  Allergen
Product  ──[BELONGS_TO]────────────────────►  Category
Product  ──[PRODUCED_BY]───────────────────►  Brand
Additive ──[HAS_FUNCTION]──────────────────►  AdditiveFunction
Category ──[IS_SUBCATEGORY_OF]─────────────►  Category
```

**Thuộc tính trên cạnh:**

| Cạnh | Thuộc tính | Mô tả |
|---|---|---|
| `HAS_INGREDIENT` | `order` | Thứ tự xuất hiện trong danh sách thành phần |
| `HAS_NUTRIENT` | `value`, `unit`, `per_serving` | Giá trị dinh dưỡng |
| `HAS_ALLERGEN` | `declared` | Có ghi rõ trên nhãn không (hay chỉ "có thể chứa") |

---

## 4. Phân loại sản phẩm (Category Taxonomy)

```
FOOD_PRODUCT
├── CANDY
│   ├── CANDY.HARD          (kẹo cứng)
│   ├── CANDY.SOFT          (kẹo mềm, kẹo dẻo)
│   ├── CANDY.CHOCOLATE     (socola)
│   └── CANDY.GUM           (kẹo cao su)
├── BISCUIT
│   ├── BISCUIT.CRACKER     (bánh quy mặn)
│   ├── BISCUIT.COOKIE      (bánh quy ngọt)
│   └── BISCUIT.WAFER       (bánh xốp)
├── SNACK
│   ├── SNACK.CHIP          (snack chiên)
│   └── SNACK.PUFFED        (snack phồng)
├── DAIRY
│   ├── DAIRY.FRESH_MILK    (sữa tươi)
│   ├── DAIRY.POWDER_MILK   (sữa bột)
│   ├── DAIRY.YOGURT        (sữa chua)
│   ├── DAIRY.CHEESE        (phô mai)
│   └── DAIRY.CONDENSED     (sữa đặc có đường)
└── INSTANT
    ├── INSTANT.NOODLE      (mì ăn liền)
    ├── INSTANT.PORRIDGE    (cháo ăn liền)
    └── INSTANT.PROCESSED   (xúc xích, pate, thịt hộp)
```

---

## 5. Chức năng phụ gia (AdditiveFunction)

Theo phân loại Codex Alimentarius:

| Mã | Tên tiếng Việt | Ví dụ E-number |
|---|---|---|
| `PRESERVATIVE` | Chất bảo quản | E200, E211, E202 |
| `ANTIOXIDANT` | Chất chống oxy hóa | E300, E306, E320 |
| `EMULSIFIER` | Chất nhũ hóa | E322, E471, E472 |
| `STABILIZER` | Chất ổn định | E412, E415, E407 |
| `THICKENER` | Chất làm dày | E1400, E1422, E466 |
| `COLOR` | Chất tạo màu | E102, E110, E129 |
| `FLAVOR_ENHANCER` | Chất tăng cường hương vị | E621, E627, E631 |
| `SWEETENER` | Chất tạo ngọt | E950, E951, E955 |
| `ACIDITY_REGULATOR` | Chất điều chỉnh độ axit | E330, E331, E296 |
| `RAISING_AGENT` | Chất làm nở | E500, E503, E450 |
| `SEQUESTRANT` | Chất tạo phức / chất giữ kim loại | E385, E386, E452 |
| `HUMECTANT` | Chất giữ ẩm | E420, E421, E422 |

---

## 6. Loại dinh dưỡng (NutrientType)

Tối thiểu 5 chỉ số bắt buộc theo QCVN 2024 (Thông tư 43 sửa đổi):

| Mã | Tên | Đơn vị |
|---|---|---|
| `ENERGY` | Năng lượng | kcal |
| `PROTEIN` | Chất đạm | g |
| `FAT_TOTAL` | Chất béo tổng | g |
| `FAT_SATURATED` | Chất béo bão hòa | g |
| `CARBOHYDRATE` | Carbohydrate tổng | g |
| `SUGAR` | Đường | g |
| `SODIUM` | Natri | mg |
| `FIBER` | Chất xơ | g |
| `CALCIUM` | Canxi | mg |
| `VITAMIN_D` | Vitamin D | µg |
| `VITAMIN_C` | Vitamin C | mg |
| `IRON` | Sắt | mg |

---

## 7. Ràng buộc Ontology

Các ràng buộc dựa trên [Thông tư 29/2023/TT-BYT](https://vanban.chinhphu.vn/?pageid=27160&docid=209434) (hiệu lực 01/01/2026), [Nghị định 43/2017/NĐ-CP](https://vanban.chinhphu.vn/default.aspx?pageid=27160&docid=189385) và [Nghị định 111/2021/NĐ-CP](https://vanban.chinhphu.vn/?pageid=27160&docid=204681).

### 7.1 Ràng buộc chung

| Ràng buộc | Áp dụng cho | Mô tả |
|---|---|---|
| Phải có ít nhất 1 `HAS_INGREDIENT` | Tất cả `Product` | Tránh node trống |
| `Additive.function_type` phải thuộc `AdditiveFunction` | Tất cả `Additive` | Closed vocabulary |
| `HAS_INGREDIENT.order` là số nguyên dương, không trùng trong cùng sản phẩm | Tất cả `HAS_INGREDIENT` | Thứ tự thành phần |
| `Nutrient.value_per_100g` ≥ 0 | Tất cả `Nutrient` | Ràng buộc miền giá trị |

### 7.2 Ràng buộc dinh dưỡng bắt buộc (theo Thông tư 29/2023/TT-BYT)

**5 chỉ số bắt buộc cho mọi sản phẩm:**

| Chỉ số | Mã trong KG | Bắt buộc với |
|---|---|---|
| Năng lượng | `ENERGY` | Tất cả sản phẩm |
| Chất đạm | `PROTEIN` | Tất cả sản phẩm |
| Carbohydrat | `CARBOHYDRATE` | Tất cả sản phẩm |
| Chất béo | `FAT_TOTAL` | Tất cả sản phẩm |
| Natri | `SODIUM` | Tất cả sản phẩm |

**Chỉ số bắt buộc bổ sung theo loại sản phẩm:**

| Chỉ số | Mã trong KG | Bắt buộc với |
|---|---|---|
| Đường tổng số | `SUGAR` | Sản phẩm có thêm đường: nước giải khát, sữa chế biến, và các thực phẩm bổ sung đường |
| Chất béo bão hòa | `FAT_SATURATED` | Thực phẩm chiên rán |

**Ràng buộc kiểm tra trong KG:**

```
CONSTRAINT_1: Tất cả Product phải có đủ {ENERGY, PROTEIN, CARBOHYDRATE, FAT_TOTAL, SODIUM}

CONSTRAINT_2: Product thuộc {DAIRY.FRESH_MILK, DAIRY.CONDENSED, SNACK.CHIP, SNACK.PUFFED}
              hoặc có SUGAR > 0 trong thành phần
              → bắt buộc có SUGAR

CONSTRAINT_3: Product thuộc {SNACK.CHIP, INSTANT.PROCESSED}
              hoặc được ghi nhãn "chiên", "rán", "fried"
              → bắt buộc có FAT_SATURATED
```

> **Lưu ý triển khai:** Trường `Product.category` và thông tin thành phần được dùng để tự động xác định CONSTRAINT_2 và CONSTRAINT_3 trong bước validation.
