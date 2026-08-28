from pathlib import Path
import re

from bs4 import BeautifulSoup

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "being",
    "but",
    "by",
    "for",
    "from",
    "had",
    "has",
    "have",
    "he",
    "her",
    "hers",
    "him",
    "his",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "no",
    "not",
    "of",
    "on",
    "or",
    "our",
    "ours",
    "she",
    "so",
    "that",
    "the",
    "their",
    "theirs",
    "them",
    "there",
    "they",
    "this",
    "those",
    "to",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "will",
    "with",
    "would",
    "you",
    "your",
    "said",
    "about",
    "after",
    "all",
    "also",
    "before",
    "could",
    "more",
    "most",
    "other",
    "over",
    "than",
    "then",
    "up",
}

TOKEN_PATTERN = re.compile(r"[a-z]+(?:'[a-z]+)?|\d+")


def preprocess(text: str) -> list[str]:
    all_tokens = TOKEN_PATTERN.findall(text.lower())

    filtered_tokens: list[str] = []

    for token in all_tokens:
        if token not in STOP_WORDS:
            filtered_tokens.append(token)

    return filtered_tokens


def read_topic(topic_path: Path) -> list[dict]:
    file_content = topic_path.read_text(encoding="utf-8")

    soup = BeautifulSoup(file_content, "html.parser")

    sentences: list[dict] = []

    for tag in soup.find_all("s"):
        content = tag.get_text().strip()

        if len(content) == 0:
            continue

        tokens = preprocess(content)

        sentence = {}
        sentence["docid"] = str(tag.get("docid", ""))

        get_num = tag.get("num", "")
        if isinstance(get_num, str):
            get_num = int(get_num)
        else:
            get_num = 0

        sentence["num"] = get_num

        get_wdcount = tag.get("wdcount", "")

        if isinstance(get_wdcount, str):
            get_wdcount = int(get_wdcount)
        else:
            get_wdcount = len(content.split())

        sentence["wdcount"] = get_wdcount

        sentence["content"] = content
        sentence["tagged_content"] = str(tag)
        sentence["token"] = tokens
        sentence["source_index"] = len(sentences)

        sentences.append(sentence)

    return sentences
