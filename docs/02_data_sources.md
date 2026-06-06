# Nguồn Dữ Liệu

## 1. Tổng quan

ViFoodKG được xây dựng từ sự kết hợp của các nguồn dữ liệu công khai, dữ liệu crawl từ trang web nhà sản xuất, và bộ ground truth annotate thủ công. Chiến lược đa nguồn giúp tăng độ phủ và cho phép kiểm tra chéo tính nhất quán.

```
┌──────────────────────────────────────────────────┐
│               Nguồn dữ liệu                      │
│                                                  │
│  [Open Food Facts]   [Trang web hãng]            │
│  [USDA FoodData]     [Quy định VN]               │
│  [Codex Alimentarius][Ground truth thủ công]     │
└────────────────────┬─────────────────────────────┘
                     ↓
             Pipeline thu thập
                     ↓
           Dữ liệu thô chuẩn hóa
```

---

## 2. Chi tiết từng nguồn

### 2.1 Open Food Facts

| Thuộc tính | Thông tin |
|---|---|
| URL | https://world.openfoodfacts.org |
| Cách lấy | Export CSV/JSON, filter `countries_tags=en:vietnam` |
| Nội dung | Tên SP, barcode, thương hiệu, thành phần, dinh dưỡng |
| Ưu điểm | Dữ liệu cộng đồng lớn, có ảnh nhãn, open license (ODbL) |
| Hạn chế | Chất lượng không đồng đều, thiếu chuẩn hóa tiếng Việt |
| Ước tính SP VN | 3,000–8,000 entries (chất lượng biến động) |

**Tiền xử lý cần thiết:**
- Lọc entries có đủ trường `ingredients_text` và ít nhất 3 chỉ số dinh dưỡng
- Xử lý mã hóa Unicode tiếng Việt (NFD → NFC)
- Loại bỏ duplicate theo barcode

### 2.2 Trang web nhà sản xuất (Web Crawling)

Crawl trực tiếp từ trang sản phẩm của các thương hiệu lớn tại Việt Nam:

| Thương hiệu | Nhóm sản phẩm | Ghi chú |
|---|---|---|
| Vinamilk | Sữa các loại | JS-heavy, dùng Playwright |
| TH True Milk | Sữa tươi, sữa chua | |
| Nestle Việt Nam | Sữa bột, mì, bánh | Có cả tiếng Việt và Anh |
| Kinh Đô (Mondelēz) | Bánh kẹo | |
| Masan | Mì ăn liền, thực phẩm chế biến | |
| Acecook | Mì ăn liền | |
| Vifon | Mì, phở ăn liền | |
| Bibica | Bánh kẹo | |

**Phương pháp crawl:**
- Dùng **Playwright** cho trang JavaScript-heavy
- Dùng **BeautifulSoup** cho trang HTML tĩnh
- Trích xuất structured data từ JSON-LD (schema.org/Product) khi có
- Fallback: LLM parse raw HTML → JSON

**Lưu ý pháp lý:** Chỉ crawl dữ liệu công khai trên trang sản phẩm, tôn trọng `robots.txt`, không lưu trữ ảnh có bản quyền.

### 2.3 USDA FoodData Central

| Thuộc tính | Thông tin |
|---|---|
| URL | https://fdc.nal.usda.gov |
| Cách lấy | REST API (miễn phí, cần API key) |
| Nội dung | Giá trị dinh dưỡng chuẩn của nguyên liệu thô |
| Vai trò trong ViFoodKG | Tham chiếu chuẩn hóa giá trị dinh dưỡng cho `Ingredient` nodes |

Ví dụ: ingredient "đường trắng" → map sang USDA FDC ID 1986 (Sugars, granulated) → lấy giá trị energy/carb tham chiếu.

### 2.4 Codex Alimentarius

| Thuộc tính | Thông tin |
|---|---|
| URL | https://www.fao.org/fao-who-codexalimentarius |
| Cách lấy | Download XML/CSV từ GSFA (General Standard for Food Additives) |
| Nội dung | Danh sách phụ gia được phép, INS/E-number, chức năng, giới hạn sử dụng |
| Vai trò | Canonical reference cho tất cả `Additive` nodes |

**Dữ liệu cần lấy:**
- Bảng GSFA: INS number, tên Anh/Pháp, function class
- Map INS → E-number (cho tương thích EU)

### 2.5 Quy định Việt Nam

| Văn bản | Nội dung liên quan | Nguồn text |
|---|---|---|
| [Thông tư 29/2023/TT-BYT](https://thuvienphapluat.vn/van-ban/The-thao-Y-te/Thong-tu-29-2023-TT-BYT-ghi-thanh-phan-dinh-duong-tren-nhan-thuc-pham-509492.aspx) | Ghi nhãn dinh dưỡng (hiệu lực 01/01/2026) | thuvienphapluat.vn |
| [Thông tư 24/2019/TT-BYT](https://thuvienphapluat.vn/van-ban/The-thao-Y-te/Thong-tu-24-2019-TT-BYT-quy-dinh-ve-quan-ly-va-su-dung-phu-gia-thuc-pham-360857.aspx) | Danh mục ~400 phụ gia được phép dùng tại VN, kèm tên tiếng Việt chính thức | thuvienphapluat.vn |
| [Nghị định 43/2017/NĐ-CP](https://thuvienphapluat.vn/van-ban/Thuong-mai/Nghi-dinh-43-2017-ND-CP-nhan-hang-hoa-346310.aspx) | Nhãn hàng hóa | thuvienphapluat.vn |
| [Nghị định 111/2021/NĐ-CP](https://thuvienphapluat.vn/van-ban/Thuong-mai/Nghi-dinh-111-2021-ND-CP-sua-doi-Nghi-dinh-43-2017-ND-CP-497099.aspx) | Sửa đổi Nghị định 43/2017 | thuvienphapluat.vn |

> **Lưu ý kỹ thuật:** File PDF tải từ chinhphu.vn là ảnh scan, không có text layer. Dùng thuvienphapluat.vn để scrape HTML text trực tiếp — không cần OCR.

**Vai trò:**
- **TT24/2019**: nguồn chính cho `Additive.name_vi` (tên tiếng Việt chính thức) và `Additive.permitted_in_vn`
- **TT29/2023**: xác nhận 5 chỉ số dinh dưỡng bắt buộc và điều kiện áp dụng SUGAR, FAT_SATURATED
- **ND43 + ND111**: tham chiếu quy định ghi nhãn chung

### 2.6 Ground Truth — Annotate thủ công

Đây là nguồn quan trọng nhất để đánh giá pipeline.

| Thông số | Giá trị |
|---|---|
| Quy mô | 300–500 sản phẩm |
| Phân bố | ~100 bánh kẹo, ~150 sữa/sản phẩm từ sữa, ~150 ăn liền |
| Annotator | 2 người annotation độc lập + 1 người resolve conflict |
| Nguồn ảnh | Chụp trực tiếp nhãn sản phẩm ngoài thị trường |
| Inter-annotator agreement | Đo bằng Cohen's Kappa (mục tiêu ≥ 0.80) |

**Quy trình annotation:**
1. Chụp ảnh nhãn sản phẩm (mặt trước + mặt sau)
2. OCR bằng PaddleOCR
3. Annotator A tạo JSON theo schema
4. Annotator B review độc lập
5. Resolve conflict → final ground truth JSON

---

## 3. Ước tính quy mô dữ liệu cuối

| Nguồn | SP ước tính (sau lọc) |
|---|---|
| Open Food Facts (VN) | 1,500–2,000 |
| Crawl web hãng | 800–1,200 |
| Ground truth thủ công | 300–500 |
| **Tổng (sau dedup)** | **~3,000–4,500 sản phẩm** |

---

## 4. Xử lý chất lượng dữ liệu

| Vấn đề | Cách xử lý |
|---|---|
| Tên thành phần không chuẩn | GPT-5.4 nano normalize → canonical name |
| Thiếu E-number | Fuzzy match tên phụ gia với bảng Codex |
| Giá trị dinh dưỡng không hợp lệ | Rule-based validation + flag outlier |
| Duplicate sản phẩm | Match theo barcode, sau đó fuzzy match tên + thương hiệu |
| Dữ liệu tiếng Anh lẫn tiếng Việt | GPT-5.4 nano dịch/chuẩn hóa |
| Ảnh nhãn chất lượng kém | PaddleOCR + LLM post-correction |
