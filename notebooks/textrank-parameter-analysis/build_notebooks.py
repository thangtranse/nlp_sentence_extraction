from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook


NOTEBOOK_DIR = Path(__file__).resolve().parent

SETUP = """import sys
from pathlib import Path

import matplotlib.pyplot as plt

PROJECT_ROOT = Path.cwd()
if not (PROJECT_ROOT / 'data').is_dir():
    for candidate in [PROJECT_ROOT, *PROJECT_ROOT.parents]:
        if (candidate / 'data' / 'DUC_TEXT').is_dir():
            PROJECT_ROOT = candidate
            break

NOTEBOOK_DIR = PROJECT_ROOT / 'notebooks' / 'textrank-parameter-analysis'
if str(NOTEBOOK_DIR) not in sys.path:
    sys.path.insert(0, str(NOTEBOOK_DIR))

from experiment_utils import *

TRAIN_DIR = PROJECT_ROOT / 'data' / 'DUC_TEXT' / 'train'
TEST_DIR = PROJECT_ROOT / 'data' / 'DUC_TEXT' / 'test'
REFERENCE_DIR = PROJECT_ROOT / 'data' / 'DUC_SUM'
OUTPUT_DIR = PROJECT_ROOT / 'data' / 'output' / 'textrank-parameter-analysis'
CSV_DIR = OUTPUT_DIR / 'csv'
CHART_DIR = OUTPUT_DIR / 'charts'
CSV_DIR.mkdir(parents=True, exist_ok=True)
CHART_DIR.mkdir(parents=True, exist_ok=True)

plt.style.use('seaborn-v0_8-whitegrid')
print(f'Project: {PROJECT_ROOT}')
print(f'Output : {OUTPUT_DIR}')"""


def markdown(cell_id, source):
    cell = new_markdown_cell(source)
    cell.id = cell_id
    return cell


def code(cell_id, source):
    cell = new_code_cell(source)
    cell.id = cell_id
    return cell


def write_notebook(name, title, step_cells):
    cells = [
        markdown("title", f"# {title}\n\n## Goal\n\n{step_cells['goal']}"),
        markdown("setup-heading", "## Setup\n\nKhởi tạo đường dẫn, module thuật toán và thư mục artifact."),
        code("setup", SETUP),
        markdown("steps-heading", "## Steps"),
        *step_cells["steps"],
        markdown("checks-heading", "## Checks\n\nCác assertion dưới đây bảo đảm artifact và dữ liệu của notebook đầy đủ."),
        code("checks", step_cells["checks"]),
        markdown("takeaways-heading", "## Takeaways"),
        code("takeaways", step_cells["takeaways"]),
    ]
    notebook = new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.9"},
        },
    )
    nbformat.write(notebook, NOTEBOOK_DIR / name)


def build_01():
    write_notebook(
        "01-dataset-and-baseline.ipynb",
        "01 — DUC dataset audit and TextRank baseline",
        {
            "goal": "Kiểm tra train/test/reference và đo baseline hiện tại trước khi tối ưu tham số.",
            "steps": [
                markdown("audit-heading", "### 1. Audit dataset"),
                code("audit", """train_paths = sorted(path for path in TRAIN_DIR.iterdir() if path.is_file())
test_paths = sorted(path for path in TEST_DIR.iterdir() if path.is_file())
dataset_rows = []
for split, paths in [('train', train_paths), ('test', test_paths)]:
    for topic_path in paths:
        reference_path = REFERENCE_DIR / topic_path.name
        assert reference_path.is_file(), f'Missing reference: {topic_path.name}'
        input_sentences = read_topic(topic_path)
        reference_sentences = read_topic(reference_path)
        shortest = sorted(len(sentence.content.split()) for sentence in reference_sentences)
        used = 0
        ceiling = 0
        for word_count in shortest:
            if used + word_count > 100:
                continue
            used += word_count
            ceiling += 1
        dataset_rows.append({
            'split': split, 'topic': topic_path.name,
            'input_sentences': len(input_sentences),
            'input_words': sum(len(sentence.content.split()) for sentence in input_sentences),
            'reference_sentences': len({sentence.key for sentence in reference_sentences}),
            'reference_words': sum(len(sentence.content.split()) for sentence in reference_sentences),
            'reference_sentence_ceiling_100_words': ceiling,
        })
write_csv(CSV_DIR / '01-dataset-summary.csv', dataset_rows, list(dataset_rows[0]))
print(f'Train topics: {len(train_paths)} | Test topics: {len(test_paths)}')"""),
                markdown("baseline-heading", "### 2. Run baseline"),
                code("baseline", """BASELINE = TextRankConfig()
baseline_rows = evaluate_config(TRAIN_DIR, REFERENCE_DIR, BASELINE, 'train')
baseline_summary = aggregate_rows(baseline_rows)
for row in baseline_rows:
    row['config_id'] = config_id(BASELINE)
write_csv(CSV_DIR / '01-baseline-topic-metrics.csv', baseline_rows, DETAIL_FIELDS)
print({key: round(value, 4) if isinstance(value, float) else value
       for key, value in baseline_summary.items()})"""),
                markdown("baseline-chart-heading", "### 3. Visualize baseline and reference size"),
                code("baseline-charts", """train_reference_counts = [row['reference_sentences'] for row in dataset_rows if row['split'] == 'train']
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.hist(train_reference_counts, bins=10, edgecolor='black')
ax.set(title='Reference sentence distribution — train', xlabel='Reference sentences per topic', ylabel='Topics')
fig.savefig(CHART_DIR / '01-reference-sentence-distribution.png', dpi=160, bbox_inches='tight')
plt.show()

fig, ax = plt.subplots(figsize=(7, 4.5))
names = ['Precision', 'Recall', 'F1']
values = [baseline_summary['macro_precision'], baseline_summary['macro_recall'], baseline_summary['macro_f1']]
bars = ax.bar(names, values, color=['#4c78a8', '#f58518', '#54a24b'])
ax.set(title='Baseline exact-sentence quality — train', ylabel='Macro score', ylim=(0, 1))
ax.bar_label(bars, fmt='%.3f')
fig.savefig(CHART_DIR / '01-baseline-metrics.png', dpi=160, bbox_inches='tight')
plt.show()"""),
            ],
            "checks": """assert len(train_paths) == 50
assert len(test_paths) == 9
assert len(baseline_rows) == 50
for path in [CSV_DIR / '01-dataset-summary.csv', CSV_DIR / '01-baseline-topic-metrics.csv',
             CHART_DIR / '01-reference-sentence-distribution.png', CHART_DIR / '01-baseline-metrics.png']:
    assert path.is_file() and path.stat().st_size > 0, path
print('All dataset and baseline checks passed.')""",
            "takeaways": """print(f\"Baseline macro Precision={baseline_summary['macro_precision']:.4f}, \"
      f\"F1={baseline_summary['macro_f1']:.4f}.\")
print(f\"Mean word-budget utilization={baseline_summary['mean_budget_utilization']:.3f}.\")
print('Recall is interpreted with care because DUC_SUM is longer than the 100-word prediction budget.')""",
        },
    )


def build_02():
    write_notebook(
        "02-similarity-threshold.ipynb",
        "02 — Similarity threshold analysis",
        {
            "goal": "Đo ảnh hưởng của threshold lên chất lượng exact-sentence và sức khỏe đồ thị.",
            "steps": [
                markdown("distribution-heading", "### 1. Inspect cosine-similarity distribution"),
                code("distribution", """similarity_values = []
for topic_path in sorted(path for path in TRAIN_DIR.iterdir() if path.is_file()):
    sentences = read_topic(topic_path)
    vectors = calculate_tfidf_vectors(sentences)
    _, similarities = build_sentence_graph(vectors, 0.0)
    for left in range(len(similarities)):
        similarity_values.extend(similarities[left][left + 1:])

sorted_similarities = sorted(similarity_values)
def percentile(values, ratio):
    return values[round((len(values) - 1) * ratio)]
percentiles = {name: percentile(sorted_similarities, ratio)
               for name, ratio in [('P50', .50), ('P75', .75), ('P90', .90), ('P95', .95)]}
print(percentiles)
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.hist(similarity_values, bins=50, edgecolor='none')
ax.set(title='All train sentence-pair cosine similarities', xlabel='Cosine similarity', ylabel='Sentence pairs')
fig.savefig(CHART_DIR / '02-similarity-distribution.png', dpi=160, bbox_inches='tight')
plt.show()"""),
                markdown("sweep-heading", "### 2. Sweep thresholds"),
                code("sweep", """THRESHOLDS = [0.00, 0.02, 0.05, 0.08, 0.10, 0.12, 0.15, 0.20, 0.25, 0.30]
configs = [TextRankConfig(similarity_threshold=value) for value in THRESHOLDS]
threshold_details, threshold_summaries = run_sweep(TRAIN_DIR, REFERENCE_DIR, configs, 'train')
ranked_thresholds = rank_configurations(threshold_summaries, required_topics=50)
write_csv(CSV_DIR / '02-threshold-topic-metrics.csv', threshold_details, DETAIL_FIELDS)
write_csv(CSV_DIR / '02-threshold-summary.csv', ranked_thresholds, SUMMARY_FIELDS)
best_threshold_row = ranked_thresholds[0]
print('Best threshold:', best_threshold_row['similarity_threshold'])"""),
                markdown("quality-heading", "### 3. Plot quality and graph health"),
                code("quality-charts", """ordered = sorted(threshold_summaries, key=lambda row: row['similarity_threshold'])
x = [row['similarity_threshold'] for row in ordered]
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.plot(x, [row['macro_precision'] for row in ordered], marker='o', label='Precision')
ax.plot(x, [row['macro_recall'] for row in ordered], marker='o', label='Recall')
ax.plot(x, [row['macro_f1'] for row in ordered], marker='o', label='F1')
ax.axvline(best_threshold_row['similarity_threshold'], color='black', linestyle='--', alpha=.5)
ax.set(title='Exact-sentence quality by threshold', xlabel='Similarity threshold', ylabel='Macro score', ylim=(0, 1))
ax.legend()
fig.savefig(CHART_DIR / '02-threshold-quality.png', dpi=160, bbox_inches='tight')
plt.show()

fig, axes = plt.subplots(2, 2, figsize=(10, 7))
series = [('mean_density', 'Density'), ('mean_isolated_ratio', 'Isolated ratio'),
          ('mean_average_degree', 'Average degree'), ('mean_connected_components', 'Components')]
for ax, (field, label) in zip(axes.flat, series):
    ax.plot(x, [row[field] for row in ordered], marker='o')
    ax.set(xlabel='Threshold', ylabel=label)
fig.suptitle('Graph health by similarity threshold')
fig.tight_layout()
fig.savefig(CHART_DIR / '02-threshold-graph-health.png', dpi=160, bbox_inches='tight')
plt.show()"""),
            ],
            "checks": """assert len(threshold_summaries) == len(THRESHOLDS)
assert all(row['converged_topics'] == 50 for row in threshold_summaries)
for path in [CSV_DIR / '02-threshold-summary.csv', CSV_DIR / '02-threshold-topic-metrics.csv',
             CHART_DIR / '02-similarity-distribution.png', CHART_DIR / '02-threshold-quality.png',
             CHART_DIR / '02-threshold-graph-health.png']:
    assert path.is_file() and path.stat().st_size > 0, path
print('All threshold checks passed.')""",
            "takeaways": """print(f\"Best tested threshold={float(best_threshold_row['similarity_threshold']):.2f}, \"
      f\"Precision={float(best_threshold_row['macro_precision']):.4f}, \"
      f\"F1={float(best_threshold_row['macro_f1']):.4f}.\")
print('This is the best value inside the tested threshold grid, not a universal optimum.')""",
        },
    )


def build_03():
    write_notebook(
        "03-pagerank-parameters.ipynb",
        "03 — PageRank parameter analysis",
        {
            "goal": "Đánh giá damping, tolerance và giới hạn vòng lặp sau khi chọn threshold trên train.",
            "steps": [
                markdown("load-heading", "### 1. Load the selected threshold"),
                code("load-threshold", """threshold_rows = read_csv(CSV_DIR / '02-threshold-summary.csv')
best_threshold_row = rank_configurations(threshold_rows, required_topics=50)[0]
BEST_THRESHOLD = float(best_threshold_row['similarity_threshold'])
print('Using train-selected threshold:', BEST_THRESHOLD)"""),
                markdown("pagerank-sweep-heading", "### 2. Sweep PageRank parameters"),
                code("pagerank-sweep", """DAMPINGS = [0.70, 0.80, 0.85, 0.90, 0.95]
TOLERANCES = [1e-4, 1e-6, 1e-8]
MAX_ITERATIONS = [100, 300, 1000]
configs = [TextRankConfig(similarity_threshold=BEST_THRESHOLD,
                          pagerank_damping=damping,
                          pagerank_tolerance=tolerance,
                          pagerank_max_iterations=max_iterations)
           for damping in DAMPINGS for tolerance in TOLERANCES for max_iterations in MAX_ITERATIONS]
pagerank_details, pagerank_summaries = run_sweep(TRAIN_DIR, REFERENCE_DIR, configs, 'train')
ranked_pagerank = rank_configurations(pagerank_summaries, required_topics=50)
write_csv(CSV_DIR / '03-pagerank-topic-metrics.csv', pagerank_details, DETAIL_FIELDS)
write_csv(CSV_DIR / '03-pagerank-summary.csv', ranked_pagerank, SUMMARY_FIELDS)
best_pagerank_row = ranked_pagerank[0]
print('Best PageRank config:', best_pagerank_row['config_id'])"""),
                markdown("pagerank-chart-heading", "### 3. Plot quality and convergence"),
                code("pagerank-charts", """converged = [row for row in pagerank_summaries if row['converged_topics'] == 50]
fig, ax = plt.subplots(figsize=(9, 5))
for damping in DAMPINGS:
    rows = sorted([row for row in converged
                   if row['pagerank_damping'] == damping and row['pagerank_max_iterations'] == 1000],
                  key=lambda row: row['pagerank_tolerance'])
    ax.plot([str(row['pagerank_tolerance']) for row in rows],
            [row['macro_precision'] for row in rows], marker='o', label=f'd={damping}')
ax.set(title='PageRank Precision by damping and tolerance', xlabel='Tolerance', ylabel='Macro Precision', ylim=(0, 1))
ax.legend(ncol=2)
fig.savefig(CHART_DIR / '03-pagerank-quality.png', dpi=160, bbox_inches='tight')
plt.show()

fig, ax = plt.subplots(figsize=(9, 5))
labels = [row['config_id'] for row in ranked_pagerank[:10]]
ax.scatter([row['mean_pagerank_iterations'] for row in ranked_pagerank[:10]],
           [row['mean_runtime_seconds'] for row in ranked_pagerank[:10]])
for label, row in zip(labels, ranked_pagerank[:10]):
    ax.annotate(str(row['rank']), (row['mean_pagerank_iterations'], row['mean_runtime_seconds']))
ax.set(title='Top-10 PageRank configs: convergence cost', xlabel='Mean iterations', ylabel='Mean seconds/topic')
fig.savefig(CHART_DIR / '03-pagerank-convergence.png', dpi=160, bbox_inches='tight')
plt.show()"""),
            ],
            "checks": """assert len(pagerank_summaries) == 45
assert ranked_pagerank
for path in [CSV_DIR / '03-pagerank-summary.csv', CSV_DIR / '03-pagerank-topic-metrics.csv',
             CHART_DIR / '03-pagerank-quality.png', CHART_DIR / '03-pagerank-convergence.png']:
    assert path.is_file() and path.stat().st_size > 0, path
print(f'Converged configs: {len(ranked_pagerank)}/45')""",
            "takeaways": """print(f\"Best converged PageRank setting: damping={best_pagerank_row['pagerank_damping']}, \"
      f\"tolerance={best_pagerank_row['pagerank_tolerance']}, \"
      f\"max_iterations={best_pagerank_row['pagerank_max_iterations']}.\")
print(f\"Precision={float(best_pagerank_row['macro_precision']):.4f}; \"
      f\"mean iterations={float(best_pagerank_row['mean_pagerank_iterations']):.1f}.\")""",
        },
    )


def build_04():
    write_notebook(
        "04-mmr-parameters.ipynb",
        "04 — MMR parameter analysis",
        {
            "goal": "So sánh tắt/bật MMR và lambda theo Precision, F1 và redundancy.",
            "steps": [
                markdown("load-pr-heading", "### 1. Load train-selected threshold and PageRank"),
                code("load-pr", """threshold_row = rank_configurations(read_csv(CSV_DIR / '02-threshold-summary.csv'), 50)[0]
pagerank_row = rank_configurations(read_csv(CSV_DIR / '03-pagerank-summary.csv'), 50)[0]
base = config_from_row(pagerank_row)
print('Base config:', config_id(base))"""),
                markdown("mmr-sweep-heading", "### 2. Sweep MMR"),
                code("mmr-sweep", """MMR_LAMBDAS = [0.30, 0.50, 0.70, 0.90, 1.00]
configs = [TextRankConfig(base.similarity_threshold, base.pagerank_damping,
                          base.pagerank_tolerance, base.pagerank_max_iterations,
                          100, False, 0.0)]
configs += [TextRankConfig(base.similarity_threshold, base.pagerank_damping,
                           base.pagerank_tolerance, base.pagerank_max_iterations,
                           100, True, value) for value in MMR_LAMBDAS]
mmr_details, mmr_summaries = run_sweep(TRAIN_DIR, REFERENCE_DIR, configs, 'train')
ranked_mmr = rank_configurations(mmr_summaries, required_topics=50)
write_csv(CSV_DIR / '04-mmr-topic-metrics.csv', mmr_details, DETAIL_FIELDS)
write_csv(CSV_DIR / '04-mmr-summary.csv', ranked_mmr, SUMMARY_FIELDS)
best_mmr_row = ranked_mmr[0]
print('Best MMR option:', best_mmr_row['config_id'])"""),
                markdown("mmr-chart-heading", "### 3. Plot quality and redundancy"),
                code("mmr-charts", """ordered = sorted(mmr_summaries, key=lambda row: (-int(bool(row['use_mmr'])), row['mmr_lambda'] or -1))
labels = ['off' if not row['use_mmr'] else f\"λ={row['mmr_lambda']:.1f}\" for row in ordered]
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.plot(labels, [row['macro_precision'] for row in ordered], marker='o', label='Precision')
ax.plot(labels, [row['macro_f1'] for row in ordered], marker='o', label='F1')
ax.set(title='MMR quality', xlabel='MMR setting', ylabel='Macro score', ylim=(0, 1))
ax.legend()
fig.savefig(CHART_DIR / '04-mmr-quality.png', dpi=160, bbox_inches='tight')
plt.show()

fig, ax = plt.subplots(figsize=(8, 4.5))
ax.plot(labels, [row['mean_redundancy'] for row in ordered], marker='o', label='Mean')
ax.plot(labels, [row['max_redundancy'] for row in ordered], marker='o', label='Maximum')
ax.set(title='Selected-sentence redundancy', xlabel='MMR setting', ylabel='Cosine similarity', ylim=(0, 1))
ax.legend()
fig.savefig(CHART_DIR / '04-mmr-redundancy.png', dpi=160, bbox_inches='tight')
plt.show()"""),
            ],
            "checks": """assert len(mmr_summaries) == 6
assert sum(not row['use_mmr'] for row in mmr_summaries) == 1
for path in [CSV_DIR / '04-mmr-summary.csv', CSV_DIR / '04-mmr-topic-metrics.csv',
             CHART_DIR / '04-mmr-quality.png', CHART_DIR / '04-mmr-redundancy.png']:
    assert path.is_file() and path.stat().st_size > 0, path
print('All MMR checks passed.')""",
            "takeaways": """label = 'off' if not best_mmr_row['use_mmr'] else f\"lambda={best_mmr_row['mmr_lambda']}\"
print(f\"Best tested MMR setting={label}, Precision={float(best_mmr_row['macro_precision']):.4f}, \"
      f\"F1={float(best_mmr_row['macro_f1']):.4f}, \"
      f\"mean redundancy={float(best_mmr_row['mean_redundancy']):.4f}.\")""",
        },
    )


def build_05():
    write_notebook(
        "05-final-configuration.ipynb",
        "05 — Final configuration selection and test evaluation",
        {
            "goal": "Chạy local grid trên train, khóa đúng một cấu hình rồi đánh giá một lần trên test.",
            "steps": [
                markdown("candidate-heading", "### 1. Build local candidate grid from train analyses"),
                code("candidates", """threshold_ranked = rank_configurations(read_csv(CSV_DIR / '02-threshold-summary.csv'), 50)
pagerank_ranked = rank_configurations(read_csv(CSV_DIR / '03-pagerank-summary.csv'), 50)
mmr_ranked = rank_configurations(read_csv(CSV_DIR / '04-mmr-summary.csv'), 50)

thresholds = [float(value) for value in top_unique_values(threshold_ranked, 'similarity_threshold', 3)]
pagerank_candidates = [(float(row['pagerank_damping']), float(row['pagerank_tolerance']),
                        int(float(row['pagerank_max_iterations']))) for row in pagerank_ranked[:2]]
mmr_candidates = []
for row in mmr_ranked:
    enabled = str(row['use_mmr']).lower() == 'true'
    candidate = (enabled, float(row['mmr_lambda']) if enabled else 0.0)
    if candidate not in mmr_candidates:
        mmr_candidates.append(candidate)
    if len(mmr_candidates) == 4:
        break
local_configs = build_local_grid(thresholds, pagerank_candidates, mmr_candidates)
print(f'Local grid: {len(local_configs)} unique configurations')"""),
                markdown("train-grid-heading", "### 2. Select and lock one configuration on train"),
                code("train-grid", """local_details, local_summaries = run_sweep(TRAIN_DIR, REFERENCE_DIR, local_configs, 'train')
ranked_train = rank_configurations(local_summaries, required_topics=50)
assert ranked_train, 'No configuration converged on every train topic'
recommended_train_row = ranked_train[0]
recommended_config = config_from_row(recommended_train_row)
write_csv(CSV_DIR / '05-local-grid-summary.csv', ranked_train, SUMMARY_FIELDS)
write_csv(CSV_DIR / '05-final-train-topic-metrics.csv',
          [row for row in local_details if row['config_id'] == recommended_train_row['config_id']], DETAIL_FIELDS)
print('Locked config:', config_id(recommended_config))"""),
                markdown("test-heading", "### 3. Evaluate the locked configuration once on test"),
                code("test-once", """test_rows = evaluate_config(TEST_DIR, REFERENCE_DIR, recommended_config, 'test')
for row in test_rows:
    row['config_id'] = config_id(recommended_config)
test_summary = aggregate_rows(test_rows)
write_csv(CSV_DIR / '05-final-test-topic-metrics.csv', test_rows, DETAIL_FIELDS)
recommendation = {
    'selection_rule': ['macro_precision_desc', 'macro_f1_desc',
                       'mean_redundancy_asc', 'mean_runtime_seconds_asc'],
    'tested_local_configurations': len(local_configs),
    'config': config_fields(recommended_config),
    'config_id': config_id(recommended_config),
    'train': {key: value for key, value in recommended_train_row.items()
              if key.startswith('macro_') or key.startswith('mean_') or key in ('eligible_topics', 'converged_topics')},
    'test': test_summary,
    'limitation': 'Exact (docid, num) match does not measure paraphrase or semantic equivalence.',
}
write_json(OUTPUT_DIR / '05-recommended-config.json', recommendation)
print('Test evaluation completed after configuration lock.')"""),
                markdown("final-chart-heading", "### 4. Compare top configurations and train/test"),
                code("final-charts", """top = ranked_train[:10]
fig, ax = plt.subplots(figsize=(10, 5))
ax.bar([str(row['rank']) for row in top], [row['macro_precision'] for row in top])
ax.set(title='Top local-grid configurations on train', xlabel='Train rank', ylabel='Macro Precision', ylim=(0, 1))
fig.savefig(CHART_DIR / '05-top-configurations.png', dpi=160, bbox_inches='tight')
plt.show()

fig, ax = plt.subplots(figsize=(7, 4.5))
labels = ['Precision', 'Recall', 'F1']
train_values = [recommended_train_row['macro_precision'], recommended_train_row['macro_recall'], recommended_train_row['macro_f1']]
test_values = [test_summary['macro_precision'], test_summary['macro_recall'], test_summary['macro_f1']]
x = range(len(labels))
ax.bar([value - .2 for value in x], train_values, width=.4, label='Train')
ax.bar([value + .2 for value in x], test_values, width=.4, label='Test')
ax.set_xticks(list(x), labels)
ax.set(title='Locked configuration: train vs test', ylabel='Macro score', ylim=(0, 1))
ax.legend()
fig.savefig(CHART_DIR / '05-train-vs-test.png', dpi=160, bbox_inches='tight')
plt.show()"""),
            ],
            "checks": """assert len({row['topic'] for row in local_details
            if row['config_id'] == recommended_train_row['config_id']}) == 50
assert len({row['topic'] for row in test_rows}) == 9
for path in [CSV_DIR / '05-local-grid-summary.csv', CSV_DIR / '05-final-train-topic-metrics.csv',
             CSV_DIR / '05-final-test-topic-metrics.csv', CHART_DIR / '05-top-configurations.png',
             CHART_DIR / '05-train-vs-test.png', OUTPUT_DIR / '05-recommended-config.json']:
    assert path.is_file() and path.stat().st_size > 0, path
print('Final train/test separation and artifact checks passed.')""",
            "takeaways": """train_precision = float(recommended_train_row['macro_precision'])
test_precision = float(test_summary['macro_precision'])
print('Recommended config:', config_fields(recommended_config))
print(f'Train Precision={train_precision:.4f}, F1={float(recommended_train_row[\"macro_f1\"]):.4f}')
print(f'Test  Precision={test_precision:.4f}, F1={float(test_summary[\"macro_f1\"]):.4f}')
print(f'Precision train-test gap={train_precision - test_precision:+.4f}')
print('Conclusion applies only to the tested grid and exact sentence matching.')""",
        },
    )


def main():
    build_01()
    build_02()
    build_03()
    build_04()
    build_05()
    print(f"Generated five notebooks in {NOTEBOOK_DIR}")


if __name__ == "__main__":
    main()
