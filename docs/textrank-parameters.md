# Giải thích và cách chọn tham số TextRank

Notebook [`duc-textrank-pipeline.ipynb`](../notebooks/duc-textrank-pipeline.ipynb) sử dụng các tham số sau:

```python
SIMILARITY_THRESHOLD = 0.0275
PAGERANK_DAMPING = 0.85
PAGERANK_TOLERANCE = 1e-8
PAGERANK_MAX_ITERATIONS = 1000
MAX_SUMMARY_WORDS = 100
USE_MMR = True
MMR_LAMBDA = 0.70
```

Ngưỡng `0.0275` là cấu hình được khóa sau khi package chuyển sang PageRank + MMR với ngân sách 100 từ và chạy lại sweep chi tiết ở vùng thấp trên tập train. Đây là giá trị tốt nhất theo Macro F1 trong lưới đã thử cho pipeline này, không phải một giá trị tối ưu phổ quát. Các tham số còn lại được giữ cố định để cô lập ảnh hưởng của threshold; sau khi chọn cấu hình, hệ thống mới đánh giá một lần trên tập test.

## 1. `SIMILARITY_THRESHOLD`

```python
SIMILARITY_THRESHOLD = 0.0275
```

Đây là ngưỡng quyết định hai câu có được nối bằng một cạnh trong đồ thị TextRank hay không:

```python
if cosine_similarity(sentence_i, sentence_j) >= SIMILARITY_THRESHOLD:
    graph[i][j] = similarity
```

Cosine similarity nằm trong khoảng từ `0` đến `1` đối với các vector TF-IDF không âm:

- Gần `0`: hai câu có rất ít từ quan trọng chung.
- Gần `1`: hai câu có cách biểu diễn TF-IDF rất giống nhau.

Giá trị `0.0275` không có nghĩa là hai câu giống nhau đúng 2,75% về ngữ nghĩa. Đây là độ gần nhau giữa hai vector TF-IDF, chủ yếu phản ánh mức độ tương đồng từ vựng sau tiền xử lý.

Ví dụ:

| Cặp câu | Cosine similarity | Có cạnh khi threshold = 0.0275? |
|---|---:|---|
| A–B | 0.32 | Có |
| A–C | 0.14 | Có |
| A–D | 0.03 | Không |
| B–C | 0.09 | Không |

### Khi threshold quá thấp

Ví dụ `0.01`:

- Đồ thị có rất nhiều cạnh.
- Những câu chỉ chia sẻ một vài từ cũng có thể được nối.
- Quan hệ mạnh và quan hệ nhiễu khó phân biệt.
- Điểm PageRank của các câu có thể trở nên gần bằng nhau.

### Khi threshold quá cao

Ví dụ `0.50`:

- Chỉ những câu gần như lặp lại nhau mới được nối.
- Nhiều câu trở thành nút cô lập.
- Đồ thị bị chia thành nhiều thành phần nhỏ.
- PageRank thiếu liên kết để xác định câu trung tâm.
- Dangling score được chia đều nhiều hơn, làm giảm khả năng phân biệt câu.

### Các chỉ số cần quan sát

#### Edge density

Mật độ cạnh là tỷ lệ số cạnh thực tế so với số cạnh tối đa của đồ thị vô hướng:

```text
density = 2E / (N × (N - 1))
```

Trong đó `N` là số câu và `E` là số cạnh. Density gần `1` cho thấy đồ thị rất dày. Density gần `0` chưa chắc là sai, nhưng cần kiểm tra thêm số câu cô lập.

#### Isolated-node ratio

Tỷ lệ câu không có liên kết:

```text
isolated_ratio = isolated_nodes / total_nodes
```

Có thể dùng các khoảng sau như dấu hiệu tham khảo, không phải tiêu chuẩn bắt buộc:

- Dưới 5%: đồ thị có thể hơi dày.
- Khoảng 5–20%: thường là vùng đáng thử nghiệm.
- Trên 30%: cần kiểm tra threshold có quá cao không.

#### Average degree

Số hàng xóm trung bình của một câu:

```text
average_degree = 2E / N
```

Average degree gần `N - 1` cho thấy gần như mọi câu đều nối với nhau. Giá trị gần `0` cho thấy đồ thị thiếu liên kết.

#### Connected components

Connected component là một nhóm nút có thể đi đến nhau thông qua các cạnh. Một topic có thể có nhiều component vì chứa nhiều sự kiện con. Tuy nhiên, quá nhiều component chỉ có một hoặc hai câu thường là dấu hiệu threshold quá cao.

### Cách chọn threshold

Trước tiên, xem phân phối cosine similarity của tất cả cặp câu khác nhau. Các percentile như P50, P75, P90 và P95 cho biết mức similarity của những nhóm cạnh mạnh nhất.

Sau đó chạy thử một dải giá trị:

```python
THRESHOLD_CANDIDATES = [
    0.0000, 0.0025, 0.0050, 0.0075, 0.0100,
    0.0125, 0.0150, 0.0175, 0.0200, 0.0225,
    0.0250, 0.0275, 0.0300,
]
```

Với mỗi threshold, ghi lại:

| Threshold | Density | Isolated ratio | Average degree | Components | ROUGE |
|---:|---:|---:|---:|---:|---:|
| 0.05 | … | … | … | … | … |
| 0.10 | … | … | … | … | … |
| 0.15 | … | … | … | … | … |

Các chỉ số đồ thị giúp loại bỏ cấu hình bất hợp lý. Chất lượng cuối cùng nên được đánh giá bằng ROUGE-1, ROUGE-2 và ROUGE-L khi so sánh kết quả với summary tham chiếu trong `data/DUC_SUM`.

Quy trình chọn tham số:

1. Chạy từng threshold trên tập train.
2. Giữ nguyên các tham số khác để so sánh công bằng.
3. Sinh summary với cùng giới hạn số từ.
4. Tính Macro Precision, Recall và F1 trên tất cả topic hợp lệ.
5. Đọc thủ công một số cặp câu có similarity gần ngưỡng.
6. Chọn giá trị có chất lượng và độ ổn định tốt trên nhiều topic.
7. Giữ nguyên giá trị đã chọn khi đánh giá tập test.

Không nên điều chỉnh threshold dựa trên kết quả test vì như vậy tập test đã tham gia vào quá trình tối ưu.

## 2. `PAGERANK_DAMPING`

```python
PAGERANK_DAMPING = 0.85
```

Damping, thường ký hiệu là `d`, cân bằng giữa điểm nhận từ các câu liên kết và phần điểm được phân phối đều:

```text
PR(i) = (1 - d) / N + d × linked_score(i)
```

Với `d = 0.85`:

- 85% điểm phụ thuộc vào cấu trúc liên kết giữa các câu.
- 15% điểm được phân phối đều.

Phần phân phối đều giúp thuật toán không bị mắc kẹt trong một nhóm nút và hỗ trợ hội tụ.

| Damping | Tác động thường gặp |
|---:|---|
| Thấp | Điểm các câu đồng đều hơn, ít phụ thuộc đồ thị |
| `0.85` | Giá trị PageRank phổ biến và là điểm khởi đầu tốt |
| Gần `1` | Phụ thuộc mạnh vào đồ thị và nhạy hơn với cấu trúc cạnh |

Có thể thử `0.70`, `0.80`, `0.85`, `0.90` và `0.95`. Khi so sánh, cần giữ nguyên threshold và các tham số khác.

## 3. `PAGERANK_TOLERANCE`

```python
PAGERANK_TOLERANCE = 1e-8
```

`1e-8` tương đương `0.00000001`. Sau mỗi vòng lặp, notebook tính tổng mức thay đổi của PageRank:

```python
difference = sum(
    abs(new_score[node] - old_score[node])
    for node in graph
)
```

Thuật toán dừng khi:

```text
difference < PAGERANK_TOLERANCE
```

| Tolerance | Tác động |
|---:|---|
| `1e-4` | Dừng sớm hơn, độ chính xác thấp hơn |
| `1e-6` | Thường đủ cho nhiều thử nghiệm |
| `1e-8` | Hội tụ chặt chẽ, phù hợp cấu hình hiện tại |
| `1e-12` | Rất nghiêm ngặt, có thể cần nhiều vòng lặp |

Tolerance chủ yếu ảnh hưởng thời gian và độ chính xác số học. Nếu thứ hạng câu không đổi giữa `1e-6` và `1e-8`, dùng `1e-6` có thể tiết kiệm thời gian mà không làm thay đổi summary.

## 4. `PAGERANK_MAX_ITERATIONS`

```python
PAGERANK_MAX_ITERATIONS = 1000
```

Đây là số vòng lặp tối đa được phép. Nếu sai số vẫn chưa nhỏ hơn tolerance sau 1000 vòng, notebook báo lỗi thay vì chạy vô hạn.

Thông thường PageRank hội tụ sớm hơn nhiều. Nếu thường xuyên chạm giới hạn:

1. Kiểm tra công thức cập nhật PageRank.
2. Kiểm tra dangling score có được phân phối lại không.
3. Kiểm tra tổng PageRank sau mỗi vòng có xấp xỉ `1` không.
4. Xem tolerance có nghiêm ngặt không cần thiết không.

Không nên chỉ tăng `MAX_ITERATIONS` để che giấu lỗi trong cách cài đặt.

## 5. `MAX_SUMMARY_WORDS`

```python
MAX_SUMMARY_WORDS = 100
```

Đây là số từ tối đa của summary. Notebook chỉ thêm nguyên câu khi tổng số từ sau khi thêm không vượt quá giới hạn.

Ví dụ:

```text
Đã chọn: 87 từ
Câu tiếp theo: 20 từ
Tổng dự kiến: 107 từ
Kết quả: bỏ qua câu này
```

Notebook không cắt câu giữa chừng, vì vậy summary có thể có 96 hoặc 99 từ thay vì đúng 100 từ. Khi so sánh nhiều phương pháp, phải dùng cùng một word budget để kết quả công bằng.

## 6. `USE_MMR`

```python
USE_MMR = True
```

MMR là Maximal Marginal Relevance. MMR giúp giảm việc chọn nhiều câu cùng diễn đạt một sự kiện.

- `True`: chọn câu dựa trên cả PageRank và mức độ trùng lặp.
- `False`: chỉ chọn dựa trên PageRank.

So sánh `True` và `False` là một ablation experiment hữu ích để biết MMR có thực sự cải thiện summary trên dữ liệu hiện tại hay không.

## 7. `MMR_LAMBDA`

```python
MMR_LAMBDA = 0.70
```

Lambda cân bằng giữa độ quan trọng và độ trùng lặp:

```text
MMR(i) = λ × relevance(i) - (1 - λ) × redundancy(i)
```

Trong notebook:

- `relevance(i)` là PageRank đã được chuẩn hóa.
- `redundancy(i)` là cosine similarity lớn nhất giữa câu đang xét và các câu đã chọn.

Với `λ = 0.70`:

```text
MMR(i) = 0.70 × relevance(i) - 0.30 × redundancy(i)
```

| Lambda | Hành vi |
|---:|---|
| `1.0` | Chỉ quan tâm PageRank, không phạt trùng lặp |
| `0.7` | Thiên về câu quan trọng nhưng vẫn giảm trùng lặp |
| `0.5` | Cân bằng độ quan trọng và tính đa dạng |
| `0.3` | Thiên về đa dạng, có thể bỏ qua câu quan trọng |
| `0.0` | Chỉ tránh trùng lặp, bỏ qua PageRank |

Có thể thử:

```python
MMR_LAMBDA_CANDIDATES = [0.3, 0.5, 0.7, 0.9, 1.0]
```

`1.0` gần tương đương việc không phạt redundancy, nên có thể dùng làm baseline để so sánh tác động của MMR.

## Nguyên tắc thực nghiệm chung

Khi tối ưu một tham số, giữ nguyên tất cả tham số còn lại. Nếu thay đổi nhiều tham số cùng lúc, sẽ không biết thay đổi nào tạo ra khác biệt.

Thứ tự thử nghiệm đề xuất:

1. Chọn `SIMILARITY_THRESHOLD` dựa trên thống kê đồ thị và Macro F1.
2. Kiểm tra một vài giá trị `PAGERANK_DAMPING`.
3. Giữ tolerance và max iterations ở mức bảo đảm hội tụ.
4. So sánh tắt và bật MMR.
5. Khi bật MMR, thử các giá trị `MMR_LAMBDA`.
6. Luôn giữ cùng `MAX_SUMMARY_WORDS` trong một phép so sánh.

Không nên chỉ báo cáo cấu hình tốt nhất. Nên lưu bảng kết quả của tất cả cấu hình đã thử để giải thích vì sao chọn bộ tham số cuối cùng.
