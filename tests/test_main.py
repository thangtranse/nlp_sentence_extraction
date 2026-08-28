import math

from evaluation.main import (
    calculate_average,
    calculate_metrics,
    find_zero_f1_topics,
    normalize_sentence,
)


def test_normalize_sentence():
    sentence = "  Hurricane   Gilbert\nReached Jamaica.  "

    assert normalize_sentence(sentence) == "hurricane gilbert reached jamaica."


def test_calculate_metrics():
    predicted = {"sentence one", "sentence two", "sentence three"}
    expected = {"sentence two", "sentence three", "sentence four", "sentence five"}

    result = calculate_metrics(predicted, expected)

    assert result["correct_count"] == 2
    assert math.isclose(result["precision"], 2 / 3)
    assert math.isclose(result["recall"], 2 / 4)
    assert math.isclose(result["f1"], 4 / 7)


def test_calculate_metrics_when_there_is_no_match():
    result = calculate_metrics({"prediction"}, {"expected"})

    assert result["precision"] == 0.0
    assert result["recall"] == 0.0
    assert result["f1"] == 0.0


def test_calculate_average():
    results = [
        {"precision": 1.0, "recall": 0.5, "f1": 2 / 3},
        {"precision": 0.0, "recall": 0.0, "f1": 0.0},
    ]

    average = calculate_average(results)

    assert math.isclose(average["precision"], 0.5)
    assert math.isclose(average["recall"], 0.25)
    assert math.isclose(average["f1"], 1 / 3)


def test_find_zero_f1_topics():
    results = [
        {"topic": "d061j", "f1": 0.25},
        {"topic": "d076b", "f1": 0.0},
        {"topic": "d092c", "f1": 0.0},
    ]

    assert find_zero_f1_topics(results) == ["d076b", "d092c"]
