"""Build the reproducible edge-weight experiment notebook.

The generated notebook deliberately keeps MMR disabled and follows the active
src/nlp_practice configuration (threshold 0.0125 and TOP_K 15).
"""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = ROOT / "notebooks" / "edge-weight-lambda-damping-experiment.ipynb"


def markdown(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(True)}


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(True),
    }


cells = [
    markdown(r"""# Thí nghiệm mở rộng trọng số cạnh: chọn $d$ và $\lambda$

## Mục tiêu

Notebook kiểm tra bằng dữ liệu thay vì giả định rằng `d = 0.85` hoặc
`lambda = 0.6` luôn tốt nhất. Trọng số cạnh mới là:

$$
w_{ij}(\lambda)=\lambda\,\cos_{TF-IDF}(s_i,s_j)
+(1-\lambda)\,\max(0,\cos_{LSA}(s_i,s_j)).
$$

- $\lambda=1$: baseline TF-IDF hiện tại.
- $\lambda=0$: chỉ dùng không gian ngữ nghĩa tiềm ẩn LSA.
- $\lambda=0.6$: 60% bằng chứng từ vựng và 40% bằng chứng ngữ nghĩa LSA.

Weighted PageRank sử dụng:

$$
PR(i)=\frac{1-d}{N}+d\sum_{j\in In(i)}PR(j)
\frac{w_{ji}}{\sum_k w_{jk}}.
$$

`d` càng lớn thì thứ hạng càng phụ thuộc vào đồ thị; `d` nhỏ làm điểm các câu
gần đều hơn. Giá trị tốt phải được chọn trên train, không lấy từ thông lệ.

> **Phạm vi công bằng:** MMR luôn tắt vì thí nghiệm trước cho kết quả kém.
> Notebook giữ `TOP_K=15` và threshold `0.0125` đúng với module hiện tại."""),
    markdown("""## 1. Thiết lập và giả định

- LSA dùng `TruncatedSVD` từ scikit-learn nên chạy được bằng dependency hiện có.
- LSA là biểu diễn ngữ nghĩa tiềm ẩn theo đồng xuất hiện từ, không phải
  contextual embedding như Sentence-BERT.
- Chọn cấu hình bằng Macro-F1 trên `DUC_TEXT/train`.
- Khóa cấu hình trước khi đánh giá đúng một lần trên `DUC_TEXT/test`.
- Đánh giá khớp nguyên câu sau khi `casefold` và chuẩn hóa khoảng trắng, giống
  `src/evaluation`.
- Các topic có reference rỗng bị bỏ qua và được báo cáo rõ."""),
    code("""from pathlib import Path
import csv
import json
import math
import random
import re
import statistics
import sys
import time

import matplotlib.pyplot as plt
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize

PROJECT_ROOT = Path.cwd()
if not (PROJECT_ROOT / 'src').is_dir():
    PROJECT_ROOT = Path.cwd().parent
sys.path.insert(0, str(PROJECT_ROOT / 'notebooks' / 'textrank-parameter-analysis'))

from experiment_utils import (
    calculate_pagerank,
    calculate_tfidf_vectors,
    read_topic,
)

TRAIN_DIR = PROJECT_ROOT / 'data' / 'DUC_TEXT' / 'train'
TEST_DIR = PROJECT_ROOT / 'data' / 'DUC_TEXT' / 'test'
REFERENCE_DIR = PROJECT_ROOT / 'data' / 'DUC_SUM'
OUTPUT_DIR = PROJECT_ROOT / 'data' / 'output' / 'edge-weight-experiment'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SIMILARITY_THRESHOLD = 0.0125
TOP_K = 15
DAMPING_VALUES = [0.70, 0.80, 0.85, 0.90, 0.95]
LAMBDA_VALUES = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
LSA_COMPONENTS = 50
RANDOM_STATE = 42

print('Project:', PROJECT_ROOT)
print('MMR: OFF | threshold:', SIMILARITY_THRESHOLD, '| TOP_K:', TOP_K)
print('d:', DAMPING_VALUES)
print('lambda:', LAMBDA_VALUES)"""),
    markdown("""## 2. Chuẩn bị TF-IDF, LSA và ground truth

Mỗi topic chỉ được vector hóa một lần. Sau đó các cấu hình dùng lại hai ma trận
tương đồng để việc sweep không thay đổi dữ liệu đầu vào."""),
    code("""def dense_tfidf(vectors):
    vocabulary = sorted({term for vector in vectors for term in vector})
    term_to_column = {term: index for index, term in enumerate(vocabulary)}
    matrix = np.zeros((len(vectors), len(vocabulary)), dtype=float)
    for row_index, vector in enumerate(vectors):
        for term, value in vector.items():
            matrix[row_index, term_to_column[term]] = value
    return matrix


def cosine_matrix(matrix):
    normalized = normalize(matrix, norm='l2', axis=1)
    similarities = normalized @ normalized.T
    similarities = np.asarray(similarities)
    np.fill_diagonal(similarities, 0.0)
    return np.clip(similarities, 0.0, 1.0)


def lsa_similarity(tfidf_matrix):
    max_components = min(
        LSA_COMPONENTS,
        tfidf_matrix.shape[0] - 1,
        tfidf_matrix.shape[1] - 1,
    )
    if max_components < 2:
        return np.zeros((tfidf_matrix.shape[0], tfidf_matrix.shape[0]))
    reduced = TruncatedSVD(
        n_components=max_components,
        random_state=RANDOM_STATE,
    ).fit_transform(tfidf_matrix)
    return cosine_matrix(reduced)


def normalized_text(text):
    return re.sub(r'\\s+', ' ', text).strip().casefold()


def prepare_split(input_dir):
    prepared = []
    skipped = []
    for topic_path in sorted(path for path in input_dir.iterdir() if path.is_file()):
        reference_path = REFERENCE_DIR / topic_path.name
        if not reference_path.is_file():
            skipped.append((topic_path.name, 'missing reference'))
            continue
        sentences = read_topic(topic_path)
        references = {
            normalized_text(sentence.content)
            for sentence in read_topic(reference_path)
            if normalized_text(sentence.content)
        }
        if not sentences:
            skipped.append((topic_path.name, 'empty input'))
            continue
        if not references:
            skipped.append((topic_path.name, 'empty reference'))
            continue
        manual_vectors = calculate_tfidf_vectors(sentences)
        tfidf_matrix = dense_tfidf(manual_vectors)
        prepared.append({
            'topic': topic_path.name,
            'sentences': sentences,
            'references': references,
            'tfidf_similarity': cosine_matrix(tfidf_matrix),
            'lsa_similarity': lsa_similarity(tfidf_matrix),
        })
    return prepared, skipped


train_topics, train_skipped = prepare_split(TRAIN_DIR)
test_topics, test_skipped = prepare_split(TEST_DIR)
print('Train hợp lệ:', len(train_topics), '| bỏ qua:', len(train_skipped))
print('Test hợp lệ :', len(test_topics), '| bỏ qua:', len(test_skipped))
print('Train skipped:', train_skipped)
print('Test skipped :', test_skipped)"""),
    markdown("""## 3. Chạy một cấu hình

Không dùng MMR. Các câu được xếp hạng trực tiếp theo PageRank và lấy 15 câu đầu,
đúng với `rank_sentences_by_pagerank(..., top_k=15)` của module hiện tại."""),
    code("""def graph_from_similarity(similarities):
    node_count = similarities.shape[0]
    graph = {index: {} for index in range(node_count)}
    for left in range(node_count):
        for right in range(left + 1, node_count):
            weight = float(similarities[left, right])
            if weight >= SIMILARITY_THRESHOLD:
                graph[left][right] = weight
                graph[right][left] = weight
    return graph


def evaluate_topic(topic, damping, edge_lambda):
    combined = (
        edge_lambda * topic['tfidf_similarity']
        + (1.0 - edge_lambda) * topic['lsa_similarity']
    )
    graph = graph_from_similarity(combined)
    scores, iterations = calculate_pagerank(
        graph,
        damping=damping,
        tolerance=1e-8,
        max_iterations=1000,
    )
    ranked = sorted(scores, key=lambda index: (-scores[index], index))[:TOP_K]
    predictions = {
        normalized_text(topic['sentences'][index].content)
        for index in ranked
    }
    references = topic['references']
    true_positive = len(predictions & references)
    precision = true_positive / len(predictions) if predictions else 0.0
    recall = true_positive / len(references) if references else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    edges = sum(len(neighbors) for neighbors in graph.values()) // 2
    isolated = sum(not neighbors for neighbors in graph.values())
    return {
        'topic': topic['topic'],
        'damping': damping,
        'edge_lambda': edge_lambda,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'iterations': iterations,
        'edges': edges,
        'isolated_ratio': isolated / len(graph) if graph else 0.0,
    }


def evaluate_grid(topics, damping_values, lambda_values):
    detail = []
    started = time.perf_counter()
    for damping in damping_values:
        for edge_lambda in lambda_values:
            for topic in topics:
                detail.append(evaluate_topic(topic, damping, edge_lambda))
    print(f'Đã chạy {len(detail)} topic-config trong {time.perf_counter()-started:.2f}s')
    return detail


def aggregate(detail):
    grouped = {}
    for row in detail:
        grouped.setdefault((row['damping'], row['edge_lambda']), []).append(row)
    summary = []
    for (damping, edge_lambda), rows in grouped.items():
        summary.append({
            'damping': damping,
            'edge_lambda': edge_lambda,
            'eligible_topics': len(rows),
            'macro_precision': statistics.fmean(row['precision'] for row in rows),
            'macro_recall': statistics.fmean(row['recall'] for row in rows),
            'macro_f1': statistics.fmean(row['f1'] for row in rows),
            'mean_iterations': statistics.fmean(row['iterations'] for row in rows),
            'mean_edges': statistics.fmean(row['edges'] for row in rows),
            'mean_isolated_ratio': statistics.fmean(row['isolated_ratio'] for row in rows),
        })
    return sorted(summary, key=lambda row: (row['damping'], row['edge_lambda']))


train_detail = evaluate_grid(train_topics, DAMPING_VALUES, LAMBDA_VALUES)
train_summary = aggregate(train_detail)
print('Số cấu hình:', len(train_summary))"""),
    markdown(r"""## 4. Chọn $d$ và $\lambda$ trên train

Tiêu chí chính là Macro-F1; nếu bằng nhau, ưu tiên Precision cao hơn, rồi cấu
hình gần baseline hơn. Đây là quy tắc xác định trước, tránh chọn thủ công sau
khi nhìn kết quả."""),
    code("""def selection_key(row):
    return (
        row['macro_f1'],
        row['macro_precision'],
        -abs(row['damping'] - 0.85),
        -abs(row['edge_lambda'] - 1.0),
    )


ranked_train = sorted(train_summary, key=selection_key, reverse=True)
best_train = ranked_train[0]
baseline_train = next(
    row for row in train_summary
    if row['damping'] == 0.85 and row['edge_lambda'] == 1.0
)
lambda_06_best = max(
    (row for row in train_summary if row['edge_lambda'] == 0.6),
    key=selection_key,
)

print('Top 10 cấu hình trên train:')
for rank, row in enumerate(ranked_train[:10], start=1):
    print(
        f"{rank:2d}. d={row['damping']:.2f}, lambda={row['edge_lambda']:.1f}, "
        f"P={row['macro_precision']:.4f}, R={row['macro_recall']:.4f}, "
        f"F1={row['macro_f1']:.4f}, iterations={row['mean_iterations']:.1f}"
    )
print('\\nBaseline:', baseline_train)
print('Best lambda=0.6:', lambda_06_best)
print('Selected:', best_train)"""),
    markdown(r"""### Trực quan hóa bề mặt tham số

Heatmap cho thấy vùng tham số ổn định hay chỉ có một điểm thắng ngẫu nhiên.
Biểu đồ damping tách riêng ảnh hưởng của $d$ tại từng $\lambda$."""),
    code("""f1_grid = np.array([
    [next(row['macro_f1'] for row in train_summary
          if row['damping'] == damping and row['edge_lambda'] == edge_lambda)
     for edge_lambda in LAMBDA_VALUES]
    for damping in DAMPING_VALUES
])

fig, axes = plt.subplots(1, 2, figsize=(15, 5))
image = axes[0].imshow(f1_grid, cmap='YlGnBu', aspect='auto')
axes[0].set_xticks(range(len(LAMBDA_VALUES)), LAMBDA_VALUES)
axes[0].set_yticks(range(len(DAMPING_VALUES)), DAMPING_VALUES)
axes[0].set(xlabel='lambda (TF-IDF share)', ylabel='damping d',
            title='Macro-F1 trên train')
for row_index in range(len(DAMPING_VALUES)):
    for column_index in range(len(LAMBDA_VALUES)):
        axes[0].text(column_index, row_index, f'{f1_grid[row_index,column_index]:.3f}',
                     ha='center', va='center', fontsize=8)
fig.colorbar(image, ax=axes[0], label='Macro-F1')

for edge_lambda in LAMBDA_VALUES:
    rows = [row for row in train_summary if row['edge_lambda'] == edge_lambda]
    axes[1].plot([row['damping'] for row in rows],
                 [row['macro_f1'] for row in rows], marker='o',
                 label=f'lambda={edge_lambda:.1f}')
axes[1].set(xlabel='damping d', ylabel='Macro-F1',
            title='Ảnh hưởng của damping trên train')
axes[1].legend(fontsize=8, ncol=2)
axes[1].grid(alpha=0.25)
fig.tight_layout()
chart_path = OUTPUT_DIR / 'train-d-lambda-sweep.png'
fig.savefig(chart_path, dpi=180, bbox_inches='tight')
plt.show()
print('Chart:', chart_path)"""),
    markdown("""## 5. Kiểm tra độ chắc chắn so với baseline

Macro-F1 cao hơn chưa đủ để “chứng minh” cải tiến. Ta so sánh F1 theo từng topic
và bootstrap khoảng tin cậy 95% cho chênh lệch trung bình. Nếu CI chứa 0 thì
kết luận phù hợp là **chưa đủ bằng chứng**, không phải cấu hình mới chắc chắn tốt."""),
    code("""def rows_for(detail, damping, edge_lambda):
    return {
        row['topic']: row
        for row in detail
        if row['damping'] == damping and row['edge_lambda'] == edge_lambda
    }


def paired_report(detail, candidate, baseline, samples=2000):
    candidate_rows = rows_for(detail, candidate['damping'], candidate['edge_lambda'])
    baseline_rows = rows_for(detail, baseline['damping'], baseline['edge_lambda'])
    topics = sorted(candidate_rows.keys() & baseline_rows.keys())
    deltas = [candidate_rows[name]['f1'] - baseline_rows[name]['f1'] for name in topics]
    wins = sum(delta > 0 for delta in deltas)
    ties = sum(math.isclose(delta, 0.0, abs_tol=1e-12) for delta in deltas)
    losses = sum(delta < 0 for delta in deltas)
    generator = random.Random(RANDOM_STATE)
    bootstrap_means = []
    for _ in range(samples):
        sample = [deltas[generator.randrange(len(deltas))] for _ in deltas]
        bootstrap_means.append(statistics.fmean(sample))
    bootstrap_means.sort()
    return {
        'topics': len(topics),
        'mean_f1_delta': statistics.fmean(deltas),
        'ci95_low': bootstrap_means[int(0.025 * samples)],
        'ci95_high': bootstrap_means[int(0.975 * samples)],
        'wins': wins,
        'ties': ties,
        'losses': losses,
    }


train_paired = paired_report(train_detail, best_train, baseline_train)
print('Selected vs baseline trên train:', train_paired)
if train_paired['ci95_low'] > 0:
    print('Kết luận train: cải tiến có bằng chứng dương trong bootstrap 95%.')
elif train_paired['ci95_high'] < 0:
    print('Kết luận train: cấu hình mới kém baseline.')
else:
    print('Kết luận train: CI chứa 0, chưa đủ bằng chứng cấu hình mới tốt hơn.')"""),
    markdown("""## 6. Khóa cấu hình và đánh giá test một lần

Cell này không tìm lại tham số trên test. Nó chỉ chạy baseline và cấu hình đã
chọn từ train, giúp tránh rò rỉ dữ liệu."""),
    code("""locked_d = best_train['damping']
locked_lambda = best_train['edge_lambda']
# Chỉ đánh giá hai cặp cần thiết, không dùng tích Descartes để tránh nhìn thêm test.
test_detail = []
test_configurations = list(dict.fromkeys([(0.85, 1.0), (locked_d, locked_lambda)]))
for damping, edge_lambda in test_configurations:
    for topic in test_topics:
        test_detail.append(evaluate_topic(topic, damping, edge_lambda))
test_summary = aggregate(test_detail)

baseline_test = next(row for row in test_summary
                     if row['damping'] == 0.85 and row['edge_lambda'] == 1.0)
selected_test = next(row for row in test_summary
                     if row['damping'] == locked_d and row['edge_lambda'] == locked_lambda)
test_paired = paired_report(test_detail, selected_test, baseline_test)

print('Locked config:', {'damping': locked_d, 'edge_lambda': locked_lambda})
print('Baseline test:', baseline_test)
print('Selected test:', selected_test)
print('Selected vs baseline trên test:', test_paired)"""),
    markdown("""## 7. Xuất bằng chứng và kết luận tự động

Các CSV lưu cả mức topic và mức tổng hợp. JSON ghi rõ cấu hình được khóa và
không tuyên bố `lambda=0.6` tốt nếu dữ liệu không chọn nó."""),
    code("""def write_csv(path, rows):
    if not rows:
        return
    with path.open('w', encoding='utf-8', newline='') as output_file:
        writer = csv.DictWriter(output_file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


write_csv(OUTPUT_DIR / 'train-detail.csv', train_detail)
write_csv(OUTPUT_DIR / 'train-summary.csv', train_summary)
write_csv(OUTPUT_DIR / 'test-detail.csv', test_detail)
write_csv(OUTPUT_DIR / 'test-summary.csv', test_summary)

evidence = {
    'method': 'lambda * TF-IDF cosine + (1-lambda) * clipped LSA cosine',
    'selection_metric': 'train macro F1; precision tie-break',
    'similarity_threshold': SIMILARITY_THRESHOLD,
    'top_k': TOP_K,
    'use_mmr': False,
    'selected_on_train': {'damping': locked_d, 'edge_lambda': locked_lambda},
    'train_baseline': baseline_train,
    'train_selected': best_train,
    'train_paired_bootstrap': train_paired,
    'test_baseline': baseline_test,
    'test_selected': selected_test,
    'test_paired_bootstrap': test_paired,
    'lambda_0_6_best_train': lambda_06_best,
}
(OUTPUT_DIR / 'recommended-edge-weight-config.json').write_text(
    json.dumps(evidence, indent=2), encoding='utf-8'
)

print(f"d được chọn từ train: {locked_d:.2f}")
print(f"lambda được chọn từ train: {locked_lambda:.1f}")
if math.isclose(locked_lambda, 0.6):
    print('lambda=0.6 được chọn vì có Macro-F1 train tốt nhất theo quy tắc đã định.')
else:
    print('lambda=0.6 KHÔNG được dữ liệu chọn; không nên khẳng định 0.6 là tối ưu.')

delta = selected_test['macro_f1'] - baseline_test['macro_f1']
print(f"Chênh lệch Macro-F1 test so với baseline: {delta:+.4f}")
if test_paired['ci95_low'] > 0:
    print('Kết luận: cải tiến tốt hơn baseline trên test trong bootstrap 95%.')
elif test_paired['ci95_high'] < 0:
    print('Kết luận: cải tiến kém baseline trên test.')
else:
    print('Kết luận: chưa đủ bằng chứng thống kê rằng cải tiến tốt hơn baseline.')
print('Artifacts:', OUTPUT_DIR)"""),
    markdown("""## Takeaways

Sau khi chạy toàn bộ notebook, dùng các output ở trên để viết kết luận:

1. Không chọn `d=0.85` chỉ vì đây là giá trị phổ biến; chọn `d` có Macro-F1
   train tốt và kiểm tra số vòng lặp hội tụ.
2. Không chọn `lambda=0.6` theo trực giác. Chỉ bảo vệ giá trị này nếu nó thắng
   theo quy tắc train đã khóa và kết quả paired comparison không mâu thuẫn.
3. Test chỉ là bằng chứng khả năng khái quát, không được dùng để đổi tham số.
4. MMR nằm ngoài thí nghiệm này và luôn tắt.
5. LSA là cải tiến nhẹ. Nếu thay bằng Sentence-BERT trong tương lai, phải chạy
   lại toàn bộ sweep vì ý nghĩa và phân phối cosine đã thay đổi."""),
]

notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3.14"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

NOTEBOOK_PATH.write_text(json.dumps(notebook, indent=1), encoding="utf-8")
print(NOTEBOOK_PATH)
