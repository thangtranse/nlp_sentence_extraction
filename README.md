```
pytest test_preprocess.py -v
```

## Tài liệu

- [Giải thích và cách chọn tham số TextRank](docs/textrank-parameters.md)
- [Thiết kế bộ phân tích tham số](docs/superpowers/specs/2026-08-20-textrank-parameter-analysis-design.md)
- [Kế hoạch triển khai bộ phân tích](docs/superpowers/plans/2026-08-20-textrank-parameter-analysis.md)

## Phân tích tham số TextRank

Bộ notebook tại [`notebooks/textrank-parameter-analysis`](notebooks/textrank-parameter-analysis) tối ưu theo exact sentence match `(docid, num)`, không sử dụng ROUGE. Thuật toán TextRank dùng Python standard library; `matplotlib` chỉ dùng để vẽ biểu đồ.

Chạy notebook theo thứ tự:

1. `01-dataset-and-baseline.ipynb`
2. `02-similarity-threshold.ipynb`
3. `03-pagerank-parameters.ipynb`
4. `04-mmr-parameters.ipynb`
5. `05-final-configuration.ipynb`

Notebook 01–04 chỉ phân tích 50 topic train. Notebook 05 chọn và khóa cấu hình trên train trước khi đánh giá đúng một lần trên 9 topic test.

Artifacts sau khi chạy:

- [Cấu hình đề xuất](data/output/textrank-parameter-analysis/05-recommended-config.json)
- [Các bảng CSV](data/output/textrank-parameter-analysis/csv)
- [Các biểu đồ PNG](data/output/textrank-parameter-analysis/charts)
