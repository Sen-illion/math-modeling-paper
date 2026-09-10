# 01｜快速开始

## 1. 同步到 Overleaf

优先使用 GitHub 导入：Overleaf → **New Project → Import from GitHub** → 选择 `math-modeling-paper`。确保 `cumcmthesis.cls` 与 `main.tex` 位于同一级目录。

若未开通 GitHub 同步，可将本仓库打成 zip 后用 **Upload Project** 上传。

## 2. 设置编译器

在 Overleaf 的 Menu 中将 Compiler 设置为 **XeLaTeX**。本模板依赖 `ctex` 和本地中文字体配置，不能使用 `pdfLaTeX`。

## 3. 编辑入口

- `main.tex`：电子版论文主文件；
- `main_print.tex`：纸质版入口的说明文件；
- `sections/`：问题重述、假设、数据、各个 Qx、综合分析和结论；问题数量按实际赛题决定；
- `cumcmthesis.cls`：模板类文件，除非明确知道后果，否则不要修改。

## 4. 最小编译检查

先填写题目、题号和摘要，再点击 Recompile。所有 `在此填写`、示例引用和示例结果都必须在提交前删除。
