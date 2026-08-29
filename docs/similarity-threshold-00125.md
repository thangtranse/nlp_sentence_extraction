# Cơ sở lựa chọn `SIMILARITY_THRESHOLD = 0.0125`

## 1. Kết luận ngắn gọn

Giá trị:

```python
SIMILARITY_THRESHOLD = 0.0125
```

được chọn trong nhánh thực nghiệm:

```text
TF-IDF + cosine similarity
    → đồ thị câu có trọng số
    → PageRank
    → lấy cố định Top-K = 15 câu
```

Nó được chọn vì đạt **Macro F1 cao nhất trong lưới mịn gồm 13 ngưỡng đã thử trên tập train** khi các tham số khác được giữ cố định.

Kết quả lịch sử của nhánh PageRank + Top-K=15:

| Macro Precision | Macro Recall | Macro F1 | Topic F1 bằng 0 |
|---:|---:|---:|---:|
| 0.1598 | 0.1662 | **0.1607** | 4/34 |

Kết luận này chỉ áp dụng cho nhánh lấy cố định 15 câu PageRank cao nhất. Nó không có nghĩa `0.0125` là ngưỡng tối ưu phổ quát cho mọi cách tiền xử lý, mọi dữ liệu hoặc mọi chính sách chọn câu.

## 2. Phân biệt `0.0125` và `0.0275`

Lịch sử dự án có hai ngưỡng quan trọng:

| Ngưỡng | Pipeline áp dụng | Chính sách đầu ra |
|---:|---|---|
| `0.0125` | PageRank | Top-K cố định, $K=15$ |
| `0.0275` | PageRank + MMR | Giới hạn 100 từ, $\lambda=0.70$ |

Hai giá trị này không mâu thuẫn. Chúng được chọn cho hai pipeline khác nhau.

Trong nhánh Top-K:

$$
Summary
=
TopK\left(PR(i),K=15\right)
$$

Trong nhánh MMR:

$$
i^*
=
\underset{i\in R}{\arg\max}
\left[
\lambda Rel(i)
-
(1-\lambda)Redundancy(i)
\right]
$$

với điều kiện tổng độ dài không vượt quá 100 từ.

Do chính sách chọn câu khác nhau, thay đổi threshold có thể dẫn đến kết quả khác nhau. Vì vậy:

> `0.0125` là ngưỡng được chọn cho PageRank + Top-K=15; `0.0275` là ngưỡng được chọn về sau cho PageRank + MMR + ngân sách 100 từ.

## 3. `SIMILARITY_THRESHOLD` là gì?

### 3.1. Vai trò

Mỗi câu là một đỉnh của đồ thị. Hai câu chỉ được nối bằng cạnh nếu cosine similarity của chúng đạt ngưỡng.

Gọi:

- $s_i$ là câu thứ $i$.
- $s_j$ là câu thứ $j$.
- $\vec{v_i}$ là vector TF-IDF của câu $i$.
- $\vec{v_j}$ là vector TF-IDF của câu $j$.
- $\theta$ là `SIMILARITY_THRESHOLD`.

Điều kiện tạo cạnh:

$$
(i,j)\in E
\iff
\cos\left(\vec{v_i},\vec{v_j}\right)\ge\theta
$$

Với cấu hình lịch sử:

$$
\theta=0.0125
$$

Do đó:

$$
(i,j)\in E
\iff
\cos\left(\vec{v_i},\vec{v_j}\right)\ge 0.0125
$$

### 3.2. Trọng số cạnh

Nếu cạnh được giữ, trọng số của nó không bị đổi thành 1. Trọng số vẫn là cosine similarity thật:

$$
w_{ij}
=
\cos\left(\vec{v_i},\vec{v_j}\right)
$$

Nếu cosine thấp hơn ngưỡng, cạnh không tồn tại:

$$
w_{ij}=0
\quad\text{khi}\quad
\cos\left(\vec{v_i},\vec{v_j}\right)<\theta
$$

Có thể biểu diễn ma trận kề có trọng số như sau:

$$
A_{ij}
=
\begin{cases}
\cos\left(\vec{v_i},\vec{v_j}\right),
& i\ne j\;\text{và}\;\cos\left(\vec{v_i},\vec{v_j}\right)\ge\theta\\
0,
& \text{ngược lại}
\end{cases}
$$

Đồ thị không có self-loop:

$$
A_{ii}=0
$$

Vì cosine đối xứng:

$$
\cos\left(\vec{v_i},\vec{v_j}\right)
=
\cos\left(\vec{v_j},\vec{v_i}\right)
$$

nên đồ thị là đồ thị vô hướng có trọng số:

$$
A_{ij}=A_{ji}
$$

## 4. Công thức TF-IDF trước khi tính threshold

Threshold không được áp dụng trực tiếp lên câu thô. Nó được áp dụng lên cosine similarity của các vector TF-IDF.

### 4.1. Term Frequency

Trong code, TF là số lần từ $t$ xuất hiện trong câu $s_i$:

$$
TF(t,s_i)
=
count(t,s_i)
$$

Ví dụ, câu sau khi tiền xử lý:

```text
earthquake iran earthquake damage
```

Ta có:

$$
TF(earthquake,s_i)=2
$$

$$
TF(iran,s_i)=1
$$

$$
TF(damage,s_i)=1
$$

### 4.2. Document Frequency

Mỗi câu được xem như một document nhỏ trong quá trình xây TF-IDF.

Document Frequency của từ $t$:

$$
DF(t)
=
\left|
\left\{
s_i:t\in s_i
\right\}
\right|
$$

Nếu một từ xuất hiện trong 10 câu khác nhau thì:

$$
DF(t)=10
$$

Số lần lặp trong cùng một câu không làm tăng DF thêm lần nữa.

### 4.3. Smooth IDF

Code sử dụng smooth IDF:

$$
IDF(t)
=
\ln\left(
\frac{1+N}{1+DF(t)}
\right)
+1
$$

Trong đó $N$ là tổng số câu trong topic.

Việc cộng 1 ở tử và mẫu giúp tránh phép chia không hợp lệ và làm công thức ổn định hơn.

### 4.4. TF-IDF

Trọng số TF-IDF của từ $t$ trong câu $s_i$:

$$
TFIDF(t,s_i)
=
TF(t,s_i)\times IDF(t)
$$

Vector chưa chuẩn hóa của câu:

$$
\vec{x_i}
=
\left(
TFIDF(t_1,s_i),
TFIDF(t_2,s_i),
\ldots,
TFIDF(t_V,s_i)
\right)
$$

Trong đó $V$ là số từ trong vocabulary.

### 4.5. Chuẩn hóa L2

Độ dài vector:

$$
\left\|\vec{x_i}\right\|_2
=
\sqrt{
\sum_{k=1}^{V}x_{ik}^{2}
}
$$

Vector sau chuẩn hóa:

$$
\vec{v_i}
=
\frac{\vec{x_i}}{\left\|\vec{x_i}\right\|_2}
$$

Khi vector khác rỗng:

$$
\left\|\vec{v_i}\right\|_2=1
$$

## 5. Công thức cosine similarity

Cosine similarity giữa hai câu:

$$
\cos\left(\vec{v_i},\vec{v_j}\right)
=
\frac{
\vec{v_i}\cdot\vec{v_j}
}{
\left\|\vec{v_i}\right\|_2
\left\|\vec{v_j}\right\|_2
}
$$

Tích vô hướng:

$$
\vec{v_i}\cdot\vec{v_j}
=
\sum_{k=1}^{V}v_{ik}v_{jk}
$$

Vì các vector đã chuẩn hóa L2:

$$
\left\|\vec{v_i}\right\|_2
=
\left\|\vec{v_j}\right\|_2
=1
$$

nên cosine rút gọn thành:

$$
\cos\left(\vec{v_i},\vec{v_j}\right)
=
\vec{v_i}\cdot\vec{v_j}
$$

Với vector TF-IDF không âm:

$$
0\le\cos\left(\vec{v_i},\vec{v_j}\right)\le1
$$

Ý nghĩa:

- Gần 0: hai câu có rất ít từ quan trọng chung.
- Gần 1: hai câu có phân bố TF-IDF rất giống nhau.

## 6. `0.0125` không phải 1,25% giống nhau về ngữ nghĩa

Không nên diễn giải:

> Hai câu giống nhau ít nhất 1,25% về mặt ngữ nghĩa thì được nối.

`0.0125` là ngưỡng hình học trong không gian vector TF-IDF. Nó chủ yếu phản ánh mức độ trùng khớp từ vựng đã được điều chỉnh bởi TF và IDF.

Ngưỡng này không trực tiếp hiểu được:

- từ đồng nghĩa;
- paraphrase;
- quan hệ nguyên nhân – kết quả;
- thực thể đồng tham chiếu;
- hai câu cùng nghĩa nhưng dùng từ khác nhau.

Cách diễn đạt đúng:

> Hai câu được nối khi cosine similarity giữa hai vector TF-IDF đạt ít nhất 0.0125.

## 7. Ví dụ tạo cạnh

Giả sử có các cosine similarity:

| Cặp câu | Cosine | Có cạnh khi $\theta=0.0125$? | Trọng số cạnh |
|---|---:|---|---:|
| A–B | 0.3200 | Có | 0.3200 |
| A–C | 0.1400 | Có | 0.1400 |
| A–D | 0.0300 | Có | 0.0300 |
| B–C | 0.0125 | Có | 0.0125 |
| B–D | 0.0100 | Không | 0 |
| C–D | 0.0000 | Không | 0 |

Vì code sử dụng điều kiện lớn hơn hoặc bằng:

$$
similarity\ge threshold
$$

nên cạnh có cosine đúng bằng `0.0125` vẫn được giữ.

Lưu ý: một số tài liệu lịch sử có bảng ví dụ cũ không đồng nhất với điều kiện code. Điều kiện chính xác theo hàm xây đồ thị là `similarity >= threshold`.

## 8. Threshold tác động đến cấu trúc đồ thị như thế nào?

### 8.1. Threshold thấp

Khi $\theta$ giảm:

$$
\theta\downarrow
\quad\Longrightarrow\quad
|E|\uparrow
$$

Nhiều cạnh yếu được giữ lại. Hệ quả có thể gồm:

- đồ thị dày hơn;
- nhiều câu được nối dù chỉ chia sẻ ít từ;
- các chủ đề con bị nối với nhau bởi cạnh yếu;
- PageRank nhận nhiều đường truyền điểm;
- chênh lệch điểm giữa các câu có thể giảm.

Nếu đặt:

$$
\theta=0
$$

thì cần đặc biệt tránh tạo cạnh có trọng số đúng bằng 0. Trong script sweep lịch sử, cạnh chỉ được tạo khi:

$$
w_{ij}>0
\quad\text{và}\quad
w_{ij}\ge\theta
$$

### 8.2. Threshold cao

Khi $\theta$ tăng:

$$
\theta\uparrow
\quad\Longrightarrow\quad
|E|\downarrow
$$

Chỉ các quan hệ mạnh được giữ lại. Hệ quả có thể gồm:

- đồ thị thưa hơn;
- số đỉnh cô lập tăng;
- số connected component tăng;
- PageRank có ít liên kết để lan truyền;
- nhiều dangling node phải phân phối lại điểm.

### 8.3. Bài toán cân bằng

Mục tiêu không phải chọn threshold làm đồ thị dày nhất hoặc thưa nhất. Mục tiêu là tìm một mức lọc đủ để:

- loại bớt cạnh nhiễu;
- giữ đủ cấu trúc liên kết;
- tạo xếp hạng câu phù hợp với tập tham chiếu.

Có thể mô tả:

$$
\theta^*
=
\underset{\theta\in\Theta}{\arg\max}
MacroF1(\theta)
$$

trong lưới ngưỡng đã thử $\Theta$.

## 9. Các chỉ số cấu trúc đồ thị

### 9.1. Số cạnh tối đa

Với đồ thị vô hướng có $N$ đỉnh và không có self-loop:

$$
E_{max}
=
\frac{N(N-1)}{2}
$$

### 9.2. Edge density

Mật độ cạnh:

$$
Density
=
\frac{|E|}{E_{max}}
$$

Thay $E_{max}$ vào:

$$
Density
=
\frac{2|E|}{N(N-1)}
$$

Giá trị nằm trong khoảng:

$$
0\le Density\le1
$$

- Density gần 1: gần như mọi cặp câu đều nối với nhau.
- Density gần 0: đồ thị rất thưa.

### 9.3. Bậc của đỉnh

Bậc của câu $i$:

$$
deg(i)
=
\left|
\left\{
j:(i,j)\in E
\right\}
\right|
$$

Bậc trung bình:

$$
AverageDegree
=
\frac{1}{N}
\sum_{i=1}^{N}deg(i)
$$

Với đồ thị vô hướng:

$$
\sum_{i=1}^{N}deg(i)=2|E|
$$

nên:

$$
AverageDegree
=
\frac{2|E|}{N}
$$

### 9.4. Tỷ lệ đỉnh cô lập

Gọi $I$ là số câu có bậc bằng 0:

$$
I
=
\left|
\left\{
i:deg(i)=0
\right\}
\right|
$$

Tỷ lệ đỉnh cô lập:

$$
IsolatedRatio
=
\frac{I}{N}
$$

Threshold cao thường làm chỉ số này tăng.

### 9.5. Connected components

Connected component là một nhóm đỉnh có đường đi đến nhau. Nhiều component có thể phản ánh nhiều sự kiện con, nhưng quá nhiều component nhỏ thường cho thấy threshold đã loại quá nhiều cạnh.

## 10. Threshold tác động vào Weighted PageRank

PageRank có trọng số:

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

$$
w_{ji}
=
\begin{cases}
\cos\left(\vec{v_j},\vec{v_i}\right),
& \cos\left(\vec{v_j},\vec{v_i}\right)\ge\theta\\
0,
& \text{ngược lại}
\end{cases}
$$

Threshold ảnh hưởng đến cả hai thành phần:

1. Tập hàng xóm $Out(j)$.
2. Tổng trọng số đi ra $\sum_k w_{jk}$.

Vì thế, chỉ cần thêm hoặc bỏ một cạnh cũng có thể thay đổi tỷ lệ điểm PageRank mà câu $j$ truyền cho mọi hàng xóm.

### 10.1. Ví dụ phân phối điểm

Giả sử câu $j$ có ba cạnh:

```text
w(j,A) = 0.30
w(j,B) = 0.10
w(j,C) = 0.01
```

Nếu threshold bằng 0.0, tổng trọng số:

$$
W_j=0.30+0.10+0.01=0.41
$$

Tỷ lệ truyền cho A:

$$
\frac{0.30}{0.41}=0.7317
$$

Nếu threshold bằng 0.0125, cạnh đến C bị loại:

$$
W_j=0.30+0.10=0.40
$$

Tỷ lệ truyền cho A:

$$
\frac{0.30}{0.40}=0.75
$$

Như vậy threshold không chỉ xóa cạnh yếu; nó còn phân phối lại điểm cho các cạnh còn lại.

## 11. Tại sao lưới thử tập trung ở vùng thấp?

Lưới lịch sử gồm 13 giá trị:

```python
THRESHOLDS = [
    0.0000,
    0.0025,
    0.0050,
    0.0075,
    0.0100,
    0.0125,
    0.0150,
    0.0175,
    0.0200,
    0.0225,
    0.0250,
    0.0275,
    0.0300,
]
```

Đây là một fine sweep với bước:

$$
\Delta\theta=0.0025
$$

Lưới tập trung từ 0 đến 0.03 vì các vector câu TF-IDF trong topic nhiều tài liệu thường khá thưa. Nhiều cặp câu chỉ chia sẻ một lượng nhỏ từ quan trọng, nên cosine hữu ích có thể nằm ở vùng thấp.

Ngưỡng 0.1 hoặc 0.5 có thể loại phần lớn quan hệ giữa các câu không lặp từ vựng mạnh. Fine sweep vùng thấp giúp tìm mức lọc tinh hơn thay vì nhảy qua vùng phù hợp.

## 12. Cách `TOP_K = 15` được xác định

Ngưỡng `0.0125` không được chọn độc lập với $K$. Lịch sử cho thấy $K=15$ được chọn từ thống kê reference trên tập train.

| Thống kê | Giá trị |
|---|---:|
| Tổng topic train | 50 |
| Reference có nội dung | 34 |
| Reference rỗng | 16 |
| Tổng số câu reference hợp lệ | 518 |
| Trung bình số câu/reference | 15.235 |
| Trung vị | 15 |
| Nhỏ nhất – lớn nhất | 10–20 |
| Top-K được chọn | **15** |

$K$ được lấy từ trung vị:

$$
K
=
Median\left(
|Reference_1|,
|Reference_2|,
\ldots,
|Reference_{34}|
\right)
$$

$$
K=15
$$

Việc chọn $K$ từ train giúp tránh sử dụng thông tin của test để điều chỉnh mô hình.

## 13. Quy trình sweep dẫn đến `0.0125`

### Bước 1: chuẩn bị dữ liệu train

Script đọc 50 topic trong:

```text
data/DUC_TEXT/train
```

Chỉ những topic có file reference cùng tên và reference không rỗng mới được đưa vào phép đánh giá chất lượng. Có 34 topic hợp lệ.

### Bước 2: tính TF-IDF và ma trận cosine đầy đủ

Mỗi topic được xử lý một lần để tạo:

$$
M_{ij}
=
\cos\left(\vec{v_i},\vec{v_j}\right)
$$

Ma trận đầy đủ được giữ trước khi thử threshold, giúp mỗi cấu hình sử dụng cùng dữ liệu cosine.

### Bước 3: thử từng threshold

Với mỗi:

$$
\theta\in\Theta
$$

script xây lại đồ thị:

$$
G_{\theta}=(V,E_{\theta})
$$

Trong đó:

$$
E_{\theta}
=
\left\{
(i,j):M_{ij}>0\;\land\;M_{ij}\ge\theta
\right\}
$$

### Bước 4: giữ cố định PageRank

Các tham số được giữ cố định:

```ini
PAGERANK_DAMPING = 0.85
PAGERANK_TOLERANCE = 1e-8
PAGERANK_MAX_ITERATIONS = 1000
TOP_K = 15
```

Điều này giúp cô lập ảnh hưởng của threshold.

### Bước 5: lấy Top-K

Các câu được sắp xếp giảm dần theo PageRank:

$$
PR(s_{(1)})
\ge
PR(s_{(2)})
\ge
\cdots
\ge
PR(s_{(N)})
$$

Prediction:

$$
Prediction_{\theta}
=
\left\{
s_{(1)},s_{(2)},\ldots,s_{(15)}
\right\}
$$

### Bước 6: so sánh exact sentence match

Gọi:

- $P_t$ là tập câu dự đoán của topic $t$.
- $R_t$ là tập câu reference của topic $t$.
- $TP_t=P_t\cap R_t$.

Số câu đúng:

$$
Correct_t
=
|P_t\cap R_t|
$$

Precision:

$$
Precision_t
=
\frac{|P_t\cap R_t|}{|P_t|}
$$

Recall:

$$
Recall_t
=
\frac{|P_t\cap R_t|}{|R_t|}
$$

F1:

$$
F1_t
=
\frac{
2\times Precision_t\times Recall_t
}{
Precision_t+Recall_t
}
$$

Nếu cả Precision và Recall đều bằng 0 thì:

$$
F1_t=0
$$

### Bước 7: tính Macro Average

Với $T=34$ topic hợp lệ:

$$
MacroPrecision
=
\frac{1}{T}
\sum_{t=1}^{T}Precision_t
$$

$$
MacroRecall
=
\frac{1}{T}
\sum_{t=1}^{T}Recall_t
$$

$$
MacroF1
=
\frac{1}{T}
\sum_{t=1}^{T}F1_t
$$

Macro-average cho mỗi topic trọng số bằng nhau, không để topic có nhiều câu chi phối toàn bộ kết quả.

### Bước 8: chọn ngưỡng trên train

Trong lưới đã thử:

$$
\theta^*
=
\underset{\theta\in\Theta}{\arg\max}
MacroF1_{train}(\theta)
$$

Kết quả lịch sử:

$$
\theta^*=0.0125
$$

với:

$$
MacroPrecision=0.1598
$$

$$
MacroRecall=0.1662
$$

$$
MacroF1=0.1607
$$

và:

$$
ZeroF1Topics=4/34
$$

## 14. Tại sao chọn theo Macro F1?

Precision và Recall phản ánh hai mục tiêu khác nhau:

- Precision cao: phần lớn câu được chọn là đúng theo reference.
- Recall cao: chọn được phần lớn câu trong reference.

Nếu chỉ tối ưu Precision, thuật toán có thể chọn rất ít câu. Nếu chỉ tối ưu Recall, thuật toán có thể chọn quá nhiều câu.

F1 là trung bình điều hòa:

$$
F1
=
\frac{2PR}{P+R}
$$

F1 chỉ cao khi cả Precision và Recall tương đối tốt.

Macro F1 được ưu tiên vì bài đánh giá nhiều topic và cần tránh để topic lớn chi phối kết quả.

## 15. Tại sao `0.0125` hợp lý cho nhánh Top-K?

Có ba lớp lý do.

### 15.1. Lý do thực nghiệm

Trong lưới 13 giá trị đã thử, `0.0125` đạt Macro F1 cao nhất cho PageRank + Top-K=15.

Đây là lý do trực tiếp và quan trọng nhất.

### 15.2. Lý do cấu trúc đồ thị

Ngưỡng nằm trong vùng thấp nên giữ được nhiều liên kết giữa các câu của nhiều tài liệu, nhưng vẫn loại các cặp có cosine bằng 0 hoặc quá yếu.

Nó tạo điểm cân bằng giữa:

$$
\text{giữ liên kết chủ đề}
\quad\text{và}\quad
\text{loại cạnh nhiễu}
$$

### 15.3. Lý do thiết kế thí nghiệm

Ngưỡng được chọn trên tập train, trong khi các tham số PageRank và Top-K được giữ cố định. Điều này giảm nguy cơ quy nhầm cải thiện cho nhiều thay đổi cùng lúc.

## 16. Vì sao không chọn threshold thấp hơn?

Threshold thấp hơn giữ thêm các cạnh rất yếu:

$$
0\le w_{ij}<0.0125
$$

Những cạnh này có thể chỉ xuất phát từ một lượng nhỏ từ vựng chung. Khi được giữ lại, chúng:

- làm tăng density;
- nối các nhóm nội dung chỉ liên quan yếu;
- chia nhỏ PageRank qua nhiều hàng xóm;
- có thể làm giảm khả năng phân biệt các câu trung tâm.

Quan trọng nhất, trong phép sweep lịch sử, các ngưỡng thấp hơn không đạt Macro F1 cao hơn `0.0125` cho Top-K=15.

## 17. Vì sao không chọn threshold cao hơn?

Threshold cao hơn loại thêm cạnh:

$$
0.0125\le w_{ij}<\theta_{higher}
$$

Các cạnh này tuy yếu nhưng có thể mang thông tin liên kết giữa những bài báo dùng từ vựng hơi khác nhau. Loại quá nhiều cạnh có thể:

- tăng số đỉnh cô lập;
- chia đồ thị thành nhiều component;
- giảm khả năng PageRank nhận ra câu trung tâm xuyên tài liệu;
- tăng ảnh hưởng của dangling mass.

Trong phép sweep lịch sử, các ngưỡng cao hơn cũng không đạt Macro F1 cao hơn `0.0125` cho Top-K=15.

## 18. Hạn chế của kết luận lịch sử

### 18.1. Chỉ là tốt nhất trong lưới đã thử

Ta chỉ biết:

$$
0.0125
=
\underset{\theta\in\Theta}{\arg\max}
MacroF1(\theta)
$$

với lưới $\Theta$ đã thử. Không thể suy ra nó là cực đại trên mọi số thực từ 0 đến 1.

Ví dụ, các giá trị `0.011`, `0.012` hoặc `0.013` không nằm trong lưới này.

### 18.2. Phụ thuộc pipeline

Nếu thay đổi một trong các thành phần sau, threshold tốt nhất có thể đổi:

- tokenizer hoặc stop words;
- công thức TF-IDF;
- chuẩn hóa vector;
- embedding thay cho TF-IDF;
- PageRank thông thường hay Personalized PageRank;
- Top-K hay MMR;
- số câu $K$;
- ngân sách từ;
- metric đánh giá.

### 18.3. Exact sentence match khá nghiêm ngặt

Metric chỉ tính đúng khi câu dự đoán khớp câu reference sau chuẩn hóa. Nó không ghi nhận:

- paraphrase;
- câu gần nghĩa;
- hai câu truyền đạt cùng sự kiện bằng từ khác;
- tính mạch lạc của toàn bản tóm tắt.

### 18.4. Chỉ có 34 topic train hợp lệ

Trong 50 topic train, 16 reference rỗng bị bỏ qua. Do đó kết quả được tính trên 34 topic hợp lệ.

### 18.5. Artifact CSV lịch sử không còn trong checkout hiện tại

Git history, README và báo cáo còn ghi nhận cấu hình được chọn cùng metric tổng hợp. Tuy nhiên, CSV đầy đủ của sweep Top-K không hiện diện trong checkout hiện tại. Vì vậy tài liệu này chỉ ghi các số liệu tổng hợp có thể truy vết, không tự dựng bảng kết quả cho 13 ngưỡng.

Nếu cần xác nhận lại toàn bộ thứ hạng, nên chạy lại script sweep trên đúng commit và lưu CSV.

## 19. Cách chạy lại thực nghiệm lịch sử

Script sweep hiện còn tại:

```text
notebooks/textrank-parameter-analysis/fine_threshold_sweep.py
```

Để tái lập đúng nhánh lịch sử, cần bảo đảm:

```ini
TOP_K = 15
PAGERANK_DAMPING = 0.85
PAGERANK_TOLERANCE = 1e-8
PAGERANK_MAX_ITERATIONS = 1000
USE_MMR = False
```

Danh sách threshold phải là:

```python
THRESHOLDS = [
    0.0000, 0.0025, 0.0050, 0.0075, 0.0100,
    0.0125, 0.0150, 0.0175, 0.0200, 0.0225,
    0.0250, 0.0275, 0.0300,
]
```

Lệnh chạy:

```bash
uv run python notebooks/textrank-parameter-analysis/fine_threshold_sweep.py
```

Sau khi chạy, cần kiểm tra:

- Macro Precision.
- Macro Recall.
- Macro F1.
- Số topic F1 bằng 0.
- Mean density.
- Mean isolated ratio.
- Mean average degree.
- Mean connected components.

Không nên dùng kết quả test để chọn lại threshold. Threshold phải được khóa từ train trước khi đánh giá test.

## 20. Cách trình bày trong báo cáo

Có thể sử dụng đoạn sau:

> `SIMILARITY_THRESHOLD` quyết định một cặp câu có được nối trong đồ thị TextRank hay không. Trước tiên, mỗi câu được biểu diễn bằng vector TF-IDF đã chuẩn hóa L2. Cosine similarity giữa hai vector được dùng làm trọng số cạnh, và cạnh chỉ được giữ khi cosine đạt ít nhất threshold. Nhóm thực hiện quét 13 giá trị từ 0 đến 0.03 với bước 0.0025 trên tập huấn luyện, đồng thời giữ cố định damping bằng 0.85, tolerance bằng $10^{-8}$, số vòng lặp tối đa bằng 1000 và Top-K bằng 15. Trong nhánh PageRank + Top-K=15, ngưỡng 0.0125 đạt Macro Precision 0.1598, Macro Recall 0.1662 và Macro F1 0.1607, cao nhất trong lưới đã thử. Vì vậy 0.0125 được chọn cho nhánh này. Đây là kết quả phụ thuộc dữ liệu và pipeline, không phải ngưỡng tối ưu phổ quát.

Nếu trình bày cả MMR, cần bổ sung:

> Khi chính sách lựa chọn được chuyển từ Top-K=15 sang MMR với ngân sách 100 từ, sweep riêng chọn threshold 0.0275. Do đó 0.0125 và 0.0275 thuộc hai cấu hình thí nghiệm khác nhau và không nên được sử dụng thay thế cho nhau mà không đánh giá lại.

## 21. Những cách diễn đạt cần tránh

Không nên viết:

> `0.0125` nghĩa là hai câu giống nhau 1,25%.

Không nên viết:

> `0.0125` là threshold tốt nhất cho TextRank.

Không nên viết:

> `0.0125` tốt hơn `0.0275` trong mọi trường hợp.

Cách diễn đạt chính xác:

> `0.0125` là threshold đạt Macro F1 cao nhất trong lưới mịn đã thử trên tập train cho pipeline PageRank + Top-K=15.

## 22. Kết luận

Giá trị `SIMILARITY_THRESHOLD = 0.0125` được lựa chọn qua một phép sweep có kiểm soát chứ không phải đặt tùy ý. Thực nghiệm giữ cố định PageRank và Top-K, thay đổi 13 threshold trong vùng 0–0.03, rồi đánh giá exact sentence match trên 34 topic train có reference hợp lệ.

Ngưỡng `0.0125` tạo ra kết quả tổng hợp tốt nhất cho nhánh đó:

$$
MacroPrecision=0.1598
$$

$$
MacroRecall=0.1662
$$

$$
MacroF1=0.1607
$$

$$
ZeroF1Topics=4/34
$$

Vì vậy, lý do chọn `0.0125` là sự kết hợp giữa:

1. Kết quả Macro F1 tốt nhất trong lưới train đã thử.
2. Cân bằng giữa giữ liên kết chủ đề và loại cạnh quá yếu.
3. Quy trình thí nghiệm giữ cố định các tham số khác.

Kết luận này phải luôn đi kèm phạm vi: **PageRank + Top-K=15**, không phải MMR + 100 từ hoặc mọi biến thể TextRank khác.
