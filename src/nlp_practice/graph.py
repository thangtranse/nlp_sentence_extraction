from pathlib import Path
import matplotlib.pyplot as plt
import networkx as nx


def build_sentence_graph(
    similarities: list[list[float]],
    similarity_threshold: float,
) -> dict[int, dict[int, float]]:
    sentence_count = len(similarities)

    graph: dict[int, dict[int, float]] = {}

    for index in range(sentence_count):
        graph[index] = {}

    for left_index in range(sentence_count):
        for right_index in range(left_index + 1, sentence_count):
            similarity = similarities[left_index][right_index]
            if similarity < similarity_threshold:
                continue

            graph[left_index][right_index] = similarity
            graph[right_index][left_index] = similarity

    return graph


def draw_sentence_graph(
    graph: dict[int, dict[int, float]],
    output_path: Path,
    min_weight: float = 0.20,
) -> None:

    network = nx.Graph()

    for node in graph:

        network.add_node(node)

    for source, neighbors in graph.items():

        for target, weight in neighbors.items():

            if weight < min_weight:

                continue

            network.add_edge(
                source,
                target,
                weight=weight,
            )

    positions = nx.spring_layout(
        network,
        seed=42,
        k=1.2,
        iterations=200,
    )

    node_labels = {node: f"S{node}" for node in network.nodes}

    plt.figure(
        figsize=(18, 14),
    )

    nx.draw_networkx_nodes(
        network,
        positions,
        node_size=350,
    )

    nx.draw_networkx_edges(
        network,
        positions,
        width=0.8,
        alpha=0.35,
    )

    nx.draw_networkx_labels(
        network,
        positions,
        labels=node_labels,
        font_size=7,
    )

    plt.title(f"Sentence Similarity Graph (weight >= {min_weight})")

    plt.axis("off")

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    plt.savefig(
        output_path,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close()
