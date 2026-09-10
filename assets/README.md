# 论文协作素材目录

这是论文写作者、绘图人员和资料整理人员共享的固定入口。新增或更新素材后，应提交并推送 GitHub，并在提交信息中写明对应问题和用途。

## 子目录

- `figures/`：可直接用于论文的 PNG、PDF、SVG 图；文件名使用英文、数字和下划线。
- `tables/`：论文表格的 CSV、XLSX、LaTeX 片段或生成脚本。
- `references/`：参考论文、报告、数据源说明和 BibTeX 文件。每份资料应有可追溯来源。
- `literature_notes/`：阅读摘要、方法对照、引用位置建议和与 Q1 到 Qn 的对应关系。

## 文件命名建议

```text
Q1_data_distribution_v1.png
Q2_baseline_comparison.csv
Qn_robustness_reference.pdf
paper_references.bib
```

## 使用规则

1. 图表必须注明数据来源、生成脚本或结果文件路径。
2. 参考资料必须记录作者、标题、年份、链接或 DOI，禁止只保存无法追溯的截图。
3. 素材不等于最终证据；论文中的数字仍以 `results/Qx/` 的验证结果为准。
4. Codex 写论文前先读取本目录的新增内容，并检查其对应的 Qx 和来源。
