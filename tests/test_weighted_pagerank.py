import math

from nlp_practice.pagerank import calculate_pagerank
from nlp_practice.weights import calculate_sentence_priorities


def test_sentence_priorities_are_normalized_and_prefer_early_central_sentence():
    sentences = [
        {"docid": "doc-a", "wdcount": 20, "content": "first"},
        {"docid": "doc-a", "wdcount": 5, "content": "second"},
        {"docid": "doc-b", "wdcount": 20, "content": "third"},
    ]
    vectors = [
        {"topic": 1.0},
        {"other": 1.0},
        {"topic": 1.0},
    ]

    priorities = calculate_sentence_priorities(
        sentences,
        vectors,
        centroid_weight=0.55,
        position_weight=0.30,
        length_weight=0.15,
        preferred_words=20,
    )

    assert math.isclose(sum(priorities.values()), 1.0)
    assert priorities[0] > priorities[1]
    assert priorities[2] > priorities[1]


def test_personalized_pagerank_changes_teleport_probability():
    graph = {0: {}, 1: {}}

    scores, _ = calculate_pagerank(
        graph,
        personalization={0: 0.8, 1: 0.2},
    )

    assert math.isclose(scores[0], 0.8)
    assert math.isclose(scores[1], 0.2)


def test_pagerank_without_personalization_keeps_uniform_behavior():
    graph = {0: {}, 1: {}}

    scores, _ = calculate_pagerank(graph)

    assert math.isclose(scores[0], 0.5)
    assert math.isclose(scores[1], 0.5)
