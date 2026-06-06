# Data Directory

Thư mục `raw/` và `processed/` không được commit vào repo (xem `.gitignore`).
Dưới đây là hướng dẫn tải lại dữ liệu khi cần.

## Cấu trúc

```
data/
├── raw/
│   ├── regulations/     # Văn bản pháp luật Việt Nam (PDF)
│   ├── codex/           # Dữ liệu Codex Alimentarius
│   └── ground_truth/    # Ảnh bao bì từ ViFoodLabel (thêm thủ công)
└── processed/           # Output sau pipeline
```

---

## raw/regulations/ — Văn bản pháp luật

> **Lưu ý:** PDF tải từ chinhphu.vn là ảnh scan, không có text layer.
> Pipeline dùng thuvienphapluat.vn để scrape HTML text — không cần OCR.
> Các file PDF dưới đây chỉ để lưu trữ tham chiếu.

| File | Nguồn PDF (tham chiếu) | Nguồn text (dùng trong pipeline) |
|---|---|---|
| `TT29-2023-TT-BYT_ghi-nhan-dinh-duong.pdf` | [chinhphu.vn](https://vanban.chinhphu.vn/?pageid=27160&docid=209434) | [thuvienphapluat.vn](https://thuvienphapluat.vn/van-ban/The-thao-Y-te/Thong-tu-29-2023-TT-BYT-ghi-thanh-phan-dinh-duong-tren-nhan-thuc-pham-509492.aspx) |
| `TT24-2019-TT-BYT_danh-muc-phu-gia.pdf` | [chinhphu.vn](https://vanban.chinhphu.vn/?pageid=27160&docid=197320) | [thuvienphapluat.vn](https://thuvienphapluat.vn/van-ban/The-thao-Y-te/Thong-tu-24-2019-TT-BYT-quy-dinh-ve-quan-ly-va-su-dung-phu-gia-thuc-pham-360857.aspx) |
| `ND43-2017-ND-CP_nhan-hang-hoa.pdf` | [chinhphu.vn](https://vanban.chinhphu.vn/default.aspx?pageid=27160&docid=189385) | [thuvienphapluat.vn](https://thuvienphapluat.vn/van-ban/Thuong-mai/Nghi-dinh-43-2017-ND-CP-nhan-hang-hoa-346310.aspx) |
| `ND111-2021-ND-CP_sua-doi-ND43.pdf` | [chinhphu.vn](https://vanban.chinhphu.vn/?pageid=27160&docid=204681) | [thuvienphapluat.vn](https://thuvienphapluat.vn/van-ban/Thuong-mai/Nghi-dinh-111-2021-ND-CP-sua-doi-Nghi-dinh-43-2017-ND-CP-497099.aspx) |

**Tải lại PDF (nếu cần):**

```bash
curl -L "https://datafiles.chinhphu.vn/cpp/files/vbpq/2024/01/29-byt.signed.pdf" -o data/raw/regulations/TT29-2023-TT-BYT_ghi-nhan-dinh-duong.pdf
curl -L "https://datafiles.chinhphu.vn/cpp/files/vbpq/2019/07/5927.signed.pdf"   -o data/raw/regulations/TT24-2019-TT-BYT_danh-muc-phu-gia.pdf
curl -L "https://datafiles.chinhphu.vn/cpp/files/vbpq/2017/04/43.signed.pdf"    -o data/raw/regulations/ND43-2017-ND-CP_nhan-hang-hoa.pdf
curl -L "https://datafiles.chinhphu.vn/cpp/files/vbpq/2021/12/111.signed.pdf"   -o data/raw/regulations/ND111-2021-ND-CP_sua-doi-ND43.pdf
```

---

## raw/codex/ — Codex Alimentarius

| File | Nguồn | Lệnh tải |
|---|---|---|
| `openfoodfacts_additives_taxonomy.txt` | [Open Food Facts GitHub](https://github.com/openfoodfacts/openfoodfacts-server) | `curl -L "https://raw.githubusercontent.com/openfoodfacts/openfoodfacts-server/main/taxonomies/additives.txt" -o data/raw/codex/openfoodfacts_additives_taxonomy.txt` |

> File taxonomy chứa E-number, tên tiếng Anh, tên tiếng Việt (một số) và Wikidata ID cho toàn bộ phụ gia Codex.
> FAO GSFA online (fao.org) bị Cloudflare bảo vệ — cần tải thủ công từ https://www.fao.org/gsfaonline nếu cần bản chính thức.

---

## raw/ground_truth/ — Ảnh bao bì (ViFoodLabel)

Thêm thủ công ~100–150 ảnh bao bì đủ điều kiện từ dự án ViFoodLabel.
Xem tiêu chí chọn ảnh tại [docs/06_work_plan.md](../docs/06_work_plan.md) mục 3.1.
