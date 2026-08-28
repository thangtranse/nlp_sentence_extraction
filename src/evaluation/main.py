import csv
import re
from html.parser import HTMLParser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REFERENCE_DIR = PROJECT_ROOT / "data" / "DUC_SUM"
PREDICTION_DIR = PROJECT_ROOT / "data" / "output" / "nlp-practice"
OUTPUT_DIR = PROJECT_ROOT / "data" / "output" / "evaluation"
OUTPUT_FILE = OUTPUT_DIR / "evaluation-results.csv"


class SentenceParser(HTMLParser):
    """Đọc nội dung nằm trong các thẻ <s> của file DUC_SUM."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.sentences = []
        self.current_parts = None

    def handle_starttag(self, tag, attributes):
        if tag.casefold() == "s":
            self.current_parts = []

    def handle_data(self, data):
        if self.current_parts is not None:
            self.current_parts.append(data)

    def handle_endtag(self, tag):
        if tag.casefold() != "s" or self.current_parts is None:
            return

        sentence = "".join(self.current_parts)
        if sentence.strip():
            self.sentences.append(sentence)
        self.current_parts = None


def normalize_sentence(sentence):
    """Bỏ khoảng trắng thừa và không phân biệt chữ hoa, chữ thường."""

    sentence = re.sub(r"\s+", " ", sentence)
    return sentence.strip().casefold()


def read_sentences(file_path):
    """Trả về tập các câu đã chuẩn hóa trong một file."""

    parser = SentenceParser()
    content = file_path.read_text(encoding="utf-8")
    parser.feed(content)
    parser.close()

    sentences = set()
    for sentence in parser.sentences:
        normalized_sentence = normalize_sentence(sentence)
        if normalized_sentence:
            sentences.add(normalized_sentence)
    return sentences


def calculate_metrics(predicted_sentences, expected_sentences):
    """Tính Precision, Recall và F1 từ hai tập câu."""

    correct_sentences = predicted_sentences.intersection(expected_sentences)
    correct_count = len(correct_sentences)

    precision = 0.0
    if predicted_sentences:
        precision = correct_count / len(predicted_sentences)

    recall = 0.0
    if expected_sentences:
        recall = correct_count / len(expected_sentences)

    f1 = 0.0
    if precision + recall > 0:
        f1 = 2 * precision * recall / (precision + recall)

    return {
        "predicted_count": len(predicted_sentences),
        "expected_count": len(expected_sentences),
        "correct_count": correct_count,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def evaluate_directories(prediction_dir, reference_dir):
    """Đánh giá tất cả file prediction có reference cùng tên."""

    results = []
    skipped = []

    prediction_files = sorted(prediction_dir.iterdir())
    for prediction_file in prediction_files:
        if not prediction_file.is_file():
            continue

        reference_file = reference_dir / prediction_file.name
        if not reference_file.is_file():
            skipped.append((prediction_file.name, "thiếu file mong đợi"))
            continue

        predicted_sentences = read_sentences(prediction_file)
        expected_sentences = read_sentences(reference_file)

        if not predicted_sentences:
            skipped.append((prediction_file.name, "kết quả chạy rỗng"))
            continue
        if not expected_sentences:
            skipped.append((prediction_file.name, "kết quả mong đợi rỗng"))
            continue

        metrics = calculate_metrics(predicted_sentences, expected_sentences)
        metrics["topic"] = prediction_file.name
        results.append(metrics)

    return results, skipped


def calculate_average(results):
    """Tính trung bình Precision, Recall và F1 của các topic hợp lệ."""

    if not results:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    precision_sum = 0.0
    recall_sum = 0.0
    f1_sum = 0.0

    for result in results:
        precision_sum += result["precision"]
        recall_sum += result["recall"]
        f1_sum += result["f1"]

    topic_count = len(results)
    return {
        "precision": precision_sum / topic_count,
        "recall": recall_sum / topic_count,
        "f1": f1_sum / topic_count,
    }


def find_zero_f1_topics(results):
    """Trả về danh sách topic hợp lệ không khớp câu nào với reference."""

    zero_f1_topics = []
    for result in results:
        if result["f1"] == 0.0:
            zero_f1_topics.append(result["topic"])
    return zero_f1_topics


def write_csv(results, output_file):
    """Ghi kết quả chi tiết ra CSV để dễ kiểm tra lại."""

    output_file.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "topic",
        "predicted_count",
        "expected_count",
        "correct_count",
        "precision",
        "recall",
        "f1",
    ]

    with output_file.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(results)


def main():
    if not PREDICTION_DIR.is_dir():
        raise FileNotFoundError(f"Không tìm thấy thư mục kết quả: {PREDICTION_DIR}")
    if not REFERENCE_DIR.is_dir():
        raise FileNotFoundError(f"Không tìm thấy thư mục mong đợi: {REFERENCE_DIR}")

    results, skipped = evaluate_directories(PREDICTION_DIR, REFERENCE_DIR)
    if not results:
        raise ValueError("Không có topic hợp lệ để đánh giá")

    write_csv(results, OUTPUT_FILE)
    average = calculate_average(results)
    zero_f1_topics = find_zero_f1_topics(results)

    print(f"Số topic được đánh giá: {len(results)}")
    print(f"Số topic bị bỏ qua: {len(skipped)}")
    for topic, reason in skipped:
        print(f"- {topic}: {reason}")

    print(f"Precision trung bình: {average['precision']:.4f}")
    print(f"Recall trung bình:    {average['recall']:.4f}")
    print(f"F1 trung bình:        {average['f1']:.4f}")
    print(f"Có {len(zero_f1_topics)} topic F1 bằng 0")
    for topic in zero_f1_topics:
        print(f"- {topic}")
    print(f"Đã lưu chi tiết tại: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
