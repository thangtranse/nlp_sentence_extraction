# Template execution contract

- Reference: `/Users/thangtran/Downloads/cau-truc-tieu-luan-hutech.docx`
- SHA-256: `102b60260797a88ca56026ca5c81380a663b32812da33bba02e5cdbb8941a5dd`
- Reference render: `/tmp/nlp-report-template` (12 pages)
- Page system: A4 portrait, two sections, 1-inch margins on all sides; section 2 has an independent footer.
- Front matter: preserve the HUTECH cover, instructor-comment page, table-of-contents page, list of abbreviations, list of figures, and list of tables.
- Typography: source uses Times New Roman-like academic styling, centered cover blocks, black headings, justified body text.
- Recurring furniture: section-2 footer contains `Mục | PAGE`; preserve and refresh page fields on open.
- Editable slots: replace the sample topic on the cover; preserve blank student/lecturer metadata; replace the sample chapter outline from the first Heading 1 onward; populate abbreviation/figure/table lists.
- Content flow: overview; theoretical basis; proposed method; implementation and experiments; conclusions and future work; references.
- Fidelity gates: retain A4 geometry, front-matter order, black academic visual system, heading hierarchy, and footer treatment. The reference file must remain unchanged.
- Named deviations: the sample IR/PhoBERT outline is replaced with the approved graph-based extractive-summarization report; figures and tables are added; the TOC is an update-on-open Word field.
