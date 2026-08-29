from nlp_practice.similarity import cosine_similarity


def build_centroid(vectors: list[dict[str, float]]) -> dict[str, float]:
    """Tính vector trung tâm bằng trung bình các vector câu."""

    if len(vectors) == 0:
        return {}

    centroid: dict[str, float] = {}

    for vector in vectors:
        for token, value in vector.items():
            if token not in centroid:
                centroid[token] = 0.0
            centroid[token] += value

    for token in centroid:
        centroid[token] /= len(vectors)

    return centroid


def calculate_position_scores(sentences: list[dict]) -> dict[int, float]:
    """Ưu tiên câu xuất hiện sớm trong từng tài liệu nguồn."""

    document_positions: dict[str, int] = {}
    scores: dict[int, float] = {}

    for index, sentence in enumerate(sentences):
        document_id = str(sentence.get("docid", ""))
        position = document_positions.get(document_id, 0)
        scores[index] = 1.0 / (1.0 + position)
        document_positions[document_id] = position + 1

    return scores


def calculate_length_score(sentence: dict, preferred_words: int) -> float:
    """Cho điểm cao nhất khi độ dài câu gần preferred_words."""

    if preferred_words <= 0:
        raise ValueError("preferred_words must be greater than 0")

    word_count = int(sentence.get("wdcount", 0))
    if word_count <= 0:
        word_count = len(str(sentence.get("content", "")).split())
    if word_count <= 0:
        return 0.0

    shorter = min(word_count, preferred_words)
    longer = max(word_count, preferred_words)
    return shorter / longer


def calculate_sentence_priorities(
    sentences: list[dict],
    vectors: list[dict[str, float]],
    centroid_weight: float,
    position_weight: float,
    length_weight: float,
    preferred_words: int = 20,
) -> dict[int, float]:
    """Kết hợp các đặc trưng và chuẩn hóa thành phân phối xác suất."""

    if len(sentences) != len(vectors):
        raise ValueError("sentences and vectors must have the same length")

    feature_weights = [centroid_weight, position_weight, length_weight]
    for weight in feature_weights:
        if weight < 0.0:
            raise ValueError("feature weights must not be negative")

    weight_sum = sum(feature_weights)
    if weight_sum <= 0.0:
        raise ValueError("at least one feature weight must be positive")

    if len(sentences) == 0:
        return {}

    centroid = build_centroid(vectors)
    position_scores = calculate_position_scores(sentences)
    raw_scores: dict[int, float] = {}

    for index, sentence in enumerate(sentences):
        centroid_score = cosine_similarity(vectors[index], centroid)
        length_score = calculate_length_score(sentence, preferred_words)

        raw_scores[index] = (
            centroid_weight * centroid_score
            + position_weight * position_scores[index]
            + length_weight * length_score
        ) / weight_sum

    total_score = sum(raw_scores.values())
    if total_score == 0.0:
        uniform_score = 1.0 / len(sentences)
        return {index: uniform_score for index in range(len(sentences))}

    return {index: score / total_score for index, score in raw_scores.items()}
