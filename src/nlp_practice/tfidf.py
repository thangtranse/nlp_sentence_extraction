import math


def compute_tf(tokens: list[str]) -> dict[str, int]:
    term_frequency: dict[str, int] = {}

    for token in tokens:
        if token not in term_frequency:
            term_frequency[token] = 0
        term_frequency[token] += 1

    return term_frequency


def compute_df(tokenized_sentences: list[list[str]]) -> dict[str, int]:
    document_frequency: dict[str, int] = {}

    for tokens in tokenized_sentences:
        unique_tokens = set(tokens)

        for token in unique_tokens:
            if token not in document_frequency:
                document_frequency[token] = 0
            document_frequency[token] += 1

    return document_frequency


def compute_idf(df: dict[str, int], total_documents: int) -> dict[str, float]:
    inverse_df: dict[str, float] = {}

    for token, frequency in df.items():
        # inverse_df[token] = math.log(total_documents / frequency)
        inverse_df[token] = math.log((1 + total_documents) / (1 + frequency)) + 1

    return inverse_df


def compute_tfidf(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    tf = compute_tf(tokens)

    vector: dict[str, float] = {}

    for token, frequency in tf.items():
        vector[token] = frequency * idf[token]

    return vector


def normalize_l2(vector: dict[str, float]) -> dict[str, float]:
    sum_of_squares = 0.0

    for value in vector.values():
        sum_of_squares += value * value

    vector_length = math.sqrt(sum_of_squares)

    if vector_length == 0.0:
        return vector

    normalized_vector: dict[str, float] = {}

    for token, value in vector.items():
        normalized_vector[token] = value / vector_length

    return normalized_vector


def build_tfidf_vectors(sentences: list[dict]) -> list[dict[str, float]]:
    tokenized_sentences: list[list[str]] = []

    for sentence in sentences:
        tokenized_sentences.append(sentence["token"])

    document_frequency = compute_df(tokenized_sentences=tokenized_sentences)
    idf = compute_idf(document_frequency, len(sentences))

    tfidf_vectors: list[dict[str, float]] = []

    for tokens in tokenized_sentences:
        vector = compute_tfidf(tokens=tokens, idf=idf)
        normalized_vector = normalize_l2(vector)
        tfidf_vectors.append(normalized_vector)

    return tfidf_vectors


# ------------
# Use library to check
# ------------

from sklearn.feature_extraction.text import TfidfVectorizer


def compute_tfidf_with_sklearn(
    sentences: list[dict],
) -> list[dict[str, float]]:

    if len(sentences) == 0:
        return []

    documents: list[str] = []

    for sentence in sentences:
        tokens = sentence["token"]
        document = " ".join(tokens)
        documents.append(document)

    vectorizer = TfidfVectorizer()

    tfidf_matrix = vectorizer.fit_transform(documents)
    feature_names = vectorizer.get_feature_names_out()

    vectors: list[dict[str, float]] = []

    for row_index in range(tfidf_matrix.shape[0]):
        vector: dict[str, float] = {}
        row = tfidf_matrix.getrow(row_index)

        for column_index, value in zip(row.indices, row.data):
            term = feature_names[column_index]
            vector[term] = float(value)

        vectors.append(vector)

    return vectors
