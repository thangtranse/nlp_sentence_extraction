# Trọng số câu trong Personalized PageRank

## 1. Mục đích

File `src/nlp_practice/weights.py` được tạo để bổ sung **trọng số ưu tiên cho từng câu** trước khi chạy PageRank. Thành phần này không thay thế trọng số cạnh cosine đã có trong TextRank, mà bổ sung thông tin về mức độ quan trọng ban đầu của từng đỉnh câu.

Hai loại trọng số có vai trò khác nhau:

- **Trọng số cạnh** biểu diễn hai câu liên quan với nhau mạnh đến đâu.
- **Trọng số câu** biểu diễn bản thân một câu đáng được ưu tiên ban đầu đến mức nào.

Phần cài đặt nằm trong commit `0767524` trên branch `codex/weighted-personalized-textrank`.

## 2. Luồng xử lý

### 2.1. TextRank trước khi cải tiến

```text
Câu
  ↓
Tiền xử lý và tách từ
  ↓
Vector TF-IDF
  ↓
Cosine similarity
  ↓
Đồ thị câu có trọng số
  ↓
PageRank
  ↓
Chọn Top-K câu
```

Mỗi câu là một đỉnh. Trọng số cạnh giữa câu $i$ và câu $j$ là độ tương đồng cosine giữa hai vector TF-IDF:

$$
w_{ij}=\cos\left(\vec{s_i},\vec{s_j}\right)
$$

Trong đó:

- $\vec{s_i}$ là vector TF-IDF của câu $i$.
- $\vec{s_j}$ là vector TF-IDF của câu $j$.
- $w_{ij}$ là trọng số cạnh nối hai câu.

PageRank thông thường được tính bằng:

$$
PR(i)
=
\frac{1-d}{N}
+
d\sum_{j\in In(i)}
PR(j)
\frac{w_{ji}}{\sum_{k\in Out(j)}w_{jk}}
$$

Trong đó:

- $N$ là tổng số câu.
- $d$ là damping factor, mặc định bằng $0.85$.
- $In(i)$ là tập các câu có cạnh đi đến câu $i$.
- $Out(j)$ là tập các câu được nối với câu $j$.

Mọi câu nhận cùng một xác suất cơ sở:

$$
\frac{1-d}{N}
$$

Ví dụ, nếu có 100 câu và $d=0.85$:

$$
\frac{1-0.85}{100}=0.0015
$$

Như vậy, PageRank thông thường xem tất cả câu có mức ưu tiên ban đầu giống nhau, bất kể vị trí, nội dung hoặc độ dài của câu.

### 2.2. Personalized PageRank sau khi cải tiến

`weights.py` tính một xác suất ưu tiên riêng $P_i$ cho từng câu. Công thức PageRank trở thành:

$$
PR(i)
=
(1-d)P_i
+
d\sum_{j\in In(i)}
PR(j)
\frac{w_{ji}}{\sum_{k\in Out(j)}w_{jk}}
$$

Thành phần xác suất cơ sở thay đổi từ:

$$
\frac{1-d}{N}
\quad\longrightarrow\quad
(1-d)P_i
$$

Câu gần chủ đề chung, xuất hiện sớm và có độ dài hợp lý sẽ nhận xác suất ưu tiên lớn hơn.

Luồng xử lý cải tiến:

```text
Vector TF-IDF của các câu
  ├── Điểm centroid
  ├── Điểm vị trí
  └── Điểm độ dài
          ↓
Kết hợp trọng số
          ↓
Chuẩn hóa thành xác suất ưu tiên Pᵢ
          ↓
Personalized PageRank
          ↓
Chọn các câu có PageRank cao
```

## 3. Các hàm trong `weights.py`

File gồm bốn hàm chính:

```python
build_centroid(...)
calculate_position_scores(...)
calculate_length_score(...)
calculate_sentence_priorities(...)
```

| Hàm                             | Trách nhiệm                                                         |
| ------------------------------- | ------------------------------------------------------------------- |
| `build_centroid`                | Tính vector trung tâm của toàn bộ topic.                            |
| `calculate_position_scores`     | Tính điểm vị trí của từng câu trong từng tài liệu nguồn.            |
| `calculate_length_score`        | Tính điểm dựa trên khoảng cách giữa độ dài câu và độ dài mong muốn. |
| `calculate_sentence_priorities` | Kết hợp ba đặc trưng và chuẩn hóa thành phân phối xác suất.         |

## 4. Điểm centroid

### 4.1. Mục đích

Centroid đại diện cho nội dung chung của toàn bộ topic. Một câu có vector TF-IDF gần centroid thường chứa các từ khóa xuất hiện xuyên suốt topic, vì vậy có khả năng trình bày chủ đề trung tâm thay vì một chi tiết phụ.

### 4.2. Cách tính centroid

Giả sử có $N$ câu với các vector TF-IDF:

$$
\vec{s_1},\vec{s_2},\ldots,\vec{s_N}
$$

Vector centroid được tính bằng trung bình cộng:

$$
\vec{c}
=
\frac{1}{N}
\sum_{i=1}^{N}\vec{s_i}
$$

Điểm centroid của câu $i$ là cosine similarity giữa vector câu và centroid:

$$
C_i
=
\cos\left(\vec{s_i},\vec{c}\right)
$$

Vì các vector TF-IDF trong bài có giá trị không âm nên thông thường:

$$
0\le C_i\le 1
$$

Điểm càng gần 1 nghĩa là câu càng gần nội dung trung tâm của topic.

### 4.3. Ví dụ

Giả sử vocabulary gồm ba từ:

```text
earthquake, iran, football
```

Ba câu có vector:

$$
\vec{s_1}=(0.8,0.6,0.0)
$$

$$
\vec{s_2}=(0.7,0.7,0.0)
$$

$$
\vec{s_3}=(0.0,0.1,0.9)
$$

Centroid là:

$$
\vec{c}
=
\left(
\frac{0.8+0.7+0.0}{3},
\frac{0.6+0.7+0.1}{3},
\frac{0.0+0.0+0.9}{3}
\right)
$$

$$
\vec{c}=(0.5,0.4667,0.3)
$$

Hai câu đầu gần centroid hơn vì chứa các từ về động đất và Iran. Câu thứ ba có thành phần `football` lớn nên ít đại diện cho chủ đề chung hơn.

## 5. Điểm vị trí

### 5.1. Mục đích

Trong tin tức, những câu đầu bài thường chứa sự kiện, nhân vật, địa điểm, thời gian hoặc kết quả quan trọng. Vì vậy, câu xuất hiện sớm thường có giá trị tóm tắt cao hơn.

### 5.2. Công thức

Điểm vị trí của câu $i$:

$$
P_i^{(position)}
=
\frac{1}{1+pos(i)}
$$

Trong đó $pos(i)$ bắt đầu từ 0 và được tính riêng trong từng `docid`.

| Vị trí trong tài liệu | Phép tính |   Điểm |
| --------------------: | --------: | -----: |
|                 Câu 1 | $1/(1+0)$ | 1.0000 |
|                 Câu 2 | $1/(1+1)$ | 0.5000 |
|                 Câu 3 | $1/(1+2)$ | 0.3333 |
|                 Câu 4 | $1/(1+3)$ | 0.2500 |
|                 Câu 5 | $1/(1+4)$ | 0.2000 |
|                Câu 10 | $1/(1+9)$ | 0.1000 |

### 5.3. Tính riêng theo tài liệu

Một topic DUC có thể chứa nhiều tài liệu. Ví dụ:

```text
doc-a: câu 1 → 1.0000
doc-a: câu 2 → 0.5000
doc-a: câu 3 → 0.3333
doc-b: câu 1 → 1.0000
doc-b: câu 2 → 0.5000
```

Nhờ đặt lại vị trí theo `docid`, câu đầu của tài liệu thứ hai không bị xem như câu thứ tư của toàn topic.

## 6. Điểm độ dài

### 6.1. Mục đích

Câu quá ngắn có thể thiếu ngữ cảnh hoặc chỉ là phần tiếp nối của câu trước. Câu quá dài có thể chứa nhiều mệnh đề, khó đọc và chiếm nhiều ngân sách tóm tắt. Vì vậy, thuật toán ưu tiên câu có độ dài gần một giá trị mong muốn.

### 6.2. Công thức

Với $words_i$ là số từ của câu và $preferred$ là độ dài mong muốn:

$$
L_i
=
\frac{
\min(words_i,preferred)
}{
\max(words_i,preferred)
}
$$

Với cấu hình mặc định:

$$
preferred=20
$$

| Số từ | Công thức | Điểm độ dài |
| ----: | --------: | ----------: |
|     5 |    $5/20$ |        0.25 |
|    10 |   $10/20$ |        0.50 |
|    15 |   $15/20$ |        0.75 |
|    20 |   $20/20$ |        1.00 |
|    25 |   $20/25$ |        0.80 |
|    30 |   $20/30$ |        0.67 |
|    40 |   $20/40$ |        0.50 |
|    80 |   $20/80$ |        0.25 |

Công thức đối xứng theo tỷ lệ: câu 10 từ bằng một nửa độ dài mong muốn và câu 40 từ dài gấp đôi đều nhận điểm 0.5.

Code ưu tiên lấy số từ từ thuộc tính `wdcount` của thẻ `<s>`. Nếu `wdcount` không tồn tại hoặc không dương, chương trình đếm từ trong `content`. Câu rỗng nhận điểm 0.

`PREFERRED_SENTENCE_WORDS` không phải giới hạn số từ của bản tóm tắt và cũng không loại bỏ câu. Nó chỉ xác định độ dài nhận điểm tối đa.

## 7. Kết hợp ba đặc trưng

Cấu hình mặc định:

```ini
CENTROID_WEIGHT = 0.55
POSITION_WEIGHT = 0.30
LENGTH_WEIGHT = 0.15
PREFERRED_SENTENCE_WORDS = 20
```

Tổng ba trọng số:

$$
0.55+0.30+0.15=1.00
$$

Điểm thô của câu $i$:

$$
Raw_i
=
\frac{
\alpha C_i
+
\beta P_i^{(position)}
+
\gamma L_i
}{
\alpha+\beta+\gamma
}
$$

Với cấu hình mặc định:

$$
Raw_i
=
0.55C_i
+
0.30P_i^{(position)}
+
0.15L_i
$$

Trong đó:

- $C_i$ là điểm centroid.
- $P_i^{(position)}$ là điểm vị trí.
- $L_i$ là điểm độ dài.

Việc chia cho tổng trọng số cho phép sử dụng cả hai cách cấu hình sau mà không đổi kết quả:

```ini
CENTROID_WEIGHT = 0.55
POSITION_WEIGHT = 0.30
LENGTH_WEIGHT = 0.15
```

hoặc:

```ini
CENTROID_WEIGHT = 55
POSITION_WEIGHT = 30
LENGTH_WEIGHT = 15
```

### 7.1. Ví dụ tính điểm thô

Giả sử câu $i$ có:

```text
Centroid score = 0.80
Position score = 0.50
Length score   = 0.75
```

Khi đó:

$$
Raw_i
=
0.55(0.80)
+
0.30(0.50)
+
0.15(0.75)
$$

$$
Raw_i=0.44+0.15+0.1125=0.7025
$$

Một câu khác có:

```text
Centroid score = 0.60
Position score = 1.00
Length score   = 1.00
```

Điểm thô:

$$
Raw_j
=
0.55(0.60)
+
0.30(1.00)
+
0.15(1.00)
$$

$$
Raw_j=0.33+0.30+0.15=0.78
$$

Mặc dù câu thứ hai có điểm centroid thấp hơn, vị trí đầu tài liệu và độ dài phù hợp giúp nó có điểm tổng cao hơn.

## 8. Chuẩn hóa thành phân phối xác suất

Các điểm `Raw` chưa phải là xác suất vì tổng của chúng chưa chắc bằng 1. Xác suất ưu tiên của câu $i$ được tính bằng:

$$
Priority_i
=
\frac{Raw_i}{\sum_{j=1}^{N}Raw_j}
$$

Giả sử ba câu có điểm:

```text
Câu 0: 0.70
Câu 1: 0.50
Câu 2: 0.30
```

Tổng điểm:

$$
Total=0.70+0.50+0.30=1.50
$$

Phân phối xác suất:

$$
Priority_0=\frac{0.70}{1.50}=0.4667
$$

$$
Priority_1=\frac{0.50}{1.50}=0.3333
$$

$$
Priority_2=\frac{0.30}{1.50}=0.2000
$$

Do đó:

$$
\sum_{i=1}^{N}Priority_i=1
$$

Dictionary được truyền vào PageRank có dạng:

```python
{
    0: 0.4667,
    1: 0.3333,
    2: 0.2000,
}
```

## 9. Tác động vào PageRank

Với `PAGERANK_DAMPING = 0.85`, ta có:

$$
1-d=0.15
$$

Trong mỗi vòng lặp, 15% điểm cơ sở được phân phối theo xác suất ưu tiên, còn 85% được lan truyền qua các cạnh của đồ thị.

Ví dụ:

```text
Priority câu A = 0.40
Priority câu B = 0.10
```

Thành phần teleport:

$$
Teleport(A)=0.15\times 0.40=0.06
$$

$$
Teleport(B)=0.15\times 0.10=0.015
$$

Câu A nhận điểm cơ sở gấp bốn lần câu B. Tuy nhiên, đây chưa phải điểm cuối cùng. Câu B vẫn có thể đạt PageRank cao nếu nhận được nhiều liên kết mạnh từ các câu quan trọng.

Có thể hiểu kết quả như sau:

$$
\text{Độ quan trọng của câu}
=
\text{ưu tiên nội tại}
+
\text{uy tín nhận từ đồ thị}
$$

### 9.1. Xử lý dangling node

Dangling node là câu không có cạnh nối với câu khác. Personalized PageRank phân phối lại tổng điểm dangling theo xác suất ưu tiên:

$$
d\times DanglingMass\times Priority_i
$$

Khi không thể di chuyển theo cạnh, thuật toán quay lại phân phối ưu tiên đã xác định thay vì chia đều cho mọi câu.

## 10. Giải thích các tham số

### 10.1. `CENTROID_WEIGHT = 0.55`

Tham số này kiểm soát ảnh hưởng của mức độ gần chủ đề trung tâm.

Nên tăng khi:

- Muốn ưu tiên câu đại diện cho nội dung chung.
- Topic gồm nhiều tài liệu cùng nói về một sự kiện.
- Muốn giảm ảnh hưởng của vị trí câu.

Nên giảm khi:

- Centroid bị chi phối bởi những từ phổ biến nhưng ít giá trị.
- Topic chứa nhiều khía cạnh khác nhau.
- Câu tham chiếu thường ưu tiên thông tin mở đầu.

Nếu đặt quá cao, các câu lặp lại nội dung phổ biến có thể được ưu tiên quá mạnh, làm bản tóm tắt trùng ý.

### 10.2. `POSITION_WEIGHT = 0.30`

Tham số này kiểm soát ảnh hưởng của vị trí câu trong từng tài liệu.

Nên tăng khi:

- Dữ liệu chủ yếu là tin tức.
- Câu đầu thường là lead chứa sự kiện chính.
- Câu tham chiếu thường được lấy từ phần đầu tài liệu.

Nên giảm khi:

- Tài liệu không có cấu trúc tin tức.
- Thông tin quan trọng thường nằm giữa hoặc cuối bài.
- Nhiều tài liệu có câu mở đầu chung chung.

Nếu đặt quá cao, thuật toán có thể chọn câu đầu của mọi tài liệu dù chúng không gần chủ đề.

### 10.3. `LENGTH_WEIGHT = 0.15`

Tham số này kiểm soát ảnh hưởng của độ dài câu.

Nên tăng khi:

- Kết quả hiện tại chọn nhiều câu quá ngắn.
- Dữ liệu có nhiều câu bị tách thành các mảnh nhỏ.
- Muốn ưu tiên câu có nội dung tương đối đầy đủ.

Nên giảm khi:

- Độ dài không liên quan rõ ràng đến chất lượng câu.
- Câu tham chiếu có độ dài rất đa dạng.
- Muốn centroid và vị trí quyết định phần lớn điểm ưu tiên.

Không nên đặt trọng số độ dài quá cao vì độ dài không trực tiếp phản ánh mức độ quan trọng của nội dung.

### 10.4. `PREFERRED_SENTENCE_WORDS = 20`

Đây là số từ mà tại đó câu nhận điểm độ dài tối đa.

Nên tăng lên 25–30 khi:

- Câu trong dữ liệu thường dài.
- Câu tham chiếu chứa nhiều thông tin chi tiết.
- Thuật toán đang ưu tiên câu quá ngắn.

Nên giảm xuống 15–18 khi:

- Muốn câu tóm tắt ngắn gọn hơn.
- Ngân sách tóm tắt thấp.
- Câu dài thường chứa nhiều thông tin phụ.

Tham số này không phải số từ tối đa của câu hoặc của bản tóm tắt.

## 11. Lý do chọn cấu hình mặc định

Cấu hình tuân theo thứ tự ưu tiên:

$$
CENTROID > POSITION > LENGTH
$$

Tương ứng:

```text
55% nội dung trung tâm
30% vị trí câu
15% độ dài câu
```

Centroid quan trọng nhất vì bản tóm tắt cần đại diện cho chủ đề. Vị trí đứng thứ hai vì dữ liệu DUC chủ yếu là tin tức. Độ dài đứng cuối vì chỉ là dấu hiệu hỗ trợ.

Đây là **cấu hình khởi đầu dựa trên giả thuyết**, không phải bộ trọng số tối ưu đã được học từ dữ liệu. Hiệu quả cần được kiểm chứng bằng Precision, Recall và F1.

## 12. Bật và tắt phương pháp

### Personalized PageRank

```python
USE_PERSONALIZED_PAGERANK = True
```

Luồng xử lý:

```text
TF-IDF
  → centroid, position, length
  → sentence priorities
  → Personalized PageRank
```

### PageRank đối chứng

```python
USE_PERSONALIZED_PAGERANK = False
```

Khi `personalization=None`, PageRank sử dụng phân phối đều:

$$
P_i=\frac{1}{N}
$$

Nhờ đó có thể chạy đối chứng mà không cần thay đổi thuật toán.

## 13. Kiểm tra dữ liệu đầu vào

`weights.py` kiểm tra các trường hợp sau:

- Số câu phải bằng số vector TF-IDF.
- Trọng số không được âm.
- Phải có ít nhất một trọng số dương.
- Topic rỗng trả về dictionary rỗng.
- Nếu tổng điểm bằng 0, chương trình quay về phân phối đều $1/N$.
- `preferred_words` phải lớn hơn 0.

Các điều kiện này giữ cho personalization vector là một phân phối xác suất hợp lệ.

## 14. Cấu hình thực nghiệm đề xuất

Nên thay đổi một nhóm tham số tại một thời điểm và giữ nguyên `SIMILARITY_THRESHOLD`, `PAGERANK_DAMPING`, `TOP_K` cùng cách đánh giá.

| Cấu hình | Centroid | Position | Length | Preferred words | Mục tiêu              |
| -------- | -------: | -------: | -----: | --------------: | --------------------- |
| Baseline |        – |        – |      – |               – | PageRank thông thường |
| A        |     0.55 |     0.30 |   0.15 |              20 | Cấu hình mặc định     |
| B        |     0.70 |     0.20 |   0.10 |              20 | Tăng ưu tiên chủ đề   |
| C        |     0.45 |     0.40 |   0.15 |              20 | Tăng ưu tiên vị trí   |
| D        |     0.50 |     0.25 |   0.25 |              20 | Tăng ảnh hưởng độ dài |
| E        |     0.55 |     0.30 |   0.15 |              15 | Ưu tiên câu ngắn hơn  |
| F        |     0.55 |     0.30 |   0.15 |              25 | Ưu tiên câu dài hơn   |

Lệnh chạy cho từng cấu hình:

```bash
uv run nlp
uv run evaluate
```

Kết quả nên được lưu riêng để tránh lần chạy sau ghi đè:

```bash
cp data/output/evaluation/evaluation-results.csv \
  data/output/evaluation/weighted-config-a.csv
```

Các chỉ số cần so sánh:

- Precision trung bình.
- Recall trung bình.
- F1 trung bình.
- Số topic có F1 bằng 0.

## 15. Kết luận

`weights.py` biến TextRank có trọng số cạnh thành Personalized TextRank có thêm trọng số ưu tiên cho đỉnh. Mỗi câu được đánh giá dựa trên mức độ gần centroid của topic, vị trí trong tài liệu và độ dài. Các điểm này được kết hợp rồi chuẩn hóa thành personalization vector cho PageRank.

Phương pháp mới không loại bỏ cơ chế lan truyền độ quan trọng qua đồ thị. Nó kết hợp hai nguồn bằng chứng:

1. **Bằng chứng nội tại**: nội dung, vị trí và độ dài của câu.
2. **Bằng chứng quan hệ**: liên kết cosine giữa câu đó với các câu khác.

Nhờ vậy, thuật toán không còn xem mọi câu có mức ưu tiên ban đầu giống nhau nhưng vẫn giữ được đặc trưng cốt lõi của TextRank.
