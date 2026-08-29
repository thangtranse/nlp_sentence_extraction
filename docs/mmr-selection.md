# Maximal Marginal Relevance trong lựa chọn câu tóm tắt

## 1. Mục đích tài liệu

Tài liệu này giải thích chi tiết Maximal Marginal Relevance (MMR), cách MMR được cài đặt trong `src/nlp_practice/selection.py`, ý nghĩa của các tham số và lý do MMR **không được chọn làm bước lựa chọn câu trong phiên bản cuối hiện tại**.

Điểm cần phân biệt:

- PageRank đánh giá mức độ quan trọng của từng câu dựa trên đồ thị.
- MMR không thay thế PageRank và không tính lại đồ thị.
- MMR là bước hậu xử lý dùng điểm PageRank để chọn một tập câu vừa quan trọng vừa ít trùng lặp.

Trong `src/nlp_practice/main.py`, lời gọi `select_sentences(...)` đang được comment. Luồng chạy hiện tại sử dụng `rank_sentences_by_pagerank(...)` và lấy `TOP_K` câu có PageRank cao nhất. Vì vậy, dù `USE_MMR` và `MMR_LAMBDA` đã được khai báo, MMR chưa tham gia vào kết quả tóm tắt cuối.

## 2. Vấn đề MMR muốn giải quyết

### 2.1. Hạn chế của việc lấy Top-K theo PageRank

Sau khi PageRank hội tụ, mỗi câu có một điểm quan trọng:

$$
PR(i)
$$

Cách chọn đơn giản là sắp xếp giảm dần rồi lấy $K$ câu đầu:

$$
Summary
=
TopK\left(PR(i)\right)
$$

Phương pháp này chỉ quan tâm đến độ quan trọng riêng của từng câu. Nó không kiểm tra các câu đã chọn có diễn đạt cùng một thông tin hay không.

Ví dụ:

```text
Câu A: Trận động đất tại Iran làm ít nhất 25.000 người thiệt mạng.
Câu B: Ít nhất 25.000 người đã chết trong trận động đất ở Iran.
Câu C: Nhiều ngôi nhà bằng gạch yếu đã sụp đổ trong trận động đất.
```

Nếu A và B đều có PageRank cao, Top-K có thể chọn cả hai. Bản tóm tắt lúc này sử dụng hai câu cho cùng một sự kiện và bỏ mất thông tin bổ sung từ C.

### 2.2. Mục tiêu của MMR

MMR cố gắng cân bằng hai mục tiêu:

1. **Relevance**: câu phải quan trọng đối với nội dung cần tóm tắt.
2. **Diversity**: câu không nên quá giống những câu đã được chọn.

Có thể mô tả ngắn gọn:

$$
\text{Giá trị lựa chọn}
=
\text{độ quan trọng}
-
\text{độ trùng lặp}
$$

## 3. Công thức MMR

Gọi:

- $R$ là tập câu chưa được chọn.
- $S$ là tập câu đã được chọn.
- $Rel(i)$ là điểm relevance của câu $i$.
- $Sim(i,j)$ là độ tương đồng giữa câu $i$ và câu $j$.
- $\lambda$ là tham số cân bằng relevance và redundancy.

Ở mỗi vòng lặp, MMR chọn:

$$
i^*
=
\underset{i\in R}{\arg\max}
\left[
\lambda Rel(i)
-
(1-\lambda)
\underset{j\in S}{\max}Sim(i,j)
\right]
$$

Đặt:

$$
Redundancy(i)
=
\underset{j\in S}{\max}Sim(i,j)
$$

Ta có dạng rút gọn:

$$
MMR(i)
=
\lambda Rel(i)
-
(1-\lambda)Redundancy(i)
$$

Trong code hiện tại:

```python
selection_score = (
    mmr_lambda * relevance[index]
    - (1.0 - mmr_lambda) * redundancy
)
```

## 4. Relevance được tính như thế nào?

### 4.1. Nguồn relevance

Relevance trong MMR chính là điểm PageRank của câu. Tuy nhiên, điểm PageRank thường nhỏ và phụ thuộc vào số lượng câu trong topic. Vì vậy, code chuẩn hóa PageRank về khoảng từ 0 đến 1 trước khi đưa vào MMR.

Gọi:

$$
PR_{min}=\min_j PR(j)
$$

$$
PR_{max}=\max_j PR(j)
$$

Điểm relevance chuẩn hóa:

$$
Rel(i)
=
\frac{PR(i)-PR_{min}}{PR_{max}-PR_{min}}
$$

Khi đó:

$$
0\le Rel(i)\le 1
$$

Câu có PageRank thấp nhất nhận relevance bằng 0; câu có PageRank cao nhất nhận relevance bằng 1.

### 4.2. Trường hợp mọi PageRank bằng nhau

Nếu:

$$
PR_{min}=PR_{max}
$$

phép chia trên không thực hiện được. Code xử lý bằng cách gán relevance bằng 1 cho tất cả câu:

```python
if math.isclose(low, high):
    for index in scores:
        normalized_scores[index] = 1.0
```

Khi đó, nếu MMR được bật, lựa chọn chủ yếu phụ thuộc vào độ trùng lặp và quy tắc phá hòa.

## 5. Redundancy được tính như thế nào?

### 5.1. Độ tương đồng giữa hai câu

Mỗi câu đã có vector TF-IDF. Độ tương đồng giữa câu $i$ và câu $j$ là cosine similarity:

$$
Sim(i,j)
=
\cos\left(\vec{s_i},\vec{s_j}\right)
$$

Trong đó:

- $\vec{s_i}$ là vector TF-IDF của câu $i$.
- $\vec{s_j}$ là vector TF-IDF của câu $j$.

### 5.2. So sánh với tất cả câu đã chọn

Một câu ứng viên được so sánh với từng câu trong tập $S$. Code lấy giá trị lớn nhất:

```python
redundancy = 0.0

for selected_index in selected_indices:
    similarity = similarities[index][selected_index]
    if similarity > redundancy:
        redundancy = similarity
```

Do đó:

$$
Redundancy(i)
=
\max_{j\in S}Sim(i,j)
$$

MMR sử dụng độ tương đồng lớn nhất thay vì trung bình vì chỉ cần một câu đã chọn rất giống ứng viên là đủ để xem ứng viên có nguy cơ trùng lặp.

### 5.3. Câu đầu tiên

Khi chưa chọn câu nào:

$$
S=\varnothing
$$

Code đặt:

$$
Redundancy(i)=0
$$

Vì vậy, điểm vòng đầu là:

$$
MMR(i)=\lambda Rel(i)
$$

Với mọi $\lambda>0$, câu có relevance cao nhất được chọn đầu tiên. Thông thường đó là câu có PageRank cao nhất.

## 6. Ý nghĩa của `MMR_LAMBDA`

Cấu hình hiện có:

```ini
MMR_LAMBDA = 0.70
```

Công thức trở thành:

$$
MMR(i)
=
0.70Rel(i)
-
0.30Redundancy(i)
$$

Điều đó có nghĩa:

- 70% hệ số dành cho độ quan trọng.
- 30% hệ số dành cho hình phạt trùng lặp.

### 6.1. Ảnh hưởng của lambda

| Lambda | Relevance | Phạt trùng lặp | Hành vi |
|---:|---:|---:|---|
| 0.0 | 0% | 100% | Chỉ tìm câu ít giống tập đã chọn; không phù hợp cho vòng đầu. |
| 0.3 | 30% | 70% | Ưu tiên đa dạng mạnh, có thể chọn câu ít quan trọng. |
| 0.5 | 50% | 50% | Cân bằng hai mục tiêu. |
| 0.7 | 70% | 30% | Giữ relevance là mục tiêu chính, giảm trùng lặp vừa phải. |
| 0.9 | 90% | 10% | Gần với xếp hạng PageRank, chỉ phạt nhẹ. |
| 1.0 | 100% | 0% | Không còn phạt redundancy; gần với chọn theo PageRank. |

### 6.2. Lambda không phải xác suất

$\lambda$ là hệ số cân bằng trong hàm mục tiêu, không phải xác suất một câu được chọn. Giá trị 0.70 không có nghĩa câu có 70% cơ hội được chọn.

### 6.3. Điều kiện hợp lệ

Code yêu cầu:

$$
0\le\lambda\le 1
$$

Nếu nằm ngoài khoảng này, chương trình báo lỗi:

```python
if not 0.0 <= mmr_lambda <= 1.0:
    raise ValueError("mmr_lambda must be in [0, 1]")
```

## 7. Ví dụ chọn câu từng vòng

Giả sử có ba câu với relevance:

| Câu | Relevance |
|---|---:|
| A | 1.00 |
| B | 0.90 |
| C | 0.75 |

Độ tương đồng:

| Cặp câu | Cosine similarity |
|---|---:|
| A và B | 0.95 |
| A và C | 0.10 |
| B và C | 0.08 |

Sử dụng:

$$
\lambda=0.70
$$

### 7.1. Vòng thứ nhất

Chưa có câu nào được chọn nên redundancy bằng 0:

$$
MMR(A)=0.70(1.00)-0.30(0)=0.70
$$

$$
MMR(B)=0.70(0.90)-0.30(0)=0.63
$$

$$
MMR(C)=0.70(0.75)-0.30(0)=0.525
$$

Chọn A.

### 7.2. Vòng thứ hai

Tập đã chọn:

$$
S=\{A\}
$$

Đối với B:

$$
Redundancy(B)=Sim(B,A)=0.95
$$

$$
MMR(B)=0.70(0.90)-0.30(0.95)
$$

$$
MMR(B)=0.63-0.285=0.345
$$

Đối với C:

$$
Redundancy(C)=Sim(C,A)=0.10
$$

$$
MMR(C)=0.70(0.75)-0.30(0.10)
$$

$$
MMR(C)=0.525-0.03=0.495
$$

MMR chọn C dù relevance của C thấp hơn B. Nguyên nhân là B quá giống câu A đã chọn.

Kết quả:

```text
Top-K PageRank có thể chọn: A, B
MMR có thể chọn:          A, C
```

MMR hy sinh một phần relevance để tăng độ đa dạng thông tin.

## 8. Giới hạn số từ

Hàm `select_sentences` không chọn cố định $K$ câu. Nó chọn nhiều câu nhất có thể trong ngân sách:

```ini
MAX_SUMMARY_WORDS = 100
```

Một câu chỉ được xem xét nếu còn vừa ngân sách:

$$
used\_words+sentence\_words\le max\_summary\_words
$$

Trong code:

```python
if used_words + sentence_words <= max_summary_words:
    fitting_indices.append(index)
```

Nếu không còn câu nào vừa phần ngân sách còn lại, thuật toán dừng. Câu không bị cắt giữa chừng.

Điều này khác với Top-K:

| Top-K | MMR hiện tại |
|---|---|
| Chọn cố định tối đa $K$ câu. | Chọn theo ngân sách từ. |
| Độ dài tổng có thể thay đổi nhiều. | Độ dài không vượt `MAX_SUMMARY_WORDS`. |
| Không phạt trùng lặp. | Phạt câu giống các câu đã chọn. |
| Chỉ cần PageRank. | Cần PageRank, ma trận similarity, lambda và word budget. |

## 9. Quy tắc phá hòa

Code so sánh ứng viên bằng tuple:

```python
candidate_key = (
    selection_score,
    pagerank_scores[index],
    -source_index,
)
```

Thứ tự ưu tiên:

1. MMR score cao hơn.
2. Nếu MMR score bằng nhau, PageRank cao hơn.
3. Nếu vẫn bằng nhau, câu xuất hiện sớm hơn trong nguồn.

Quy tắc này giúp kết quả xác định và có thể lặp lại.

## 10. Khôi phục thứ tự nguồn

MMR chọn câu theo thứ tự tối ưu, không phải thứ tự xuất hiện. Sau khi hoàn tất, code sắp xếp lại các câu theo `source_index`:

```python
selected_indices.sort(
    key=lambda index: sentences[index].get("source_index", index)
)
```

Việc này giúp bản tóm tắt dễ đọc và giữ mạch thời gian tốt hơn.

## 11. Độ phức tạp

Giả sử có $N$ câu và cần chọn $M$ câu. Trong mỗi vòng, thuật toán có thể:

- duyệt các câu chưa chọn;
- so sánh mỗi ứng viên với các câu đã chọn;
- kiểm tra giới hạn số từ.

Độ phức tạp gần đúng:

$$
O(NM^2)
$$

Trong trường hợp xấu khi $M$ gần $N$, độ phức tạp có thể tiến gần:

$$
O(N^3)
$$

Tuy nhiên, ma trận cosine đã được tính trước và ngân sách 100 từ thường khiến số câu được chọn nhỏ, nên chi phí thực tế thấp hơn trường hợp xấu.

## 12. Ưu điểm của MMR

### 12.1. Giảm câu trùng ý

MMR trực tiếp phạt một câu nếu nó quá giống câu đã chọn. Đây là ưu điểm lớn trong multi-document summarization, nơi nhiều bài báo có thể lặp lại cùng một sự kiện.

### 12.2. Tăng độ bao phủ

Khi tránh chọn nhiều câu về cùng một chi tiết, bản tóm tắt có cơ hội bao phủ nhiều khía cạnh hơn.

### 12.3. Kết hợp được với PageRank

MMR không yêu cầu thay đổi thuật toán PageRank. Nó sử dụng kết quả PageRank làm relevance và ma trận cosine làm redundancy.

### 12.4. Kiểm soát ngân sách

Phiên bản cài đặt trong dự án đảm bảo tổng số từ không vượt `MAX_SUMMARY_WORDS` và không cắt câu.

### 12.5. Dễ giải thích

Công thức thể hiện rõ sự đánh đổi giữa độ quan trọng và độ trùng lặp thông qua một tham số $\lambda$.

## 13. Nhược điểm và rủi ro

### 13.1. Phụ thuộc vào cosine TF-IDF

Redundancy hiện được đo bằng cosine giữa vector TF-IDF. Hai câu đồng nghĩa nhưng dùng từ khác có thể không bị xem là trùng lặp. Ngược lại, hai câu chia sẻ nhiều từ nhưng cung cấp số liệu hoặc góc nhìn khác nhau có thể bị phạt quá mạnh.

### 13.2. Tối ưu tham lam

MMR chọn câu tốt nhất ở từng vòng nhưng không tìm tập câu tối ưu toàn cục. Một lựa chọn sớm có thể làm thay đổi mạnh tất cả lựa chọn sau.

### 13.3. Nhạy với lambda

Lambda thấp có thể chọn câu đa dạng nhưng ít quan trọng. Lambda cao làm MMR gần Top-K và giảm ít trùng lặp.

### 13.4. Phụ thuộc ngân sách từ

Một câu quan trọng nhưng dài có thể không vừa phần ngân sách còn lại và bị bỏ qua. Một câu ngắn hơn nhưng kém quan trọng có thể được chọn thay thế.

### 13.5. Thay đổi hai yếu tố cùng lúc

Trong code hiện tại, chuyển từ `rank_sentences_by_pagerank` sang `select_sentences` đồng thời thay đổi:

1. Chính sách từ Top-K sang MMR.
2. Điều kiện độ dài từ số câu sang ngân sách 100 từ.
3. Thứ tự đầu ra từ thứ tự xếp hạng sang thứ tự nguồn.

Vì vậy, nếu F1 thay đổi, không thể kết luận ngay thay đổi đến riêng từ MMR.

### 13.6. Có thêm tham số cần hiệu chỉnh

Pipeline phải chọn thêm:

- `USE_MMR`.
- `MMR_LAMBDA`.
- `MAX_SUMMARY_WORDS`.

Nếu điều chỉnh các tham số này trực tiếp trên tập test, kết quả có nguy cơ bị overfit.

## 14. Vì sao phiên bản cuối hiện tại không chọn MMR?

### 14.1. Giữ phạm vi bài tập tập trung vào đồ thị và PageRank

Mục tiêu chính của bài là biểu diễn văn bản bằng đồ thị, xây dựng cạnh có trọng số và xếp hạng câu bằng PageRank hoặc Personalized PageRank. MMR là một thuật toán chọn câu sau PageRank, không phải thành phần tạo hoặc xếp hạng đồ thị.

Không bật MMR giúp kết quả cuối phản ánh trực tiếp hơn tác động của:

- TF-IDF;
- cosine similarity;
- ngưỡng cạnh;
- trọng số đỉnh;
- PageRank.

### 14.2. Cần cô lập tác động của cấu hình trọng số mới

Để so sánh PageRank thông thường và Personalized PageRank, chính sách chọn câu phải được giữ giống nhau:

$$
\text{Baseline PageRank}+TopK
$$

so với:

$$
\text{Personalized PageRank}+TopK
$$

Nếu đồng thời bật MMR, thay đổi kết quả có thể đến từ personalization, hình phạt redundancy hoặc ngân sách 100 từ. Khi đó thí nghiệm không còn cô lập được tác động của trọng số câu.

### 14.3. Top-K đơn giản và dễ truy vết hơn

Với Top-K, một câu được chọn vì nó nằm trong $K$ điểm PageRank cao nhất. Mối quan hệ giữa điểm và kết quả rõ ràng.

Với MMR, một câu PageRank cao có thể bị loại vì tương đồng với một câu được chọn trước đó. Kết quả phụ thuộc vào lịch sử lựa chọn và khó giải thích hơn trong phần bảo vệ thuật toán cơ bản.

### 14.4. MMR thay đổi cả số lượng câu lẫn ngân sách

Top-K hiện sử dụng:

```ini
TOP_K = 15
```

MMR hiện sử dụng:

```ini
MAX_SUMMARY_WORDS = 100
```

Hai đầu ra không có cùng điều kiện độ dài. So sánh trực tiếp Precision, Recall và F1 có thể không công bằng vì số câu dự đoán khác nhau ảnh hưởng trực tiếp đến các chỉ số.

### 14.5. Chưa có artifact kết quả MMR đủ để kết luận thực nghiệm

Repository có code và tài liệu thiết kế cho việc sweep MMR, nhưng trong checkout hiện tại không tìm thấy CSV kết quả MMR để truy vết đầy đủ từng cấu hình. Vì vậy không nên viết rằng MMR chắc chắn làm F1 thấp hơn hoặc cao hơn.

Quyết định không chọn MMR hiện tại là quyết định về phạm vi và thiết kế thí nghiệm, không phải kết luận rằng MMR không hiệu quả.

### 14.6. Redundancy từ TF-IDF có thể phạt thông tin xác nhận hợp lệ

Trong multi-document summarization, nhiều nguồn cùng nhắc lại một con số hoặc sự kiện có thể cho thấy thông tin đó quan trọng. MMR chỉ nhìn cosine lexical nên có thể xem sự lặp lại này là dư thừa và phạt câu, dù câu cung cấp nguồn, ngữ cảnh hoặc chi tiết bổ sung.

### 14.7. Tránh thêm lambda chưa được khóa bằng train/validation

Giá trị `0.70` là một cấu hình khởi đầu hợp lý, nhưng cần được chọn bằng tập train hoặc validation. Nếu chưa có kết quả sweep được lưu và kiểm chứng, sử dụng nó trong phiên bản cuối sẽ bổ sung một quyết định khó chứng minh.

## 15. Cách viết lý do trong báo cáo

Có thể sử dụng đoạn sau:

> MMR đã được xây dựng như một phương án hậu xử lý nhằm giảm các câu trùng lặp. Tuy nhiên, phiên bản cuối sử dụng trực tiếp Top-K theo PageRank để giữ phạm vi nghiên cứu tập trung vào ảnh hưởng của biểu diễn TF-IDF, trọng số đồ thị và Personalized PageRank. Việc bật MMR đồng thời thay đổi chính sách lựa chọn câu, giới hạn độ dài và bổ sung tham số lambda, làm khó cô lập tác động của trọng số câu mới. Ngoài ra, chưa có artifact thực nghiệm đầy đủ trong phiên bản hiện tại để khẳng định MMR cải thiện các chỉ số đánh giá. Vì vậy, MMR được giữ như một hướng mở rộng và sẽ chỉ được lựa chọn sau khi đánh giá ablation trên cùng ngân sách đầu ra.

Không nên viết:

> Không chọn MMR vì MMR cho kết quả kém.

Trừ khi đã có CSV thực nghiệm chứng minh nhận định đó.

## 16. Thiết kế thí nghiệm công bằng cho MMR

Muốn quyết định có chọn MMR hay không, nên chạy ablation với các điều kiện đầu ra tương đương.

### 16.1. So sánh đề xuất

| Cấu hình | PageRank | MMR | Lambda | Ngân sách |
|---|---|---|---:|---:|
| A | Thông thường | Tắt | – | 100 từ |
| B | Thông thường | Bật | 0.3 | 100 từ |
| C | Thông thường | Bật | 0.5 | 100 từ |
| D | Thông thường | Bật | 0.7 | 100 từ |
| E | Thông thường | Bật | 0.9 | 100 từ |
| F | Personalized | Tắt | – | 100 từ |
| G | Personalized | Bật | 0.7 | 100 từ |

Điểm quan trọng là cấu hình không dùng MMR cũng phải chọn câu trong cùng ngân sách 100 từ. Không nên so Top-K 15 câu với MMR 100 từ rồi quy toàn bộ chênh lệch cho MMR.

### 16.2. Chỉ số cần báo cáo

- Macro Precision.
- Macro Recall.
- Macro F1.
- Số topic có F1 bằng 0.
- Số câu trung bình.
- Số từ trung bình.
- Mức sử dụng ngân sách.
- Mean pairwise redundancy.
- Maximum pairwise redundancy.

### 16.3. Đo redundancy của bản tóm tắt

Với tập $S$ gồm $m$ câu đã chọn, mean redundancy có thể tính bằng:

$$
MeanRedundancy
=
\frac{2}{m(m-1)}
\sum_{i<j}Sim(i,j)
$$

Maximum redundancy:

$$
MaxRedundancy
=
\max_{i<j}Sim(i,j)
$$

MMR có ý nghĩa nếu giảm redundancy mà không làm giảm quá nhiều Precision, Recall và F1.

### 16.4. Quy trình chọn tham số

1. Khóa TF-IDF, threshold, damping và personalization.
2. Chạy cấu hình không MMR trên train.
3. Chạy các lambda trên train hoặc validation.
4. Chọn lambda theo tiêu chí đã định trước.
5. Chỉ đánh giá một lần trên test.
6. Lưu CSV và cấu hình để kết quả có thể tái lập.

## 17. Khi nào nên chọn MMR?

Nên cân nhắc bật MMR khi:

- Bản tóm tắt thường chứa nhiều câu cùng ý.
- Mean hoặc maximum redundancy cao.
- Topic có nhiều tài liệu cùng lặp một sự kiện.
- MMR giảm redundancy mà vẫn giữ hoặc cải thiện F1.
- Đầu ra cần tuân thủ ngân sách từ chặt chẽ.

Không nên bật chỉ vì MMR là một phương pháp phổ biến. Nó cần giải quyết một vấn đề được đo thấy trong kết quả hiện tại.

## 18. Khi nào Top-K phù hợp hơn?

Top-K phù hợp hơn khi:

- Mục tiêu là giải thích trực tiếp PageRank.
- Cần cô lập tác động của trọng số đồ thị hoặc trọng số đỉnh.
- Muốn một baseline đơn giản, dễ tái lập.
- Chưa có kết quả tuning lambda đáng tin cậy.
- Chưa chuẩn hóa ngân sách đầu ra giữa các phương pháp.

## 19. Kết luận

MMR là một bước lựa chọn câu có khả năng giảm trùng lặp bằng cách cân bằng PageRank relevance và cosine redundancy:

$$
MMR(i)
=
\lambda Rel(i)
-
(1-\lambda)Redundancy(i)
$$

Trong dự án, MMR đã được cài đặt với kiểm soát ngân sách từ, quy tắc phá hòa và khôi phục thứ tự nguồn. Tuy nhiên, phiên bản cuối hiện tại chưa sử dụng MMR vì cần giữ bài toán tập trung vào PageRank, cô lập tác động của trọng số câu mới và tránh đưa thêm lambda cùng chính sách độ dài chưa được xác nhận bằng artifact thực nghiệm đầy đủ.

Do đó, kết luận phù hợp không phải là “MMR không tốt”, mà là:

> MMR là hướng hậu xử lý tiềm năng nhưng chưa được lựa chọn cho phiên bản cuối vì chưa đáp ứng điều kiện so sánh công bằng và truy vết thực nghiệm cần thiết.
