# 01｜快速开始

## 1. 同步到 Overleaf

克隆本仓库后，用 Cursor / Codex 打开根目录（`main.tex` 与 `cumcmthesis.cls` 必须在同一级）。改完推送到 GitHub 的 `main`，Action 会同步到 Overleaf。不要在 Overleaf 网页改正文。

## 2. 设置编译器

在 Overleaf 的 Menu 中将 Compiler 设置为 **XeLaTeX**。本模板依赖 `ctex` 和本地中文字体配置，不能使用 `pdfLaTeX`。

## 3. 编辑入口

- `main.tex`：电子版论文主文件；
- `main_print.tex`：纸质版入口的说明文件；
- `sections/`：问题重述、假设、数据、各个 Qx、综合分析和结论；问题数量按实际赛题决定；
- `cumcmthesis.cls`：模板类文件，除非明确知道后果，否则不要修改。

## 4. 最小编译检查

先填写题目、题号和摘要，再点击 Recompile。所有 `在此填写`、示例引用和示例结果都必须在提交前删除。
