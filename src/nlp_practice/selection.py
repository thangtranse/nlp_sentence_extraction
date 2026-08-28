import math


def normalize_scores(scores: dict[int, float]) -> dict[int, float]:
    low = min(scores.values())
    hight = max(scores.values())

    normalized_scores: dict[int, float] = {}

    if math.isclose(low, hight):
        for index in scores:
            normalized_scores[index] = 1.0

        return normalized_scores

    for index, score in scores.items():
        normalized_scores[index] = (score - low) / (hight - low)

    return normalized_scores
