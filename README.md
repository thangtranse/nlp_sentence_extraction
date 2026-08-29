# Tóm tắt thực nghiệm TextRank

Đề tài thực hiện tóm tắt văn bản trích xuất trên dữ liệu DUC theo chuỗi xử lý:

```text
chủ đề → tách câu → TF-IDF + L2 → cosine similarity
       → đồ thị câu → PageRank → Top-K hoặc MMR
       → giới hạn 100 từ → khôi phục thứ tự nguồn
```

## Kết quả chính

### 1. Kiểm chứng TF-IDF viết tay

Ba câu kiểm soát:

```python
sentences = [
    {"content": "cat dog dog", "token": ["cat", "dog", "dog"]},
    {"content": "cat fish", "token": ["cat", "fish"]},
    {"content": "dog bird", "token": ["dog", "bird"]},
]
```

TF-IDF viết tay sử dụng TF dạng số đếm, smooth IDF và chuẩn hóa L2. Kết quả trùng với `TfidfVectorizer` trên toàn bộ trọng số đã kiểm tra; sai khác tuyệt đối lớn nhất bằng `0.0`.

| Câu | Vector TF-IDF sau L2            |
| --- | ------------------------------- |
| S1  | `cat=0.447214`, `dog=0.894427`  |
| S2  | `cat=0.605349`, `fish=0.795961` |
| S3  | `dog=0.605349`, `bird=0.795961` |

### 2. Cơ sở lựa chọn TOP K

K chỉ được suy ra từ tập huấn luyện để tránh rò rỉ thông tin từ tập kiểm tra.

| Thống kê                                 | Giá trị |
| ---------------------------------------- | ------: |
| Chủ đề huấn luyện                        |      50 |
| Tham chiếu có nội dung                   |      34 |
| Tham chiếu rỗng                          |      16 |
| Tổng số câu tham chiếu hợp lệ            |     518 |
| Trung bình số câu trên tham chiếu hợp lệ |  15.235 |
| Trung vị                                 |      15 |
| Khoảng nhỏ nhất–lớn nhất                 |   10–20 |
| **TOP K được chọn**                      |  **15** |

Trong nhánh PageRank + Top-K=15, ngưỡng `0.0125` đạt kết quả tốt nhất trong lưới mịn:

| Macro Precision | Macro Recall | Macro F1 | Chủ đề F1=0 |
| --------------: | -----------: | -------: | ----------: |
|          0.1598 |       0.1662 |   0.1607 |        4/34 |

Kết quả này chỉ áp dụng cho nhánh lấy cố định 15 câu PageRank cao nhất.

### 3. Lựa chọn `SIMILARITY_THRESHOLD`

Ngưỡng tương đồng quyết định một cặp câu có tạo thành cạnh trong đồ thị hay không:

```text
tạo cạnh (i, j) khi cosine(i, j) >= SIMILARITY_THRESHOLD
```

Ngưỡng quá thấp giữ nhiều cạnh yếu và làm đồ thị quá dày. Ngưỡng quá cao làm tăng đỉnh cô lập và chia đồ thị thành nhiều thành phần nhỏ. Thực nghiệm quét 13 giá trị từ `0.0` đến `0.03`, bước `0.0025`, trong khi giữ cố định các tham số khác.

Với quy trình cuối dùng PageRank + MMR + giới hạn 100 từ, `0.0275` đạt Macro F1 cao nhất trên tập huấn luyện:

|  Threshold |  Precision |     Recall |         F1 |   F1=0 | Mean density | Mean degree |
| ---------: | ---------: | ---------: | ---------: | -----: | -----------: | ----------: |
|     0.0200 |     0.1580 |     0.0574 |     0.0830 |     12 |       0.1790 |       52.47 |
|     0.0225 |     0.1614 |     0.0590 |     0.0849 |     12 |       0.1704 |       49.95 |
| **0.0275** | **0.1695** | **0.0634** | **0.0905** | **10** |   **0.1546** |   **45.27** |
|     0.0300 |     0.1592 |     0.0577 |     0.0828 |     13 |       0.1470 |       43.04 |

Vì vậy cấu hình hiện tại chọn `SIMILARITY_THRESHOLD = 0.0275`. Đây là giá trị tốt nhất trong lưới và theo metric đã thử, không phải ngưỡng tối ưu phổ quát.

### 4. Kết quả cấu hình cuối

Cấu hình đánh giá:

```text
similarity threshold = 0.0275
PageRank damping     = 0.85
tolerance            = 1e-8
MMR lambda           = 0.70
word budget          = 100
```

| Chỉ số              |  Train |   Test |
| ------------------- | -----: | -----: |
| Chủ đề hợp lệ       |     34 |      9 |
| Macro Precision     | 0.1695 | 0.1233 |
| Macro Recall        | 0.0634 | 0.0591 |
| Macro F1            | 0.0905 | 0.0769 |
| Chủ đề F1=0         |     10 |      3 |
| Số từ trung bình    |  99.85 |  99.89 |
| Mean density        | 0.1546 | 0.1599 |
| Mean isolated ratio | 0.0190 | 0.0138 |
| Mean degree         |  45.27 |  47.13 |

Tập test chỉ có 9 chủ đề, do đó chênh lệch train–test chỉ nên được xem là bằng chứng mô tả. Exact sentence match cũng không đo được paraphrase, tương đương ngữ nghĩa hoặc tính mạch lạc của toàn bản tóm tắt.

## Tài liệu và dữ liệu kết quả

- [Báo cáo DOCX](artifacts/bao-cao-tom-tat-van-ban-textrank-hutech.docx)
- [Giải thích tham số TextRank](docs/textrank-parameters.md)
- [Kết quả quét ngưỡng mịn](data/output/fine-threshold-sweep/csv)
- [Kết quả đánh giá theo K](data/output/duc-textrank-evaluation.csv)

## Chạy kiểm thử

```bash
uv run pytest -q
```
