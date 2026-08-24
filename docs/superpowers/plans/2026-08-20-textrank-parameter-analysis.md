# TextRank Parameter Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible five-notebook experiment suite that tunes the manual TextRank pipeline on DUC train topics using exact sentence Precision, selects one configuration, and evaluates it once on DUC test topics.

**Architecture:** A standard-library experiment module owns parsing, TextRank, exact-key metrics, graph diagnostics, parameter sweeps, and CSV/JSON persistence. Five generated notebooks call that module and use `matplotlib` only for charts; artifacts are written under a dedicated output namespace and the final notebook separates train selection from test evaluation.

**Tech Stack:** Python 3.9+, standard library (`collections`, `csv`, `dataclasses`, `html.parser`, `json`, `math`, `pathlib`, `re`, `statistics`, `time`), Jupyter/nbformat/nbclient, matplotlib, pytest.

**Spec:** `docs/superpowers/specs/2026-08-20-textrank-parameter-analysis-design.md`

## Global Constraints

- Do not use ROUGE.
- Match a prediction to DUC_SUM by exact `(docid, num)` key.
- Rank configurations by macro Precision, then macro F1, then lower mean redundancy, then lower mean runtime.
- Use only standard-library code for parsing, TF-IDF, cosine similarity, graph construction, PageRank, MMR, metrics, sweeps, and persistence.
- Use `matplotlib` only inside notebooks for charts.
- Keep `MAX_SUMMARY_WORDS = 100` for every quality comparison.
- Tune on 50 `data/DUC_TEXT/train` topics only; evaluate the locked configuration once on 9 `data/DUC_TEXT/test` topics.
- Preserve sorted topic order and deterministic tie-breaking; do not use random sampling.
- Do not modify `notebooks/duc-textrank-pipeline.ipynb` or its existing outputs.
- The workspace has no Git repository metadata, so task checkpoints use fresh tests and artifact checks instead of commits.

---

## File Map

- Create `notebooks/textrank-parameter-analysis/experiment_utils.py`: manual TextRank, evaluation, sweep, aggregation, and persistence APIs.
- Create `tests/test_textrank_parameter_analysis.py`: focused unit and integration tests for the shared module.
- Create `notebooks/textrank-parameter-analysis/build_notebooks.py`: deterministic notebook scaffolder containing the five reader-facing experiment narratives and chart cells.
- Create `notebooks/textrank-parameter-analysis/01-dataset-and-baseline.ipynb`: audit dataset and execute baseline.
- Create `notebooks/textrank-parameter-analysis/02-similarity-threshold.ipynb`: threshold sweep and graph-health charts.
- Create `notebooks/textrank-parameter-analysis/03-pagerank-parameters.ipynb`: PageRank quality/convergence sweep.
- Create `notebooks/textrank-parameter-analysis/04-mmr-parameters.ipynb`: MMR quality/redundancy sweep.
- Create `notebooks/textrank-parameter-analysis/05-final-configuration.ipynb`: local joint search, locked selection, and one-time test evaluation.
- Create `data/output/textrank-parameter-analysis/csv/*`: detail and aggregate tables produced by executed notebooks.
- Create `data/output/textrank-parameter-analysis/charts/*.png`: charts produced by executed notebooks.
- Create `data/output/textrank-parameter-analysis/05-recommended-config.json`: locked configuration and train/test metrics.
- Modify `README.md`: link the experiment suite and its design/parameter documents.

---

### Task 1: Manual TextRank Core

**Files:**
- Create: `notebooks/textrank-parameter-analysis/experiment_utils.py`
- Create: `tests/test_textrank_parameter_analysis.py`

**Interfaces:**
- Produces: `Sentence`, `TextRankConfig`, `TopicResult`, `PageRankConvergenceError`.
- Produces: `read_topic(path) -> list[Sentence]` and `read_reference_keys(path) -> set[tuple[str, int]]`.
- Produces: `calculate_tf`, `calculate_idf`, `l2_normalize`, `calculate_tfidf_vectors`, `cosine_similarity`.
- Produces: `build_sentence_graph(vectors, threshold) -> (graph, similarities)`.
- Produces: `calculate_pagerank(graph, damping, tolerance, max_iterations) -> (scores, iterations)`.
- Produces: `summarize_topic(path, config) -> TopicResult`.

- [ ] **Step 1: Write failing parser and TF-IDF tests**

Add tests that parse an in-memory DUC fixture through a temporary file, preserve `docid`, convert `num` to `int`, and validate a hand-computed two-document smooth IDF value:

```python
def test_read_topic_preserves_sentence_key_and_numeric_num(tmp_path):
    topic = tmp_path / "d001a"
    topic.write_text(
        '<s docid="DOC-1" num="10" wdcount="2"> Alpha beta.</s>\n',
        encoding="utf-8",
    )
    sentence = read_topic(topic)[0]
    assert sentence.key == ("DOC-1", 10)
    assert sentence.num == 10
    assert sentence.tagged_content.startswith('<s docid="DOC-1" num="10"')


def test_calculate_idf_uses_smooth_formula():
    idf = calculate_idf([("alpha", "beta"), ("alpha", "gamma")])
    assert idf["alpha"] == pytest.approx(1.0)
    assert idf["beta"] == pytest.approx(math.log(3 / 2) + 1)
```

- [ ] **Step 2: Run parser/TF-IDF tests and verify RED**

Run:

```bash
.venv/bin/python -m pytest tests/test_textrank_parameter_analysis.py -q
```

Expected: collection fails because `experiment_utils.py` or its exported names do not exist.

- [ ] **Step 3: Implement sentence parsing and sparse TF-IDF**

Implement immutable sentence/config/result models and the standard-library parser. Use these exact public fields:

```python
@dataclass(frozen=True)
class Sentence:
    docid: str
    num: int
    wdcount: int
    content: str
    tagged_content: str
    tokens: tuple[str, ...]
    source_index: int

    @property
    def key(self) -> tuple[str, int]:
        return self.docid, self.num


@dataclass(frozen=True)
class TextRankConfig:
    similarity_threshold: float = 0.10
    pagerank_damping: float = 0.85
    pagerank_tolerance: float = 1e-8
    pagerank_max_iterations: int = 1000
    max_summary_words: int = 100
    use_mmr: bool = True
    mmr_lambda: float = 0.70
```

Reuse the pipeline formulas exactly: `TF=count/len(tokens)`, `IDF=log((1+N)/(1+df))+1`, and L2-normalized sparse dictionaries.

- [ ] **Step 4: Run parser/TF-IDF tests and verify GREEN**

Run the same pytest command. Expected: parser and vector tests pass; later unimplemented tests may still fail only for their missing APIs.

- [ ] **Step 5: Write failing graph and PageRank tests**

```python
def test_graph_is_symmetric_has_no_self_loop_and_applies_threshold():
    vectors = [{"a": 1.0}, {"a": 0.8, "b": 0.6}, {"c": 1.0}]
    graph, similarities = build_sentence_graph(vectors, 0.5)
    assert graph[0] == {1: pytest.approx(0.8)}
    assert graph[1][0] == pytest.approx(0.8)
    assert graph[2] == {}
    assert all(node not in neighbors for node, neighbors in graph.items())
    assert similarities[0][2] == 0.0


def test_pagerank_redistributes_dangling_mass_and_normalizes():
    graph = {0: {1: 1.0}, 1: {0: 1.0}, 2: {}}
    scores, iterations = calculate_pagerank(graph, 0.85, 1e-10, 1000)
    assert sum(scores.values()) == pytest.approx(1.0)
    assert scores[0] == pytest.approx(scores[1])
    assert iterations < 1000


def test_pagerank_reports_non_convergence():
    graph = {0: {1: 1.0}, 1: {0: 1.0, 2: 1.0}, 2: {1: 1.0}}
    with pytest.raises(PageRankConvergenceError):
        calculate_pagerank(graph, 0.85, 1e-30, 1)
```

- [ ] **Step 6: Run graph/PageRank tests and verify RED**

Expected: failures identify missing graph and PageRank behavior, not fixture or import errors.

- [ ] **Step 7: Implement graph, PageRank, MMR, and summarization**

Use a weighted undirected adjacency list:

```python
Graph = dict[int, dict[int, float]]
```

PageRank must initialize uniformly, redistribute dangling mass uniformly, weight outgoing contributions by `edge_weight / total_outgoing_weight`, calculate L1 difference, and raise `PageRankConvergenceError` on exhaustion.

`summarize_topic` must return:

```python
@dataclass(frozen=True)
class TopicResult:
    topic: str
    selected_sentences: tuple[Sentence, ...]
    graph: Graph
    similarities: tuple[tuple[float, ...], ...]
    pagerank_scores: dict[int, float]
    pagerank_iterations: int
    elapsed_seconds: float

    @property
    def prediction_keys(self) -> tuple[tuple[str, int], ...]: ...
    @property
    def word_count(self) -> int: ...
```

Select by PageRank/MMR, skip a sentence that does not fit the remaining budget, never truncate, and sort selected sentences by `source_index` before returning.

- [ ] **Step 8: Add and pass budget/source-order tests**

Add a fixture where score order differs from source order and one candidate exceeds the remaining budget. Assert the returned word count is at most 100 and output keys are restored to source order. Run the focused test file until all Task 1 cases pass.

---

### Task 2: Exact-Key Metrics and Experiment Runner

**Files:**
- Modify: `notebooks/textrank-parameter-analysis/experiment_utils.py`
- Modify: `tests/test_textrank_parameter_analysis.py`

**Interfaces:**
- Consumes: `TextRankConfig`, `TopicResult`, `summarize_topic` from Task 1.
- Produces: `TopicMetrics`, `GraphMetrics`, `EvaluationRow`.
- Produces: `evaluate_keys`, `calculate_graph_metrics`, `calculate_redundancy`.
- Produces: `evaluate_config(input_dir, reference_dir, config, split) -> list[EvaluationRow]`.
- Produces: `aggregate_rows(rows) -> dict[str, float | int | str]`.
- Produces: `write_csv`, `read_csv`, `write_json`.

- [ ] **Step 1: Write failing exact-key metric tests**

```python
def test_exact_key_metrics_deduplicate_prediction_and_reference():
    metrics = evaluate_keys(
        [("A", 1), ("A", 1), ("B", 2)],
        {("A", 1), ("C", 3)},
    )
    assert metrics.true_positive == 1
    assert metrics.predicted == 2
    assert metrics.reference == 2
    assert metrics.precision == pytest.approx(0.5)
    assert metrics.recall == pytest.approx(0.5)
    assert metrics.f1 == pytest.approx(0.5)
```

- [ ] **Step 2: Run the focused test and verify RED**

Expected: `evaluate_keys` or `TopicMetrics` is missing.

- [ ] **Step 3: Implement exact-key and graph metrics**

Use these models:

```python
@dataclass(frozen=True)
class TopicMetrics:
    true_positive: int
    predicted: int
    reference: int
    precision: float
    recall: float
    f1: float


@dataclass(frozen=True)
class GraphMetrics:
    nodes: int
    edges: int
    density: float
    isolated_nodes: int
    isolated_ratio: float
    average_degree: float
    connected_components: int
```

Compute connected components with an explicit stack/visited set. Calculate redundancy only across distinct selected sentence pairs; return `(0.0, 0.0)` for fewer than two selected sentences.

- [ ] **Step 4: Add graph-statistics and redundancy tests, then pass them**

Use a four-node graph containing one two-node component and two isolated nodes. Assert `edges=1`, `density=1/6`, `isolated_ratio=0.5`, `average_degree=0.5`, and `connected_components=3`.

- [ ] **Step 5: Write failing directory-evaluation test**

Create two temporary topic/reference files and assert sorted topic rows, explicit `split`, all config fields, graph fields, quality fields, word count, convergence status, and elapsed time are present. Add a second case with a missing reference and assert `FileNotFoundError` names the missing topic.

- [ ] **Step 6: Implement deterministic evaluation and aggregation**

Define `EvaluationRow` with scalar CSV-safe fields. `evaluate_config` must iterate sorted regular files, require a matching reference, call `summarize_topic`, and convert non-convergence into `status="not_converged"` without aborting other topics.

`aggregate_rows` must include:

```python
{
    "eligible_topics": int,
    "converged_topics": int,
    "macro_precision": float,
    "macro_recall": float,
    "macro_f1": float,
    "mean_density": float,
    "mean_isolated_ratio": float,
    "mean_average_degree": float,
    "mean_connected_components": float,
    "mean_redundancy": float,
    "max_redundancy": float,
    "mean_word_count": float,
    "mean_budget_utilization": float,
    "mean_pagerank_iterations": float,
    "mean_runtime_seconds": float,
}
```

Macro metrics use only reference-bearing, converged topic rows. Non-converged configurations remain visible through counts/status.

- [ ] **Step 7: Implement CSV/JSON round-trip and pass Task 2 tests**

Write UTF-8 CSV with a header derived from explicit field order, not dictionary insertion accident. JSON uses `indent=2`, `sort_keys=True`, and a trailing newline. Run the full focused test file and confirm all Task 1–2 cases pass.

---

### Task 3: Parameter Sweeps and Deterministic Selection

**Files:**
- Modify: `notebooks/textrank-parameter-analysis/experiment_utils.py`
- Modify: `tests/test_textrank_parameter_analysis.py`

**Interfaces:**
- Consumes: `evaluate_config`, `aggregate_rows` from Task 2.
- Produces: `config_id(config) -> str`.
- Produces: `run_sweep(input_dir, reference_dir, configs, split) -> (detail_rows, summary_rows)`.
- Produces: `rank_configurations(summary_rows) -> list[dict]`.
- Produces: `top_unique_values(rows, field, limit) -> list`.
- Produces: `build_local_grid(thresholds, pagerank_configs, mmr_configs) -> list[TextRankConfig]`.

- [ ] **Step 1: Write failing deterministic-ranking test**

Build four synthetic summary rows proving the ordering rules:

```python
ranked = rank_configurations([
    {"config_id": "b", "macro_precision": 0.4, "macro_f1": 0.3,
     "mean_redundancy": 0.2, "mean_runtime_seconds": 1.0, "converged_topics": 50},
    {"config_id": "a", "macro_precision": 0.4, "macro_f1": 0.3,
     "mean_redundancy": 0.1, "mean_runtime_seconds": 2.0, "converged_topics": 50},
    {"config_id": "c", "macro_precision": 0.4, "macro_f1": 0.2,
     "mean_redundancy": 0.0, "mean_runtime_seconds": 0.5, "converged_topics": 50},
    {"config_id": "bad", "macro_precision": 0.9, "macro_f1": 0.9,
     "mean_redundancy": 0.0, "mean_runtime_seconds": 0.1, "converged_topics": 49},
], required_topics=50)
assert [row["config_id"] for row in ranked] == ["a", "b", "c"]
```

- [ ] **Step 2: Run ranking test and verify RED**

Expected: missing ranking API.

- [ ] **Step 3: Implement config IDs, sweeps, ranking, and local-grid deduplication**

`config_id` must include all seven config fields with stable formatting. `run_sweep` must preserve config order and topic order. `build_local_grid` must remove duplicate configurations while preserving the first occurrence.

- [ ] **Step 4: Add sweep call-count and deduplication tests**

Use `monkeypatch` only at the experiment boundary to count `evaluate_config` calls; assert each unique config executes once. Assert `USE_MMR=False` produces one configuration with `mmr_lambda=None` in report rows rather than one duplicate per lambda.

- [ ] **Step 5: Run the complete shared-module test suite**

Run:

```bash
.venv/bin/python -m pytest tests/test_textrank_parameter_analysis.py -q
```

Expected: all manual algorithm, metric, persistence, sweep, and ranking tests pass.

---

### Task 4: Build the Five Reader-Facing Notebooks

**Files:**
- Create: `notebooks/textrank-parameter-analysis/build_notebooks.py`
- Create: `notebooks/textrank-parameter-analysis/01-dataset-and-baseline.ipynb`
- Create: `notebooks/textrank-parameter-analysis/02-similarity-threshold.ipynb`
- Create: `notebooks/textrank-parameter-analysis/03-pagerank-parameters.ipynb`
- Create: `notebooks/textrank-parameter-analysis/04-mmr-parameters.ipynb`
- Create: `notebooks/textrank-parameter-analysis/05-final-configuration.ipynb`
- Modify: `tests/test_textrank_parameter_analysis.py`

**Interfaces:**
- Consumes all Task 1–3 public APIs.
- Produces the CSV, PNG, and JSON paths fixed by the spec.
- Notebook 05 consumes CSV from notebooks 02–04 and produces the final locked config.

- [ ] **Step 1: Write failing notebook-structure test**

Assert the five expected files exist, parse as nbformat 4, have unique cell IDs, use kernel `python3`, and contain markdown headings `Goal`, `Setup`, `Steps`, `Checks`, and `Takeaways`. Parse every code cell with `ast.parse` and assert only notebook code imports `matplotlib` outside the standard library and local `experiment_utils`.

- [ ] **Step 2: Run the notebook-structure test and verify RED**

Expected: notebook files are missing.

- [ ] **Step 3: Implement deterministic notebook builder**

Use `nbformat.v4.new_notebook`, `new_markdown_cell`, and `new_code_cell`. Assign explicit stable cell IDs. Each notebook must:

1. Resolve `PROJECT_ROOT` whether run from root or notebook directory.
2. Add its folder to `sys.path` and import `experiment_utils`.
3. Create `csv` and `charts` output directories.
4. Display bounded tables using a small local `print_table` helper.
5. Save every figure with `dpi=160`, `bbox_inches="tight"`, then display it.
6. Assert expected row counts/files in its Checks section.
7. Derive Takeaways text from executed values, not hard-coded claims.

- [ ] **Step 4: Implement notebook 01 audit and baseline**

Use train/test counts from the filesystem, require matching DUC_SUM files, calculate baseline metrics, and calculate the 100-word reference sentence-count ceiling by greedily fitting reference sentence word counts in ascending order. Save the four artifacts named in the spec.

- [ ] **Step 5: Implement notebook 02 threshold analysis**

Use exactly:

```python
THRESHOLDS = [0.00, 0.02, 0.05, 0.08, 0.10, 0.12, 0.15, 0.20, 0.25, 0.30]
```

Gather all off-diagonal pair similarities once per topic for histogram/percentiles. Run the threshold sweep with all other baseline parameters fixed. Save detail/summary CSV and the three required charts. Annotate the top Precision/F1 threshold.

- [ ] **Step 6: Implement notebook 03 PageRank analysis**

Read notebook 02 summary CSV, select the best threshold through `rank_configurations`, then run the Cartesian product of damping `[0.70, 0.80, 0.85, 0.90, 0.95]`, tolerance `[1e-4, 1e-6, 1e-8]`, and max iterations `[100, 300, 1000]`. Preserve `not_converged` rows. Plot quality and convergence/runtime; save the four required artifacts.

- [ ] **Step 7: Implement notebook 04 MMR analysis**

Read the best threshold/PageRank values from prior summary CSV files. Run one `USE_MMR=False` config plus `USE_MMR=True` for lambdas `[0.30, 0.50, 0.70, 0.90, 1.00]`. Plot quality and redundancy and save the four required artifacts.

- [ ] **Step 8: Implement notebook 05 local search and locked test evaluation**

Read prior summaries, select up to three thresholds, two converged PageRank configurations, and the no-MMR plus up to three MMR candidates. Run the deduplicated local grid on train, rank it, assign `recommended_config = ranked_train[0]`, then call test evaluation exactly once after that assignment. Save all five required artifacts and compare train/test metrics on the same `0–1` y-axis.

- [ ] **Step 9: Generate notebooks and pass structural tests**

Run:

```bash
.venv/bin/python notebooks/textrank-parameter-analysis/build_notebooks.py
.venv/bin/python -m pytest tests/test_textrank_parameter_analysis.py -q
```

Expected: five notebooks generated deterministically and the complete focused suite passes.

---

### Task 5: Execute Experiments, Verify Artifacts, and Document Usage

**Files:**
- Modify in place with executed outputs: all five experiment notebooks.
- Create by execution: `data/output/textrank-parameter-analysis/csv/*`.
- Create by execution: `data/output/textrank-parameter-analysis/charts/*.png`.
- Create by execution: `data/output/textrank-parameter-analysis/05-recommended-config.json`.
- Modify: `README.md`.

**Interfaces:**
- Consumes generated notebooks and all shared APIs.
- Produces the final user-facing recommendation and reproducible artifacts.

- [ ] **Step 1: Execute notebooks sequentially**

Run each with the project root as working directory:

```bash
.venv/bin/python -m jupyter nbconvert --execute --to notebook --inplace --ExecutePreprocessor.timeout=1800 notebooks/textrank-parameter-analysis/01-dataset-and-baseline.ipynb
.venv/bin/python -m jupyter nbconvert --execute --to notebook --inplace --ExecutePreprocessor.timeout=1800 notebooks/textrank-parameter-analysis/02-similarity-threshold.ipynb
.venv/bin/python -m jupyter nbconvert --execute --to notebook --inplace --ExecutePreprocessor.timeout=1800 notebooks/textrank-parameter-analysis/03-pagerank-parameters.ipynb
.venv/bin/python -m jupyter nbconvert --execute --to notebook --inplace --ExecutePreprocessor.timeout=1800 notebooks/textrank-parameter-analysis/04-mmr-parameters.ipynb
.venv/bin/python -m jupyter nbconvert --execute --to notebook --inplace --ExecutePreprocessor.timeout=1800 notebooks/textrank-parameter-analysis/05-final-configuration.ipynb
```

Expected: every command exits 0 and each notebook contains executed outputs without error tracebacks.

- [ ] **Step 2: Add artifact consistency test**

Assert every spec artifact exists and is non-empty. Read `05-recommended-config.json` and `csv/05-local-grid-summary.csv`; assert the JSON configuration matches the first ranked CSV row. Assert train topic detail has 50 unique topic names and final test detail has 9.

- [ ] **Step 3: Run full test suite and artifact check**

Run:

```bash
.venv/bin/python -m pytest -q
```

Expected: all tests pass with no failures. If Jupyter requires local ports, rerun with the required sandbox approval rather than weakening execution tests.

- [ ] **Step 4: Add README usage section**

Link the experiment folder, spec, plan, parameter guide, final JSON, CSV directory, and chart directory. Document the required notebook order and state that notebooks 01–04 tune only on train while notebook 05 locks the configuration before one-time test evaluation.

- [ ] **Step 5: Perform final evidence review**

Read the executed outputs and final JSON. Report:

- Recommended values for all seven configuration fields.
- Train macro Precision/F1.
- Test macro Precision/F1.
- Train/test gap.
- Mean redundancy and graph-health values.
- Exact number of evaluated train/test topics.
- The limitation that exact sentence matching does not measure paraphrase or semantic equivalence.

Do not claim the configuration is globally optimal; call it the best configuration among the explicitly tested candidate grid.
