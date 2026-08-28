def calculate_pagerank(
    graph: dict[int, dict[int, float]],
    damping: float = 0.85,
    tolerance: float = 1e-8,
    max_iterations: int = 1000,
) -> tuple[dict[int, float], int]:
    node_count = len(graph)

    if node_count == 0:
        return {}, 0

    scores: dict[int, float] = {}
    outgoing_weights: dict[int, float] = {}

    for node, neighbors in graph.items():
        scores[node] = 1.0 / node_count
        outgoing_weights[node] = sum(neighbors.values())

    for iteration in range(1, max_iterations + 1):
        dangling_score = 0.0

        for node, total_weight in outgoing_weights.items():
            if total_weight == 0.0:
                dangling_score += scores[node]

        base_score = (1.0 - damping) / node_count
        dangling_share = damping * dangling_score / node_count

        new_scores: dict[int, float] = {}
        for node in graph:
            new_scores[node] = base_score + dangling_share

        for source, neighbors in graph.items():
            total_weight = outgoing_weights[source]

            if total_weight == 0.0:
                continue

            for target, edge_weight in neighbors.items():
                new_scores[target] += (
                    damping * scores[source] * edge_weight / total_weight
                )

        difference = 0.0

        for node in graph:
            difference += abs(new_scores[node] - scores[node])

        scores = new_scores

        if difference < tolerance:
            return scores, iteration

    raise RuntimeError("PageRank did not converge")


def get_pagerank_score(item: dict) -> float:
    return item["score"]


def rank_sentences_by_pagerank(
    sentences: list[dict], pagerank_scores: dict[int, float], top_k: int
) -> list[dict]:
    ranked_sentences: list[dict] = []

    for index in range(len(sentences)):
        sentence = sentences[index]
        score = pagerank_scores[index]

        item = {
            "index": index,
            "score": score,
            "content": sentence["content"],
            "tagged_content": sentence["tagged_content"],
        }

        ranked_sentences.append(item)

    ranked_sentences.sort(key=get_pagerank_score, reverse=True)

    return ranked_sentences[:top_k]
