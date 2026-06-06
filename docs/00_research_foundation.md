# Nền Tảng Nghiên Cứu

> File này là tài liệu tham chiếu cốt lõi của toàn bộ nghiên cứu.
> Mọi quyết định thiết kế, thực nghiệm, và đánh giá đều phải bám sát các RQ và H dưới đây.

---

## 1. Bối cảnh & Động lực (Motivation)

Thực phẩm đóng gói dành cho trẻ em (bánh kẹo, sữa, thực phẩm ăn liền) ngày càng phổ biến tại Việt Nam, nhưng thông tin về thành phần, phụ gia và giá trị dinh dưỡng còn phân tán, không chuẩn hóa, và khó tra cứu có hệ thống. Hiện chưa tồn tại một đồ thị tri thức nào tổ chức các thực thể này cho bối cảnh thực phẩm Việt Nam.

Trong khi đó, các LLM thế hệ mới (đặc biệt các mô hình nhỏ gọn như GPT-5.4 nano) cho thấy khả năng trích xuất thông tin có cấu trúc từ văn bản tự nhiên với chi phí thấp — mở ra khả năng xây dựng KG quy mô lớn một cách tự động mà không đòi hỏi nhân công annotation toàn bộ.

---

## 2. Research Questions (Câu hỏi nghiên cứu)

### RQ1 — Khả năng xây dựng tự động
> **Liệu một pipeline dựa trên LLM có thể tự động xây dựng đồ thị tri thức thực phẩm đóng gói Việt Nam đạt chất lượng đủ tin cậy để sử dụng trong nghiên cứu?**

Câu hỏi này xem xét toàn bộ pipeline từ thu thập dữ liệu đến KG population, đánh giá xem mức độ tự động hóa có thể đạt được mà không cần annotation thủ công toàn bộ.

### RQ2 — Chất lượng trích xuất
> **GPT-5.4 nano với ontology-guided prompting đạt độ chính xác như thế nào trong việc trích xuất thành phần, phụ gia và thông tin dinh dưỡng từ nhãn thực phẩm tiếng Việt?**

Câu hỏi này đánh giá chất lượng extraction ở cấp độ entity và triple, so sánh với ground truth được annotate thủ công từ ảnh bao bì thực tế.

### RQ3 — Hiệu quả của few-shot prompting
> **Few-shot prompting cải thiện chất lượng extraction so với zero-shot prompting và rule-based baseline ở mức độ nào?**

Câu hỏi này thúc đẩy ablation study để xác định cấu hình prompt tối ưu và định lượng đóng góp của từng yếu tố trong pipeline.

### RQ4 — Độ hoàn chỉnh của KG
> **KG được xây dựng tự động đáp ứng các ràng buộc ontology và yêu cầu ghi nhãn dinh dưỡng bắt buộc theo Thông tư 29/2023/TT-BYT ở mức độ nào?**

Câu hỏi này đánh giá completeness và consistency của KG, đặc biệt là mức độ tuân thủ quy định pháp lý Việt Nam về nhãn thực phẩm.

---

## 3. Hypotheses (Giả thiết nghiên cứu)

### H1 — Chất lượng extraction đạt ngưỡng ứng dụng
> **Pipeline GPT-5.4 nano few-shot đạt F1 ≥ 0.80 trên tác vụ trích xuất thành phần, phụ gia và dinh dưỡng từ nhãn thực phẩm tiếng Việt.**

*Cơ sở:* Các nghiên cứu gần đây (FKG.in, FoodAtlas) cho thấy LLM với structured prompting đạt F1 > 0.80 trên tác vụ extraction thực phẩm. Nhãn thực phẩm Việt Nam có cấu trúc bán chuẩn, ít ambiguous hơn văn bản tự do.

*Liên kết:* RQ2 — đo bằng Triple F1 trên tập ground truth ([04_evaluation.md](04_evaluation.md) mục 2.1)

### H2 — Few-shot vượt trội so với baseline
> **Few-shot prompting (5–10 examples) đạt F1 cao hơn có ý nghĩa thống kê so với zero-shot prompting và rule-based baseline.**

*Cơ sở:* In-context learning với examples giúp LLM hiểu đúng format nhãn tiếng Việt (viết tắt, đơn vị không chuẩn, tên phụ gia dạng hỗn hợp Việt-Anh).

*Liên kết:* RQ3 — đo bằng ablation study 4 biến thể ([04_evaluation.md](04_evaluation.md) mục 6)

### H3 — KG đạt độ hoàn chỉnh schema cao
> **Hơn 80% product nodes trong KG được điền đủ 5 chỉ số dinh dưỡng bắt buộc theo Thông tư 29/2023/TT-BYT.**

*Cơ sở:* Từ năm 2024, quy định mới bắt buộc ghi nhãn dinh dưỡng → nguồn dữ liệu mới hơn sẽ có đủ thông tin hơn các nguồn cũ.

*Liên kết:* RQ4 — đo bằng Nutrient Fill Rate ([04_evaluation.md](04_evaluation.md) mục 3.2)

### H4 — Phụ gia được chuẩn hóa tốt qua entity linking
> **Hơn 75% additive entities trong KG được map thành công sang mã Codex Alimentarius (E-number/INS) thông qua pipeline entity linking.**

*Cơ sở:* Codex GSFA có danh sách đầy đủ ~350 phụ gia phổ biến; nhãn thực phẩm VN thường ghi kèm mã E-number hoặc tên tiêu chuẩn.

*Liên kết:* RQ2, RQ4 — đo bằng Additive Coverage ([04_evaluation.md](04_evaluation.md) mục 3.3)

---

## 4. Đóng góp khoa học (Contributions)

| # | Đóng góp | Loại | Liên kết |
|---|---|---|---|
| C1 | **ViFoodKG Ontology** — schema đặc thù cho thực phẩm đóng gói Việt Nam, tương thích FoodOn và Codex Alimentarius, phù hợp Thông tư 29/2023/TT-BYT | Ontology | [01_ontology.md](01_ontology.md) |
| C2 | **Pipeline LLM-automated** — quy trình bán tự động xây dựng KG thực phẩm sử dụng GPT-5.4 nano với ontology-guided prompting, bao gồm entity normalization và linking | Phương pháp | [03_pipeline.md](03_pipeline.md) |
| C3 | **ViFoodKG Dataset** — đồ thị tri thức thực phẩm đóng gói Việt Nam công bố mở (Neo4j + RDF/Turtle), tập trung nhóm sản phẩm trẻ em | Tài nguyên | — |
| C4 | **Bộ ground truth** — ~100–150 sản phẩm được annotate thủ công từ ảnh bao bì thực tế (ViFoodLabel), kèm inter-annotator agreement | Dữ liệu | [06_work_plan.md](06_work_plan.md) |
| C5 | **Bộ độ đo đánh giá KG** — framework đánh giá toàn diện (correctness, completeness, consistency, coverage) cùng kết quả ablation study | Đánh giá | [04_evaluation.md](04_evaluation.md) |

---

## 5. Phạm vi & Giới hạn (Scope & Limitations)

**Trong phạm vi nghiên cứu này:**
- Xây dựng KG và đánh giá chất lượng KG
- Ba nhóm sản phẩm: bánh kẹo, sữa & sản phẩm từ sữa, thực phẩm ăn liền
- Thực phẩm đóng gói lưu thông trên thị trường Việt Nam

**Ngoài phạm vi (dành cho nghiên cứu tiếp theo):**
- Ứng dụng downstream: RAG, KG-augmented NER trên bao bì
- Thực phẩm tươi sống, thực phẩm nhà hàng
- Cập nhật KG real-time khi sản phẩm mới ra thị trường

---

## 6. Mapping RQ → Experiment → Metric

| RQ | Experiment | Metric chính | Section |
|---|---|---|---|
| RQ1 | Pipeline end-to-end trên toàn bộ dataset | Population Density, Schema Completeness | [04_evaluation.md](04_evaluation.md) §3 |
| RQ2 | Extraction quality trên ground truth | Triple F1, Entity Linking Accuracy | [04_evaluation.md](04_evaluation.md) §2 |
| RQ3 | Ablation: rule-based vs zero-shot vs few-shot | Triple F1 so sánh | [04_evaluation.md](04_evaluation.md) §6 |
| RQ4 | Constraint validation trên toàn KG | Nutrient Fill Rate, Violation Rate | [04_evaluation.md](04_evaluation.md) §3–4 |
