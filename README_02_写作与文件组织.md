# 02｜写作与文件组织

## 推荐顺序

1. 在 `sections/problem_restatement.tex` 中重述题目；
2. 在 `sections/assumptions_symbols.tex` 中统一假设、变量和单位；
3. 在 `sections/data_preprocessing.tex` 中记录数据处理；
4. 按实际问题数填写 `qx.tex`，并在 `sections/questions.tex` 中维护顺序；
5. 在 `overall_analysis.tex` 中比较三问结果；
6. 在 `conclusion.tex` 中逐问给出结论；
7. 最后填写参考文献、AI 工具使用声明和附录文件列表。

## 图表和交叉引用

最终进入论文的图片放入 `paper/assets/figures/`，表格源文件放入 `paper/assets/tables/`，文件名使用英文、数字和下划线；不要使用中文文件名。每张图表都要有 `caption` 和唯一的 `label`，正文使用 `\cref{fig:xxx}` 或 `\cref{tab:xxx}` 引用。`paper/figures/` 仅作为 LaTeX 编译资源目录，定稿前应复制经过核验的版本。

## 参考资料

参考论文、报告和数据源说明放入 `paper/assets/references/`；阅读摘要、出处、可引用结论和适用问题放入 `paper/assets/literature_notes/`。不要只把网页链接散落在聊天记录中。

## 结果来源

正文中的数值必须来自已运行、已检查的结果文件。不要手工修改冻结结果，也不要把聊天中的试算数字直接粘贴到论文。

## 并行协作

Q1 到 Qn 可以分别编辑各自的章节和结果目录，但公共符号、单位、数据口径和最终 `main.tex` 整合必须统一复核。任何影响方法或结果的修改必须提交并推送 GitHub 后，才能交给论文作者或 Codex 使用。
