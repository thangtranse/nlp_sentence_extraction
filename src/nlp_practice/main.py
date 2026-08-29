from pathlib import Path
from nlp_practice.graph import build_sentence_graph, draw_sentence_graph
from nlp_practice.pagerank import calculate_pagerank, rank_sentences_by_pagerank
from nlp_practice.preprocessing import read_topic
from nlp_practice.selection import select_sentences
from nlp_practice.similarity import (
    build_similarity_matrix,
    cosine_similarity,
    write_similarity_matrix,
)
from nlp_practice.tfidf import (
    build_tfidf_vectors,
    compute_tfidf_with_sklearn,
)

# --- Config
SIMILARITY_THRESHOLD = 0.0125

PAGERANK_DAMPING = 0.85
PAGERANK_TOLERANCE = 1e-8
PAGERANK_MAX_ITERATIONS = 1000

USE_MMR = True
MAX_SUMMARY_WORDS = 100
MMR_LAMBDA = 0.70

TOP_K = 15
# ----


def main() -> None:
    PROJECT_ROOT = Path(__file__).resolve().parents[2]

    INPUT_DIR = PROJECT_ROOT / "data" / "DUC_TEXT" / "train"
    OUTPUT_DIR = PROJECT_ROOT / "data" / "output" / "nlp-practice"

    if not INPUT_DIR.is_dir():
        raise FileNotFoundError(f"Không tìm thấy thư mục: {INPUT_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Project root: {PROJECT_ROOT}")
    print(f"Input data: {INPUT_DIR}")
    print(f"Output data: {OUTPUT_DIR}")

    topic_files = sorted(INPUT_DIR.iterdir())

    if len(topic_files) == 0:
        raise RuntimeError(f"Không có file nào trong: {INPUT_DIR}")

    for topic_path in topic_files:
        if not topic_path.is_file():
            continue

        # if not topic_path.name == "d092c":
        #     continue

        sentences = read_topic(topic_path=topic_path)

        tfidf_vectors: list[dict[str, float]] = build_tfidf_vectors(sentences=sentences)

        # Keep the full matrix for MMR redundancy. The threshold belongs to
        # graph construction and must not erase weak pairwise similarities.
        similarity_matrix = build_similarity_matrix(
            tfidf_vectors, threshold=SIMILARITY_THRESHOLD
        )

        write_similarity_matrix(
            matrix=similarity_matrix,
            output_path=OUTPUT_DIR / "vector" / topic_path.with_suffix(".txt").name,
        )

        graph = build_sentence_graph(
            similarity_matrix,
            SIMILARITY_THRESHOLD,
        )

        draw_sentence_graph(
            graph=graph,
            output_path=OUTPUT_DIR / "vector" / topic_path.with_suffix(".png").name,
        )

        pagerank_scores, iterations = calculate_pagerank(
            graph,
            damping=PAGERANK_DAMPING,
            tolerance=PAGERANK_TOLERANCE,
            max_iterations=PAGERANK_MAX_ITERATIONS,
        )

        selected_sentences = rank_sentences_by_pagerank(
            sentences, pagerank_scores, top_k=TOP_K
        )

        # selected_sentences = select_sentences(
        #     sentences=sentences,
        #     pagerank_scores=pagerank_scores,
        #     similarities=similarity_matrix,
        #     max_summary_words=MAX_SUMMARY_WORDS,
        #     use_mmr=USE_MMR,
        #     mmr_lambda=MMR_LAMBDA,
        # )

        # for rank, sentence in enumerate(ranked_sentences, start=1):
        #     print(f"Rank: {rank}")
        #     print(f"Sentence index: {sentence['index']}")
        #     print(f"PageRank score: {sentence['score']:.8f}")
        #     print(f"Content: {sentence['content']}")
        #     print("-" * 80)

        output_path = OUTPUT_DIR / topic_path.name

        with open(output_path, "w", encoding="utf-8") as output_file:
            for sentence in selected_sentences:
                output_file.write(sentence["tagged_content"])
                output_file.write("\n")

        print(f"Đã ghi kết quả: {output_path}")


if __name__ == "__main__":
    main()
