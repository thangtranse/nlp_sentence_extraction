# TextRank Parameter Analysis Design

## Mục tiêu

Xây dựng một bộ notebook thực nghiệm giúp xác định cấu hình TextRank phù hợp với dữ liệu DUC. Bộ notebook phải giải thích được ảnh hưởng của từng nhóm tham số, trực quan hóa kết quả và đề xuất cấu hình cuối cùng dựa trên phép đo câu trích xuất, không sử dụng ROUGE.

## Phạm vi

Bộ thực nghiệm phân tích các tham số:

- `SIMILARITY_THRESHOLD`.
- `PAGERANK_DAMPING`.
- `PAGERANK_TOLERANCE`.
- `PAGERANK_MAX_ITERATIONS`.
- `USE_MMR`.
- `MMR_LAMBDA`.

`MAX_SUMMARY_WORDS` được giữ cố định ở 100 trong các phép so sánh chính để các cấu hình có cùng ngân sách. Notebook baseline sẽ báo cáo mức sử dụng ngân sách và giới hạn Recall do reference dài hơn prediction.

Không thay đổi notebook pipeline hoặc các output hiện tại. Không dùng ROUGE. Không dùng thư viện graph, TF-IDF hoặc similarity bên ngoài; `matplotlib` chỉ được dùng để vẽ biểu đồ.

## Cấu trúc

```text
notebooks/textrank-parameter-analysis/
├── experiment_utils.py
├── 01-dataset-and-baseline.ipynb
├── 02-similarity-threshold.ipynb
├── 03-pagerank-parameters.ipynb
├── 04-mmr-parameters.ipynb
└── 05-final-configuration.ipynb
```

Output được ghi vào:

```text
data/output/textrank-parameter-analysis/
├── csv/
└── charts/
```

Tên CSV và PNG bắt đầu bằng số thứ tự notebook để có thể truy ngược nguồn tạo artifact.

## Thành phần dùng chung

`experiment_utils.py` cung cấp các đơn vị nhỏ, độc lập:

1. Parse câu DUC từ thẻ `<s>` bằng `html.parser`.
2. Chuẩn hóa và tokenize nội dung.
3. Tính TF, smooth IDF, sparse TF-IDF và chuẩn hóa L2.
4. Tính cosine similarity giữa hai sparse vector.
5. Dựng weighted undirected adjacency list, không self-loop.
6. Tính PageRank có damping, dangling redistribution, tolerance và giới hạn vòng lặp.
7. Chọn câu theo PageRank hoặc MMR trong ngân sách 100 từ.
8. Khôi phục thứ tự câu nguồn.
9. Parse reference DUC_SUM.
10. Đánh giá prediction theo định danh câu `(docid, num)`.
11. Tính thống kê đồ thị, redundancy và macro metric.
12. Đọc và ghi CSV bằng standard library.

Thành phần dùng chung không tạo biểu đồ và không phụ thuộc `matplotlib`. Điều này giữ thuật toán chính có thể đọc, kiểm thử và tái sử dụng ngoài notebook.

## Định nghĩa câu đúng

Một câu prediction được tính là đúng khi cặp sau xuất hiện trong reference cùng topic:

```text
(docid, num)
```

Nội dung câu không tham gia khóa đối chiếu. `docid` được giữ dạng chuỗi và `num` được chuyển sang số nguyên ngay khi parse.

Nếu một reference chứa trùng khóa, khóa chỉ được tính một lần. Nếu prediction chứa trùng khóa, chỉ lần xuất hiện đầu tiên được tính là prediction duy nhất để tránh tăng sai cả tử số và mẫu số.

## Metric

Với mỗi topic:

```text
true_positive = |prediction_keys ∩ reference_keys|
precision = true_positive / |prediction_keys|
recall = true_positive / |reference_keys|
f1 = 2 × precision × recall / (precision + recall)
```

Khi mẫu số bằng 0, metric tương ứng bằng 0 và topic được gắn cờ để có thể kiểm tra dữ liệu.

Metric chính để xếp hạng cấu hình là macro Precision: tính Precision riêng cho từng topic hợp lệ rồi lấy trung bình, để topic lớn không lấn át topic nhỏ. Macro F1 là tiêu chí phá hòa đầu tiên.

Các metric phụ:

- Macro Recall.
- Hit@K.
- Số câu được chọn.
- Số từ summary và tỷ lệ sử dụng word budget.
- Pairwise redundancy trung bình và lớn nhất giữa các câu đã chọn.
- Thời gian chạy trung bình mỗi topic.
- Số vòng PageRank.
- Edge density.
- Isolated-node ratio.
- Average degree.
- Số connected components.

## Phân chia dữ liệu

- Tuning: 50 topic trong `data/DUC_TEXT/train`, ghép với `data/DUC_SUM/<topic>`.
- Final evaluation: 9 topic trong `data/DUC_TEXT/test`, ghép với `data/DUC_SUM/<topic>`.

Mọi lựa chọn tham số chỉ dựa trên train. Notebook cuối khóa cấu hình trước khi chạy test và không dùng test để điều chỉnh lại cấu hình.

Thiếu input hoặc reference là lỗi rõ ràng, không tự động bỏ qua. Reference parse được nhưng không có câu hợp lệ được báo cáo riêng và không được âm thầm đưa vào macro average.

## Notebook 01: Dataset and Baseline

Notebook kiểm tra:

- Số topic train/test và khả năng ghép reference.
- Phân phối số câu, số từ input và số câu reference.
- Baseline với cấu hình hiện tại: threshold `0.10`, damping `0.85`, tolerance `1e-8`, tối đa 1000 vòng, MMR bật và lambda `0.70`.
- Precision, Recall, F1, word-budget utilization và graph statistics của baseline.
- Recall ceiling thực nghiệm dưới ngân sách 100 từ: chọn tối đa các câu reference ngắn nhất có thể nằm trong ngân sách. Đây là upper bound về số câu, không phải upper bound về chất lượng ngữ nghĩa.

Artifacts:

- `csv/01-dataset-summary.csv`.
- `csv/01-baseline-topic-metrics.csv`.
- `charts/01-reference-sentence-distribution.png`.
- `charts/01-baseline-metrics.png`.

## Notebook 02: Similarity Threshold

Quét các giá trị ban đầu:

```python
[0.00, 0.02, 0.05, 0.08, 0.10, 0.12, 0.15, 0.20, 0.25, 0.30]
```

Các tham số còn lại giữ ở baseline. Notebook vẽ:

- Macro Precision, Recall và F1 theo threshold.
- Density, isolated ratio, average degree và components theo threshold.
- Precision đối chiếu với isolated ratio để nhận diện điểm đánh đổi.
- Phân phối cosine similarity bằng histogram và các percentile P50, P75, P90, P95.

Notebook ghi bảng đầy đủ thay vì chỉ giữ điểm tốt nhất. Vùng threshold cho bước cuối gồm tối đa ba giá trị có Precision cao nhất; tie-break bằng F1 rồi threshold thấp hơn để tránh phân mảnh không cần thiết.

Artifacts:

- `csv/02-threshold-summary.csv`.
- `csv/02-threshold-topic-metrics.csv`.
- `charts/02-similarity-distribution.png`.
- `charts/02-threshold-quality.png`.
- `charts/02-threshold-graph-health.png`.

## Notebook 03: PageRank Parameters

Giữ threshold tốt nhất từ notebook 02 và thử:

```python
damping = [0.70, 0.80, 0.85, 0.90, 0.95]
tolerance = [1e-4, 1e-6, 1e-8]
max_iterations = [100, 300, 1000]
```

Notebook báo cáo chất lượng, thời gian và số vòng hội tụ. Một cấu hình không hội tụ được giữ trong CSV với trạng thái `not_converged`, không làm dừng toàn bộ phép thử.

Tolerance và max iterations không được chọn chỉ vì Precision nhỉnh hơn do sai số hội tụ. Trong nhóm có cùng thứ hạng câu và metric, ưu tiên cấu hình chạy ít vòng hơn nhưng phải hội tụ trên mọi topic train.

Artifacts:

- `csv/03-pagerank-summary.csv`.
- `csv/03-pagerank-topic-metrics.csv`.
- `charts/03-pagerank-quality.png`.
- `charts/03-pagerank-convergence.png`.

## Notebook 04: MMR Parameters

Giữ threshold và PageRank tốt nhất từ các bước trước, sau đó thử:

```python
use_mmr = [False, True]
mmr_lambda = [0.30, 0.50, 0.70, 0.90, 1.00]
```

Khi `USE_MMR=False`, lambda được ghi là rỗng và chỉ chạy một cấu hình thay vì lặp năm lần tương đương. Notebook so sánh Precision/F1 với redundancy trung bình và lớn nhất.

Artifacts:

- `csv/04-mmr-summary.csv`.
- `csv/04-mmr-topic-metrics.csv`.
- `charts/04-mmr-quality.png`.
- `charts/04-mmr-redundancy.png`.

## Notebook 05: Final Configuration

Notebook đọc CSV của ba bước trước, lấy vùng ứng viên và chạy local grid search:

- Tối đa ba threshold tốt nhất.
- Tối đa hai cấu hình PageRank tốt nhất đã hội tụ trên mọi topic.
- `USE_MMR=False` và tối đa ba lambda tốt nhất khi MMR bật.

Cấu hình train được xếp hạng theo thứ tự:

1. Macro Precision giảm dần.
2. Macro F1 giảm dần.
3. Mean redundancy tăng dần.
4. Mean runtime tăng dần.
5. Thứ tự cấu hình ổn định theo giá trị tham số.

Sau khi chọn đúng một cấu hình từ train, notebook chạy cấu hình đó trên test một lần và báo cáo train/test cạnh nhau. Kết luận nêu rõ cấu hình được chọn, metric, chênh lệch train/test và giới hạn của exact sentence match.

Artifacts:

- `csv/05-local-grid-summary.csv`.
- `csv/05-final-train-topic-metrics.csv`.
- `csv/05-final-test-topic-metrics.csv`.
- `charts/05-top-configurations.png`.
- `charts/05-train-vs-test.png`.
- `05-recommended-config.json`.

## Biểu đồ

Mọi biểu đồ dùng `matplotlib`, có:

- Tiêu đề mô tả phép thử.
- Nhãn trục và đơn vị.
- Legend khi có nhiều series.
- Grid nhẹ để đọc giá trị.
- Marker tại từng cấu hình thực sự đã chạy.
- Annotation cho cấu hình được chọn.
- Kích thước đủ đọc trong notebook và file PNG.

Không dùng trục bị cắt theo cách phóng đại khác biệt nhỏ. Metric tỷ lệ dùng cùng miền `0–1` khi so sánh trực tiếp.

## Tính tái lập

- Duyệt topic theo tên file đã sort.
- Tie-break luôn được định nghĩa rõ.
- Không dùng random sampling.
- CSV chứa đầy đủ tham số, số topic hợp lệ và trạng thái hội tụ.
- Notebook chạy từ project root hoặc từ chính thư mục notebook.
- Mỗi notebook có phần Goal, Setup, Steps, Checks và Takeaways.

## Kiểm thử và xác minh

Kiểm thử tập trung vào `experiment_utils.py`:

- Parse DUC và chuyển `num` thành số nguyên.
- TF, smooth IDF, L2 normalization và cosine trên ví dụ tính tay.
- Đồ thị đối xứng, không self-loop và đúng threshold.
- PageRank bảo toàn tổng điểm, xử lý dangling node và báo không hội tụ.
- Chọn câu không vượt word budget và khôi phục thứ tự nguồn.
- Exact key Precision, Recall và F1.
- Graph statistics và redundancy.
- Train/test topic mapping.

Xác minh cuối:

1. Chạy unit tests.
2. Thực thi năm notebook theo thứ tự từ đầu đến cuối.
3. Kiểm tra CSV/PNG/JSON dự kiến tồn tại và không rỗng.
4. Kiểm tra notebook cuối chỉ dùng train để chọn cấu hình.
5. Đối chiếu cấu hình trong JSON với dòng đứng đầu local-grid CSV.

## Giới hạn diễn giải

Exact sentence match đánh giá khả năng chọn đúng câu được DUC_SUM chọn, không đánh giá paraphrase hoặc tương đồng ngữ nghĩa. Precision được ưu tiên vì prediction bị giới hạn 100 từ trong khi reference dài hơn đáng kể. F1, Recall, redundancy và graph health vẫn phải được báo cáo để tránh tối ưu một chiều.
