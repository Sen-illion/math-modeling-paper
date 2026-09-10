# 全国大学生数学建模竞赛 LaTeX 模板（2026 提交版）

本仓库是 Overleaf 论文源码根目录，基于 `cumcmthesis` 模板整理。`main.tex` 与 `cumcmthesis.cls` 必须位于同一级。

## 写作与 Overleaf 同步

论文只在本仓库修改。推送到 `main` 后，GitHub Action 会同步到 Overleaf 网页。不要改建模仓库里的 `paper/`。

队员：

1. 向仓库所有者申请本仓库的 **Write** 权限。
2. `git clone https://github.com/Sen-illion/math-modeling-paper.git`
3. 用 Cursor / Codex 打开这个文件夹，只改 `.tex`，不要在 Overleaf 网页改正文。
4. 提交后只推 GitHub：`git pull --rebase`，然后 `git push origin main`。

仓库所有者：

1. Overleaf **Account Settings → Git Integration** 生成 token。
2. GitHub 仓库 **Settings → Secrets and variables → Actions** 新增 `OVERLEAF_GIT_TOKEN`。
3. 把队员加成 GitHub Write 协作者；Overleaf 项目加成 Viewer，仅用于看 PDF。
4. 网页端只编译、不改正文。同一时间不要两人改同一个文件。

## 入口文件

- `main.tex`：电子版论文入口，使用 `withoutpreface`，不输出承诺书和编号专用页。
- `main_print.tex`：纸质版论文入口，保留承诺书和编号专用页。
- `common_setup.tex`：公共宏包、题目信息和队伍信息。
- `paper_body.tex`：摘要、正文入口、AI 工具声明、参考文献和附录。
- `sections/`：各章节内容文件。
- `cumcmthesis.cls`：原模板类文件，除非必要不要修改。

## 编译

Overleaf 的 Compiler 选择 **XeLaTeX**。电子版从 `main.tex` 编译并下载 PDF；纸质版打印时从 `main_print.tex` 编译。正文不设目录，正文不超过 30 页；附录应列出支撑材料和完整可运行代码。使用 AI 时，应在参考文献前保留真实的 AI 工具使用声明，并准备 AI 使用详情 PDF。

详细说明见 `README_01_快速开始.md`、`README_02_写作与文件组织.md` 和 `README_03_提交检查.md`。
