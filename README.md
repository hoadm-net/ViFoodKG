# ViFoodKG — Đồ Thị Tri Thức Thực Phẩm Việt Nam

## Giới thiệu

ViFoodKG là một đồ thị tri thức (Knowledge Graph) cho thực phẩm đóng gói tiêu dùng tại Việt Nam, tập trung vào các nhóm sản phẩm mà trẻ em sử dụng thường xuyên: **bánh kẹo, sữa và các sản phẩm từ sữa, thực phẩm ăn liền**.

Nghiên cứu này đề xuất và hiện thực hóa một pipeline **tự động dựa trên LLM (GPT-5.4 nano)** để trích xuất, chuẩn hóa và xây dựng đồ thị tri thức từ nhiều nguồn dữ liệu thực phẩm, đồng thời cung cấp bộ độ đo định lượng để đánh giá độ hoàn chỉnh và chất lượng của KG thu được.

## Mục tiêu nghiên cứu

1. **Thiết kế ontology** đặc thù cho thực phẩm đóng gói Việt Nam: thành phần, phụ gia, dinh dưỡng, thương hiệu, dị ứng nguyên.
2. **Xây dựng pipeline tự động** dùng GPT-5.4 nano để trích xuất thông tin có cấu trúc từ nhãn sản phẩm và các nguồn dữ liệu thô.
3. **Xây dựng ViFoodKG** — đồ thị tri thức quy mô thực tế, lưu trữ trên Neo4j và xuất định dạng RDF/Turtle.
4. **Đánh giá định lượng** độ chính xác, độ hoàn chỉnh và tính nhất quán của KG thông qua bộ ground truth annotate thủ công.

> Các ứng dụng downstream (RAG, tăng cường NER trên bao bì...) là đối tượng của các nghiên cứu tiếp theo và **nằm ngoài phạm vi** bài báo này.

## Phạm vi dữ liệu

| Nhóm sản phẩm | Ví dụ |
|---|---|
| Bánh kẹo | Bánh quy, kẹo dẻo, snack, bánh tươi đóng gói |
| Sữa & sản phẩm từ sữa | Sữa tươi, sữa bột, sữa chua, phô mai, sữa đặc |
| Thực phẩm ăn liền | Mì ăn liền, cháo ăn liền, xúc xích, pate |

## Đóng góp chính

- **Ontology** cho thực phẩm đóng gói Việt Nam, mở rộng từ FoodOn, tương thích Codex Alimentarius
- **Dataset ground truth** gồm 300–500 sản phẩm annotate thủ công
- **Pipeline LLM-automated** sử dụng GPT-5.4 nano với ontology-guided prompting
- **Bộ độ đo đánh giá KG** toàn diện: correctness, completeness, consistency, coverage

## Cấu trúc tài liệu

```
docs/
├── 00_research_foundation.md  # Research questions, hypotheses, contributions
├── 01_ontology.md             # Schema, entities, relations, ràng buộc
├── 02_data_sources.md         # Nguồn dữ liệu và cách thu thập
├── 03_pipeline.md             # Pipeline LLM-automated chi tiết
├── 04_evaluation.md           # Bộ độ đo đánh giá KG
├── 05_tech_stack.md           # Công nghệ và công cụ sử dụng
└── 06_work_plan.md            # Kế hoạch triển khai
```

## Mô hình LLM

Nghiên cứu sử dụng **GPT-5.4 nano** (OpenAI) — mô hình nhỏ gọn, chi phí thấp, không có reasoning chain dài, phù hợp cho tác vụ trích xuất có cấu trúc với schema định nghĩa sẵn ở quy mô lớn.

Tham khảo: [OpenAI GPT-5.4 nano](https://developers.openai.com/api/docs/models/gpt-5.4-nano)
