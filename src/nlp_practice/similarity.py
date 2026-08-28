import math
from pathlib import Path


def dot_product(vector_a: dict[str, float], vector_b: dict[str, float]) -> float:
    result = 0.0

    for token, weight_a in vector_a.items():
        weight_b = vector_b.get(token, 0.0)

        result += weight_a * weight_b

    return result


def vector_magnitude(vector: dict[str, float]) -> float:
    sum_of_squares = 0.0
    for weight in vector.values():
        sum_of_squares += weight * weight

    return math.sqrt(sum_of_squares)


def cosine_similarity(vector_a: dict[str, float], vector_b: dict[str, float]) -> float:
    magnitude_a = vector_magnitude(vector=vector_a)
    magnitude_b = vector_magnitude(vector=vector_b)

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    similarity = dot_product(vector_a=vector_a, vector_b=vector_b) / (
        magnitude_a * magnitude_b
    )

    return similarity


def build_similarity_matrix(
    vectors: list[dict[str, float]], threshold: float = 0.0
) -> list[list[float]]:
    total_vectors = len(vectors)

    matrix: list[list[float]] = []

    for _ in range(total_vectors):
        row = [0.0] * total_vectors
        matrix.append(row)

    for i in range(total_vectors):
        for j in range(i + 1, total_vectors):
            similarity = cosine_similarity(vector_a=vectors[i], vector_b=vectors[j])

            if similarity < threshold:
                continue

            matrix[i][j] = similarity
            matrix[j][i] = similarity

    return matrix


def write_similarity_matrix(
    matrix: list[list[float]],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open("w", encoding="utf-8") as file:
        file.write("     ")

        for index in range(len(matrix)):
            file.write(f"S{index:<7}")

        file.write("\n")

        for row_index, row in enumerate(matrix):
            file.write(f"S{row_index:<4}")

            for value in row:
                file.write(f"{value:<8.3f}")

            file.write("\n")
