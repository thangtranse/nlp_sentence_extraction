from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from evaluation.main import calculate_metrics, read_sentences
from experiment_utils import (
    TextRankConfig,
    aggregate_rows,
    calculate_graph_metrics,
    evaluate_config,
)
from nlp_practice.pagerank import calculate_pagerank, rank_sentences_by_pagerank
from nlp_practice.preprocessing import read_topic
from nlp_practice.selection import select_sentences
from nlp_practice.similarity import build_similarity_matrix
from nlp_practice.tfidf import build_tfidf_vectors

THRESHOLDS = [
    0.0,
    0.0025,
    0.005,
    0.0075,
    0.01,
    0.0125,
    0.015,
    0.0175,
    0.02,
    0.0225,
    0.025,
    0.0275,
    0.03,
]
SELECTED_THRESHOLD = 0.0275
TOP_K = 15

OUTPUT_DIR = ROOT / "data" / "output" / "fine-threshold-sweep"
CSV_DIR = OUTPUT_DIR / "csv"
CHART_DIR = OUTPUT_DIR / "charts"


def mean(values) -> float:
    values = list(values)
    return statistics.fmean(values) if values else 0.0


def graph_from_matrix(matrix: list[list[float]], threshold: float):
    graph = {index: {} for index in range(len(matrix))}
    for left in range(len(matrix)):
        for right in range(left + 1, len(matrix)):
            weight = matrix[left][right]
            # A zero-weight entry is not a meaningful TextRank edge.
            if weight > 0.0 and weight >= threshold:
                graph[left][right] = weight
                graph[right][left] = weight
    return graph


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_top_k_sweep() -> list[dict]:
    input_dir = ROOT / "data" / "DUC_TEXT" / "train"
    reference_dir = ROOT / "data" / "DUC_SUM"
    topics = []
    for topic_path in sorted(input_dir.iterdir()):
        reference_path = reference_dir / topic_path.name
        if not topic_path.is_file() or not reference_path.is_file():
            continue
        references = read_sentences(reference_path)
        if not references:
            continue
        sentences = read_topic(topic_path)
        vectors = build_tfidf_vectors(sentences)
        similarities = build_similarity_matrix(vectors, threshold=0.0)
        topics.append((sentences, similarities, references))

    summaries = []
    for threshold in THRESHOLDS:
        metrics = []
        graph_metrics = []
        for sentences, similarities, references in topics:
            graph = graph_from_matrix(similarities, threshold)
            scores, _ = calculate_pagerank(
                graph, damping=0.85, tolerance=1e-8, max_iterations=1000
            )
            ranked = rank_sentences_by_pagerank(sentences, scores, top_k=TOP_K)
            predictions = {
                " ".join(sentence["content"].split()).casefold() for sentence in ranked
            }
            metrics.append(calculate_metrics(predictions, references))
            graph_metrics.append(calculate_graph_metrics(graph))

        summaries.append(
            {
                "threshold": threshold,
                "eligible_topics": len(metrics),
                "macro_precision": mean(row["precision"] for row in metrics),
                "macro_recall": mean(row["recall"] for row in metrics),
                "macro_f1": mean(row["f1"] for row in metrics),
                "zero_f1_topics": sum(row["f1"] == 0.0 for row in metrics),
                "mean_density": mean(row.density for row in graph_metrics),
                "mean_isolated_ratio": mean(
                    row.isolated_ratio for row in graph_metrics
                ),
                "mean_average_degree": mean(
                    row.average_degree for row in graph_metrics
                ),
                "mean_connected_components": mean(
                    row.connected_components for row in graph_metrics
                ),
            }
        )
    return summaries


def run_package_mmr_sweep(split: str) -> list[dict]:
    input_dir = ROOT / "data" / "DUC_TEXT" / split
    reference_dir = ROOT / "data" / "DUC_SUM"
    topics = []
    for topic_path in sorted(input_dir.iterdir()):
        reference_path = reference_dir / topic_path.name
        if not topic_path.is_file() or not reference_path.is_file():
            continue
        references = read_sentences(reference_path)
        if not references:
            continue
        sentences = read_topic(topic_path)
        vectors = build_tfidf_vectors(sentences)
        similarities = build_similarity_matrix(vectors, threshold=0.0)
        topics.append((sentences, similarities, references))

    summaries = []
    for threshold in THRESHOLDS:
        metrics = []
        graph_metrics = []
        word_counts = []
        for sentences, similarities, references in topics:
            graph = graph_from_matrix(similarities, threshold)
            scores, _ = calculate_pagerank(
                graph, damping=0.85, tolerance=1e-8, max_iterations=300
            )
            selected = select_sentences(
                sentences=sentences,
                pagerank_scores=scores,
                similarities=similarities,
                max_summary_words=100,
                use_mmr=True,
                mmr_lambda=0.70,
            )
            predictions = {
                " ".join(sentence["content"].split()).casefold()
                for sentence in selected
            }
            metrics.append(calculate_metrics(predictions, references))
            graph_metrics.append(calculate_graph_metrics(graph))
            word_counts.append(
                sum(len(sentence["content"].split()) for sentence in selected)
            )

        summaries.append(
            {
                "threshold": threshold,
                "eligible_topics": len(metrics),
                "macro_precision": mean(row["precision"] for row in metrics),
                "macro_recall": mean(row["recall"] for row in metrics),
                "macro_f1": mean(row["f1"] for row in metrics),
                "zero_f1_topics": sum(row["f1"] == 0.0 for row in metrics),
                "mean_word_count": mean(word_counts),
                "mean_density": mean(row.density for row in graph_metrics),
                "mean_isolated_ratio": mean(
                    row.isolated_ratio for row in graph_metrics
                ),
                "mean_average_degree": mean(
                    row.average_degree for row in graph_metrics
                ),
                "mean_connected_components": mean(
                    row.connected_components for row in graph_metrics
                ),
            }
        )
    return summaries


def run_mmr_sweep() -> tuple[list[dict], list[dict]]:
    reference_dir = ROOT / "data" / "DUC_SUM"
    train_dir = ROOT / "data" / "DUC_TEXT" / "train"
    test_dir = ROOT / "data" / "DUC_TEXT" / "test"
    train_summaries = []
    selected_test_rows = []

    for threshold in THRESHOLDS:
        config = TextRankConfig(
            similarity_threshold=threshold,
            pagerank_damping=0.85,
            pagerank_tolerance=1e-8,
            pagerank_max_iterations=300,
            max_summary_words=100,
            use_mmr=True,
            mmr_lambda=0.70,
        )
        train_rows = evaluate_config(train_dir, reference_dir, config, "train")
        summary = aggregate_rows(train_rows)
        train_summaries.append(
            {
                "threshold": threshold,
                "eligible_topics": summary["eligible_topics"],
                "converged_topics": summary["converged_topics"],
                "macro_precision": summary["macro_precision"],
                "macro_recall": summary["macro_recall"],
                "macro_f1": summary["macro_f1"],
                "zero_f1_topics": sum(
                    int(row["reference"]) > 0 and float(row["f1"]) == 0.0
                    for row in train_rows
                ),
                "mean_density": summary["mean_density"],
                "mean_isolated_ratio": summary["mean_isolated_ratio"],
                "mean_average_degree": summary["mean_average_degree"],
                "mean_connected_components": summary["mean_connected_components"],
            }
        )
        if threshold == SELECTED_THRESHOLD:
            selected_test_rows = evaluate_config(
                test_dir, reference_dir, config, "test"
            )

    return train_summaries, selected_test_rows


def make_quality_chart(top_k_rows: list[dict], mmr_rows: list[dict]) -> None:
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    thresholds = [row["threshold"] for row in top_k_rows]
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharex=True)
    for axis, rows, title in (
        (axes[0], top_k_rows, "PageRank + Top-K=15"),
        (axes[1], mmr_rows, "PageRank + MMR + 100 words"),
    ):
        axis.plot(
            thresholds,
            [row["macro_precision"] for row in rows],
            marker="o",
            label="Precision",
        )
        axis.plot(
            thresholds,
            [row["macro_recall"] for row in rows],
            marker="o",
            label="Recall",
        )
        axis.plot(thresholds, [row["macro_f1"] for row in rows], marker="o", label="F1")
        axis.axvline(
            SELECTED_THRESHOLD,
            color="#C00000",
            linestyle="--",
            linewidth=1.2,
            label="Selected 0.0275",
        )
        axis.set_title(title)
        axis.set_xlabel("Similarity threshold")
        axis.grid(alpha=0.25)
    axes[0].set_ylabel("Macro score")
    axes[1].legend(loc="best", fontsize=8)
    figure.suptitle("Fine-grained similarity-threshold sweep on DUC train")
    figure.tight_layout()
    figure.savefig(CHART_DIR / "fine-threshold-quality.png", dpi=180)
    plt.close(figure)

    figure, axes = plt.subplots(1, 2, figsize=(12, 4.8), sharex=True)
    axes[0].plot(
        thresholds,
        [row["mean_density"] for row in top_k_rows],
        marker="o",
        label="Top-K density",
    )
    axes[0].plot(
        thresholds,
        [row["mean_density"] for row in mmr_rows],
        marker="s",
        label="MMR density",
    )
    axes[0].set_ylabel("Mean density")
    axes[1].plot(
        thresholds,
        [row["mean_connected_components"] for row in top_k_rows],
        marker="o",
        label="Top-K components",
    )
    axes[1].plot(
        thresholds,
        [row["mean_connected_components"] for row in mmr_rows],
        marker="s",
        label="MMR components",
    )
    axes[1].set_ylabel("Mean connected components")
    for axis in axes:
        axis.axvline(SELECTED_THRESHOLD, color="#C00000", linestyle="--", linewidth=1.2)
        axis.set_xlabel("Similarity threshold")
        axis.grid(alpha=0.25)
        axis.legend(loc="best", fontsize=8)
    figure.suptitle("Graph health in the fine-grained threshold sweep")
    figure.tight_layout()
    figure.savefig(CHART_DIR / "fine-threshold-graph-health.png", dpi=180)
    plt.close(figure)


def main() -> None:
    top_k_rows = run_top_k_sweep()
    package_mmr_train_rows = run_package_mmr_sweep("train")
    package_mmr_test_rows = run_package_mmr_sweep("test")
    mmr_rows, selected_test_rows = run_mmr_sweep()
    selected_test_summary = aggregate_rows(selected_test_rows)
    test_summary_rows = [
        {
            "threshold": SELECTED_THRESHOLD,
            "eligible_topics": selected_test_summary["eligible_topics"],
            "converged_topics": selected_test_summary["converged_topics"],
            "macro_precision": selected_test_summary["macro_precision"],
            "macro_recall": selected_test_summary["macro_recall"],
            "macro_f1": selected_test_summary["macro_f1"],
            "zero_f1_topics": sum(
                float(row["f1"]) == 0.0 for row in selected_test_rows
            ),
            "mean_density": selected_test_summary["mean_density"],
            "mean_isolated_ratio": selected_test_summary["mean_isolated_ratio"],
            "mean_average_degree": selected_test_summary["mean_average_degree"],
            "mean_connected_components": selected_test_summary[
                "mean_connected_components"
            ],
        }
    ]

    write_csv(CSV_DIR / "top-k-15-train-summary.csv", top_k_rows)
    write_csv(
        CSV_DIR / "package-mmr-100-words-train-summary.csv",
        package_mmr_train_rows,
    )
    write_csv(
        CSV_DIR / "package-mmr-100-words-test-summary.csv",
        package_mmr_test_rows,
    )
    write_csv(CSV_DIR / "mmr-100-words-train-summary.csv", mmr_rows)
    write_csv(CSV_DIR / "mmr-100-words-test-summary.csv", test_summary_rows)
    write_csv(CSV_DIR / "mmr-100-words-test-topic-metrics.csv", selected_test_rows)
    make_quality_chart(top_k_rows, mmr_rows)

    print(
        "Top-K selected:",
        next(row for row in top_k_rows if row["threshold"] == SELECTED_THRESHOLD),
    )
    best_package_mmr = max(package_mmr_train_rows, key=lambda row: row["macro_f1"])
    print("Package MMR best train:", best_package_mmr)
    print(
        "Package MMR test at best train threshold:",
        next(
            row
            for row in package_mmr_test_rows
            if row["threshold"] == best_package_mmr["threshold"]
        ),
    )
    print(
        "MMR train selected:",
        next(row for row in mmr_rows if row["threshold"] == SELECTED_THRESHOLD),
    )
    print("MMR test selected:", test_summary_rows[0])
    print("Output:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
