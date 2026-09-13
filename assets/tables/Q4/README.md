# Q4-3 图15(b)的数据

`q43_daily_costs.csv` 为三种策略在 2025-02-01 至 2025-12-31 的逐日总费用，共 334 行。

- `date`：日历日期。
- `N0`、`LA`、`M0L`：对应策略当天总费用，单位为元；绘图时除以 10000，显示为万元。
- 来源：建模仓库 `results/Q4/q43_{N0,LA,M0L}_daily.csv` 的 `total_cost` 列，按相同日期逐行复制，没有重新求解或调整数值。
- 来源版本、原文件指纹及全年总额见 `../../figures/q4_daily_cost_distribution_provenance.json`。

在论文仓库运行 `python scripts/Q4/make_daily_cost_distribution.py` 可重新生成上下排列的箱线图与累计分布图。需要 NumPy、Matplotlib 及论文使用的 SimSun 字体。导出的 PNG/PDF/SVG 位于 `assets/figures/`，正文使用的 PNG/PDF 同时写入 `figures/`。

画布按最终插图尺寸 76.8 mm × 70.9444 mm 生成，与原图15(a)的纵横比一致。三种策略沿用原图配色及 N0、LA、M0L 顺序；散点横向抖动使用固定种子42，仅用于显示。
