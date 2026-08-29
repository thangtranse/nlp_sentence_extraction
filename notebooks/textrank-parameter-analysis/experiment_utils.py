import csv
import json
import math
import re
import statistics
import time
from collections import Counter
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "being",
    "but",
    "by",
    "for",
    "from",
    "had",
    "has",
    "have",
    "he",
    "her",
    "hers",
    "him",
    "his",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "no",
    "not",
    "of",
    "on",
    "or",
    "our",
    "ours",
    "she",
    "so",
    "that",
    "the",
    "their",
    "theirs",
    "them",
    "there",
    "they",
    "this",
    "those",
    "to",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "will",
    "with",
    "would",
    "you",
    "your",
    "said",
    "about",
    "after",
    "all",
    "also",
    "before",
    "could",
    "more",
    "most",
    "other",
    "over",
    "than",
    "then",
    "up",
}
TOKEN_PATTERN = re.compile(r"[a-z]+(?:'[a-z]+)?|\d+")


Graph = dict[int, dict[int, float]]


class PageRankConvergenceError(RuntimeError):
    pass


@dataclass(frozen=True)
class Sentence:
    docid: str
    num: int
    wdcount: int
    content: str
    tagged_content: str
    tokens: tuple[str, ...]
    source_index: int

    @property
    def key(self) -> tuple[str, int]:
        return self.docid, self.num


@dataclass(frozen=True)
class TextRankConfig:
    similarity_threshold: float = 0.10
    pagerank_damping: float = 0.85
    pagerank_tolerance: float = 1e-8
    pagerank_max_iterations: int = 1000
    max_summary_words: int = 100
    use_mmr: bool = True
    mmr_lambda: float = 0.70


@dataclass(frozen=True)
class TopicResult:
    topic: str
    selected_sentences: tuple[Sentence, ...]
    selected_indices: tuple[int, ...]
    graph: Graph
    similarities: tuple[tuple[float, ...], ...]
    pagerank_scores: dict[int, float]
    pagerank_iterations: int
    elapsed_seconds: float

    @property
    def prediction_keys(self) -> tuple[tuple[str, int], ...]:
        return tuple(sentence.key for sentence in self.selected_sentences)

    @property
    def word_count(self) -> int:
        return sum(
            len(sentence.content.split()) for sentence in self.selected_sentences
        )


def preprocess(text: str) -> tuple[str, ...]:
    return tuple(
        token
        for token in TOKEN_PATTERN.findall(text.lower())
        if token not in STOP_WORDS
    )


class DUCTopicParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.sentences: list[Sentence] = []
        self.current_attributes = None
        self.current_start_tag = ""
        self.current_text_parts: list[str] = []
        self.source_counter = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "s":
            self.current_attributes = dict(attrs)
            self.current_start_tag = self.get_starttag_text()
            self.current_text_parts = []

    def handle_data(self, data):
        if self.current_attributes is not None:
            self.current_text_parts.append(data)

    def handle_endtag(self, tag):
        if tag.lower() != "s" or self.current_attributes is None:
            return
        raw_text = "".join(self.current_text_parts)
        content = raw_text.strip()
        tokens = preprocess(content)
        if tokens:
            attributes = self.current_attributes
            self.sentences.append(
                Sentence(
                    docid=str(attributes.get("docid", "")),
                    num=int(attributes.get("num", 0)),
                    wdcount=int(attributes.get("wdcount", len(content.split()))),
                    content=content,
                    tagged_content=f"{self.current_start_tag}{raw_text}</s>",
                    tokens=tokens,
                    source_index=self.source_counter,
                )
            )
        self.source_counter += 1
        self.current_attributes = None
        self.current_start_tag = ""
        self.current_text_parts = []


def read_topic(topic_path: Path) -> list[Sentence]:
    parser = DUCTopicParser()
    parser.feed(topic_path.read_text(encoding="utf-8"))
    parser.close()
    return parser.sentences


def read_reference_keys(reference_path: Path) -> set[tuple[str, int]]:
    return {sentence.key for sentence in read_topic(reference_path)}


def calculate_tf(tokens: tuple[str, ...]) -> dict[str, float]:
    counts = Counter(tokens)
    return {term: count / len(tokens) for term, count in counts.items()}


def calculate_idf(tokenized_sentences: list[tuple[str, ...]]) -> dict[str, float]:
    sentence_count = len(tokenized_sentences)
    document_frequency = Counter(
        term for tokens in tokenized_sentences for term in set(tokens)
    )
    return {
        term: math.log((1 + sentence_count) / (1 + frequency)) + 1
        for term, frequency in document_frequency.items()
    }


def l2_normalize(vector: dict[str, float]) -> dict[str, float]:
    norm = math.sqrt(sum(weight * weight for weight in vector.values()))
    if norm == 0.0:
        return {}
    return {term: weight / norm for term, weight in vector.items()}


def calculate_tfidf_vectors(sentences: list[Sentence]) -> list[dict[str, float]]:
    tokenized_sentences = [sentence.tokens for sentence in sentences]
    idf = calculate_idf(tokenized_sentences)
    vectors = []
    for tokens in tokenized_sentences:
        tf = calculate_tf(tokens)
        vectors.append(
            l2_normalize({term: value * idf[term] for term, value in tf.items()})
        )
    return vectors


def cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if len(left) > len(right):
        left, right = right, left
    return sum(weight * right.get(term, 0.0) for term, weight in left.items())


def build_sentence_graph(
    vectors: list[dict[str, float]], similarity_threshold: float
) -> tuple[Graph, list[list[float]]]:
    sentence_count = len(vectors)
    graph = {index: {} for index in range(sentence_count)}
    similarities = [[0.0] * sentence_count for _ in range(sentence_count)]
    for left_index in range(sentence_count):
        for right_index in range(left_index + 1, sentence_count):
            similarity = cosine_similarity(vectors[left_index], vectors[right_index])
            similarities[left_index][right_index] = similarity
            similarities[right_index][left_index] = similarity
            if similarity >= similarity_threshold:
                graph[left_index][right_index] = similarity
                graph[right_index][left_index] = similarity
    return graph, similarities


def calculate_pagerank(
    graph: Graph,
    damping: float = 0.85,
    tolerance: float = 1e-8,
    max_iterations: int = 1000,
) -> tuple[dict[int, float], int]:
    node_count = len(graph)
    if node_count == 0:
        return {}, 0
    if not 0.0 < damping < 1.0:
        raise ValueError("damping must be in (0, 1)")
    scores = {node: 1.0 / node_count for node in graph}
    outgoing_weights = {
        node: sum(neighbors.values()) for node, neighbors in graph.items()
    }
    for iteration in range(1, max_iterations + 1):
        dangling_score = sum(
            scores[node]
            for node, outgoing_weight in outgoing_weights.items()
            if outgoing_weight == 0.0
        )
        base_score = (1.0 - damping) / node_count
        dangling_share = damping * dangling_score / node_count
        new_scores = {node: base_score + dangling_share for node in graph}
        for source, neighbors in graph.items():
            total_weight = outgoing_weights[source]
            if total_weight == 0.0:
                continue
            for target, edge_weight in neighbors.items():
                new_scores[target] += (
                    damping * scores[source] * edge_weight / total_weight
                )
        difference = sum(abs(new_scores[node] - scores[node]) for node in graph)
        scores = new_scores
        if difference < tolerance:
            return scores, iteration
    raise PageRankConvergenceError(
        f"PageRank did not converge after {max_iterations} iterations"
    )


def normalize_scores(scores: dict[int, float]) -> dict[int, float]:
    low, high = min(scores.values()), max(scores.values())
    if math.isclose(low, high):
        return {index: 1.0 for index in scores}
    return {index: (score - low) / (high - low) for index, score in scores.items()}


def select_sentences(
    sentences: list[Sentence],
    pagerank_scores: dict[int, float],
    similarities: list[list[float]],
    config: TextRankConfig,
) -> list[int]:
    relevance = normalize_scores(pagerank_scores)
    remaining = set(range(len(sentences)))
    selected: list[int] = []
    used_words = 0
    while remaining:
        fitting = [
            index
            for index in remaining
            if used_words + len(sentences[index].content.split())
            <= config.max_summary_words
        ]
        if not fitting:
            break

        def selection_score(index: int) -> tuple[float, float, int]:
            redundancy = (
                max(similarities[index][chosen] for chosen in selected)
                if config.use_mmr and selected
                else 0.0
            )
            score = (
                config.mmr_lambda * relevance[index]
                - (1.0 - config.mmr_lambda) * redundancy
                if config.use_mmr
                else relevance[index]
            )
            return score, pagerank_scores[index], -sentences[index].source_index

        chosen = max(fitting, key=selection_score)
        selected.append(chosen)
        remaining.remove(chosen)
        used_words += len(sentences[chosen].content.split())
    return selected


def summarize_topic(topic_path: Path, config: TextRankConfig) -> TopicResult:
    started = time.perf_counter()
    sentences = read_topic(topic_path)
    if not sentences:
        return TopicResult(
            topic_path.name, (), (), {}, (), {}, 0, time.perf_counter() - started
        )
    vectors = calculate_tfidf_vectors(sentences)
    graph, similarities = build_sentence_graph(vectors, config.similarity_threshold)
    scores, iterations = calculate_pagerank(
        graph,
        config.pagerank_damping,
        config.pagerank_tolerance,
        config.pagerank_max_iterations,
    )
    selected_indices = select_sentences(sentences, scores, similarities, config)
    selected_indices.sort(key=lambda index: sentences[index].source_index)
    return TopicResult(
        topic=topic_path.name,
        selected_sentences=tuple(sentences[index] for index in selected_indices),
        selected_indices=tuple(selected_indices),
        graph=graph,
        similarities=tuple(tuple(row) for row in similarities),
        pagerank_scores=scores,
        pagerank_iterations=iterations,
        elapsed_seconds=time.perf_counter() - started,
    )


@dataclass(frozen=True)
class TopicMetrics:
    true_positive: int
    predicted: int
    reference: int
    precision: float
    recall: float
    f1: float


@dataclass(frozen=True)
class GraphMetrics:
    nodes: int
    edges: int
    density: float
    isolated_nodes: int
    isolated_ratio: float
    average_degree: float
    connected_components: int


def evaluate_keys(
    prediction_keys,
    reference_keys: set[tuple[str, int]],
) -> TopicMetrics:
    predictions = set(prediction_keys)
    references = set(reference_keys)
    true_positive = len(predictions & references)
    precision = true_positive / len(predictions) if predictions else 0.0
    recall = true_positive / len(references) if references else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return TopicMetrics(
        true_positive=true_positive,
        predicted=len(predictions),
        reference=len(references),
        precision=precision,
        recall=recall,
        f1=f1,
    )


def calculate_graph_metrics(graph: Graph) -> GraphMetrics:
    nodes = len(graph)
    edges = sum(len(neighbors) for neighbors in graph.values()) // 2
    isolated_nodes = sum(not neighbors for neighbors in graph.values())
    density = 2 * edges / (nodes * (nodes - 1)) if nodes > 1 else 0.0
    average_degree = 2 * edges / nodes if nodes else 0.0
    isolated_ratio = isolated_nodes / nodes if nodes else 0.0
    visited = set()
    connected_components = 0
    for start in graph:
        if start in visited:
            continue
        connected_components += 1
        stack = [start]
        visited.add(start)
        while stack:
            node = stack.pop()
            for neighbor in graph[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)
    return GraphMetrics(
        nodes=nodes,
        edges=edges,
        density=density,
        isolated_nodes=isolated_nodes,
        isolated_ratio=isolated_ratio,
        average_degree=average_degree,
        connected_components=connected_components,
    )


def calculate_redundancy(result: TopicResult) -> tuple[float, float]:
    pair_values = []
    indices = result.selected_indices
    for position, left_index in enumerate(indices):
        for right_index in indices[position + 1 :]:
            pair_values.append(result.similarities[left_index][right_index])
    if not pair_values:
        return 0.0, 0.0
    return statistics.fmean(pair_values), max(pair_values)


def _config_fields(config: TextRankConfig) -> dict[str, object]:
    return {
        "similarity_threshold": config.similarity_threshold,
        "pagerank_damping": config.pagerank_damping,
        "pagerank_tolerance": config.pagerank_tolerance,
        "pagerank_max_iterations": config.pagerank_max_iterations,
        "max_summary_words": config.max_summary_words,
        "use_mmr": config.use_mmr,
        "mmr_lambda": config.mmr_lambda if config.use_mmr else None,
    }


def config_fields(config: TextRankConfig) -> dict[str, object]:
    return _config_fields(config)


def evaluate_config(
    input_dir: Path,
    reference_dir: Path,
    config: TextRankConfig,
    split: str,
) -> list[dict[str, object]]:
    rows = []
    for topic_path in sorted(path for path in input_dir.iterdir() if path.is_file()):
        reference_path = reference_dir / topic_path.name
        if not reference_path.is_file():
            raise FileNotFoundError(
                f"Missing reference for topic {topic_path.name}: {reference_path}"
            )
        base = {"split": split, "topic": topic_path.name, **_config_fields(config)}
        try:
            result = summarize_topic(topic_path, config)
        except PageRankConvergenceError:
            rows.append(
                {
                    **base,
                    "status": "not_converged",
                    "true_positive": 0,
                    "predicted": 0,
                    "reference": len(read_reference_keys(reference_path)),
                    "precision": 0.0,
                    "recall": 0.0,
                    "f1": 0.0,
                    "hit_at_1": 0,
                    "hit_at_3": 0,
                    "hit_at_5": 0,
                    "word_count": 0,
                    "budget_utilization": 0.0,
                    "nodes": 0,
                    "edges": 0,
                    "density": 0.0,
                    "isolated_nodes": 0,
                    "isolated_ratio": 0.0,
                    "average_degree": 0.0,
                    "connected_components": 0,
                    "mean_redundancy": 0.0,
                    "max_redundancy": 0.0,
                    "pagerank_iterations": config.pagerank_max_iterations,
                    "runtime_seconds": 0.0,
                }
            )
            continue
        references = read_reference_keys(reference_path)
        metrics = evaluate_keys(result.prediction_keys, references)
        graph_metrics = calculate_graph_metrics(result.graph)
        mean_redundancy, max_redundancy = calculate_redundancy(result)
        prediction_keys = list(dict.fromkeys(result.prediction_keys))
        rows.append(
            {
                **base,
                "status": "converged",
                "true_positive": metrics.true_positive,
                "predicted": metrics.predicted,
                "reference": metrics.reference,
                "precision": metrics.precision,
                "recall": metrics.recall,
                "f1": metrics.f1,
                "hit_at_1": int(any(key in references for key in prediction_keys[:1])),
                "hit_at_3": int(any(key in references for key in prediction_keys[:3])),
                "hit_at_5": int(any(key in references for key in prediction_keys[:5])),
                "word_count": result.word_count,
                "budget_utilization": result.word_count / config.max_summary_words,
                "nodes": graph_metrics.nodes,
                "edges": graph_metrics.edges,
                "density": graph_metrics.density,
                "isolated_nodes": graph_metrics.isolated_nodes,
                "isolated_ratio": graph_metrics.isolated_ratio,
                "average_degree": graph_metrics.average_degree,
                "connected_components": graph_metrics.connected_components,
                "mean_redundancy": mean_redundancy,
                "max_redundancy": max_redundancy,
                "pagerank_iterations": result.pagerank_iterations,
                "runtime_seconds": result.elapsed_seconds,
            }
        )
    return rows


def aggregate_rows(rows: list[dict[str, object]]) -> dict[str, object]:
    eligible = [
        row
        for row in rows
        if row["status"] == "converged" and int(row["reference"]) > 0
    ]
    converged = [row for row in rows if row["status"] == "converged"]

    def mean(field: str, source=eligible) -> float:
        return statistics.fmean(float(row[field]) for row in source) if source else 0.0

    return {
        "eligible_topics": len(eligible),
        "converged_topics": len(converged),
        "macro_precision": mean("precision"),
        "macro_recall": mean("recall"),
        "macro_f1": mean("f1"),
        "macro_hit_at_1": mean("hit_at_1"),
        "macro_hit_at_3": mean("hit_at_3"),
        "macro_hit_at_5": mean("hit_at_5"),
        "mean_density": mean("density", converged),
        "mean_isolated_ratio": mean("isolated_ratio", converged),
        "mean_average_degree": mean("average_degree", converged),
        "mean_connected_components": mean("connected_components", converged),
        "mean_redundancy": mean("mean_redundancy", converged),
        "max_redundancy": max(
            (float(row["max_redundancy"]) for row in converged), default=0.0
        ),
        "mean_word_count": mean("word_count", converged),
        "mean_budget_utilization": mean("budget_utilization", converged),
        "mean_pagerank_iterations": mean("pagerank_iterations", converged),
        "mean_runtime_seconds": mean("runtime_seconds", converged),
    }


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


DETAIL_FIELDS = [
    "config_id",
    "split",
    "topic",
    "status",
    "similarity_threshold",
    "pagerank_damping",
    "pagerank_tolerance",
    "pagerank_max_iterations",
    "max_summary_words",
    "use_mmr",
    "mmr_lambda",
    "true_positive",
    "predicted",
    "reference",
    "precision",
    "recall",
    "f1",
    "hit_at_1",
    "hit_at_3",
    "hit_at_5",
    "word_count",
    "budget_utilization",
    "nodes",
    "edges",
    "density",
    "isolated_nodes",
    "isolated_ratio",
    "average_degree",
    "connected_components",
    "mean_redundancy",
    "max_redundancy",
    "pagerank_iterations",
    "runtime_seconds",
]

SUMMARY_FIELDS = [
    "rank",
    "config_id",
    "similarity_threshold",
    "pagerank_damping",
    "pagerank_tolerance",
    "pagerank_max_iterations",
    "max_summary_words",
    "use_mmr",
    "mmr_lambda",
    "eligible_topics",
    "converged_topics",
    "macro_precision",
    "macro_recall",
    "macro_f1",
    "macro_hit_at_1",
    "macro_hit_at_3",
    "macro_hit_at_5",
    "mean_density",
    "mean_isolated_ratio",
    "mean_average_degree",
    "mean_connected_components",
    "mean_redundancy",
    "max_redundancy",
    "mean_word_count",
    "mean_budget_utilization",
    "mean_pagerank_iterations",
    "mean_runtime_seconds",
]


def config_id(config: TextRankConfig) -> str:
    mmr = f"{config.mmr_lambda:.2f}" if config.use_mmr else "off"
    return (
        f"t={config.similarity_threshold:.2f}|d={config.pagerank_damping:.2f}"
        f"|tol={config.pagerank_tolerance:.0e}|iter={config.pagerank_max_iterations}"
        f"|words={config.max_summary_words}|mmr={mmr}"
    )


def run_sweep(
    input_dir: Path,
    reference_dir: Path,
    configs: list[TextRankConfig],
    split: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    detail_rows = []
    summary_rows = []
    seen = set()
    for config in configs:
        identifier = config_id(config)
        if identifier in seen:
            continue
        seen.add(identifier)
        rows = evaluate_config(input_dir, reference_dir, config, split)
        for row in rows:
            row["config_id"] = identifier
        detail_rows.extend(rows)
        summary_rows.append(
            {
                "config_id": identifier,
                **_config_fields(config),
                **aggregate_rows(rows),
            }
        )
    return detail_rows, summary_rows


def rank_configurations(
    summary_rows: list[dict[str, object]], required_topics: int
) -> list[dict[str, object]]:
    eligible = [
        row
        for row in summary_rows
        if int(float(row["converged_topics"])) == required_topics
    ]
    ranked = sorted(
        eligible,
        key=lambda row: (
            -float(row["macro_precision"]),
            -float(row["macro_f1"]),
            float(row["mean_redundancy"]),
            float(row["mean_runtime_seconds"]),
            str(row["config_id"]),
        ),
    )
    for rank, row in enumerate(ranked, start=1):
        row["rank"] = rank
    return ranked


def top_unique_values(
    rows: list[dict[str, object]], field: str, limit: int
) -> list[object]:
    values = []
    for row in rows:
        value = row[field]
        if value not in values:
            values.append(value)
        if len(values) == limit:
            break
    return values


def build_local_grid(
    thresholds: list[float],
    pagerank_configs: list[tuple[float, float, int]],
    mmr_configs: list[tuple[bool, float]],
) -> list[TextRankConfig]:
    configs = []
    seen = set()
    for threshold in thresholds:
        for damping, tolerance, max_iterations in pagerank_configs:
            for use_mmr, mmr_lambda in mmr_configs:
                config = TextRankConfig(
                    similarity_threshold=float(threshold),
                    pagerank_damping=float(damping),
                    pagerank_tolerance=float(tolerance),
                    pagerank_max_iterations=int(max_iterations),
                    max_summary_words=100,
                    use_mmr=bool(use_mmr),
                    mmr_lambda=float(mmr_lambda) if use_mmr else 0.0,
                )
                identifier = config_id(config)
                if identifier not in seen:
                    seen.add(identifier)
                    configs.append(config)
    return configs


def config_from_row(row: dict[str, object]) -> TextRankConfig:
    use_mmr_value = row["use_mmr"]
    use_mmr = (
        use_mmr_value
        if isinstance(use_mmr_value, bool)
        else str(use_mmr_value).lower() == "true"
    )
    mmr_value = row.get("mmr_lambda")
    return TextRankConfig(
        similarity_threshold=float(row["similarity_threshold"]),
        pagerank_damping=float(row["pagerank_damping"]),
        pagerank_tolerance=float(row["pagerank_tolerance"]),
        pagerank_max_iterations=int(float(row["pagerank_max_iterations"])),
        max_summary_words=int(float(row.get("max_summary_words", 100))),
        use_mmr=use_mmr,
        mmr_lambda=float(mmr_value) if use_mmr and mmr_value not in (None, "") else 0.0,
    )
