import math


def normalize_scores(scores: dict[int, float]) -> dict[int, float]:
    if len(scores) == 0:
        return {}

    low = min(scores.values())
    high = max(scores.values())

    normalized_scores: dict[int, float] = {}

    if math.isclose(low, high):
        for index in scores:
            normalized_scores[index] = 1.0

        return normalized_scores

    for index, score in scores.items():
        normalized_scores[index] = (score - low) / (high - low)

    return normalized_scores


def select_sentences(
    sentences: list[dict],
    pagerank_scores: dict[int, float],
    similarities: list[list[float]],
    max_summary_words: int,
    use_mmr: bool,
    mmr_lambda: float,
) -> list[dict]:
    if max_summary_words <= 0:
        return []

    if not 0.0 <= mmr_lambda <= 1.0:
        raise ValueError("mmr_lambda must be in [0, 1]")

    relevance = normalize_scores(pagerank_scores)
    remaining = set(range(len(sentences)))
    selected_indices: list[int] = []
    used_words = 0

    while remaining:
        fitting_indices: list[int] = []
        for index in remaining:
            sentence_words = len(sentences[index]["content"].split())
            if used_words + sentence_words <= max_summary_words:
                fitting_indices.append(index)

        if len(fitting_indices) == 0:
            break

        chosen_index = fitting_indices[0]
        chosen_key: tuple[float, float, int] | None = None

        for index in fitting_indices:
            redundancy = 0.0
            if use_mmr and len(selected_indices) > 0:
                for selected_index in selected_indices:
                    similarity = similarities[index][selected_index]
                    if similarity > redundancy:
                        redundancy = similarity

            selection_score = relevance[index]
            if use_mmr:
                selection_score = (
                    mmr_lambda * relevance[index] - (1.0 - mmr_lambda) * redundancy
                )

            source_index = sentences[index].get("source_index", index)
            candidate_key = (
                selection_score,
                pagerank_scores[index],
                -source_index,
            )
            if chosen_key is None or candidate_key > chosen_key:
                chosen_key = candidate_key
                chosen_index = index

        selected_indices.append(chosen_index)
        remaining.remove(chosen_index)
        used_words += len(sentences[chosen_index]["content"].split())

    selected_indices.sort(key=lambda index: sentences[index].get("source_index", index))

    selected_sentences: list[dict] = []
    for index in selected_indices:
        sentence = dict(sentences[index])
        sentence["index"] = index
        sentence["score"] = pagerank_scores[index]
        selected_sentences.append(sentence)

    return selected_sentences
