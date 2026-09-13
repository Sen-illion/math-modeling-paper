# Q4-3 费用结构与日费用分布图的数据

`q43_daily_costs.csv` 为三种策略在 2025-02-01 至 2025-12-31 的逐日总费用，共 334 行。

- `date`：日历日期。
- `N0`、`LA`、`M0L`：对应策略当天总费用，单位为元；绘图时除以 10000，显示为万元。
- 来源：建模仓库 `results/Q4/q43_{N0,LA,M0L}_daily.csv` 的 `total_cost` 列，按相同日期逐行复制，没有重新求解或调整数值。
- 来源版本、原文件指纹及全年总额见 `../../figures/q4_daily_cost_distribution_provenance.json`。

`q43_N0_daily.csv`、`q43_LA_daily.csv`、`q43_M0L_daily.csv` 是同一来源版本的完整日记录，用于从 `total_cost` 和 `emergency_cost` 重绘费用结构。非紧急费用等于二者之差，包含计划购电与调整结算，不等同于 `plan_cost` 单列。

运行 `python scripts/Q4/make_figure16_readable.py` 生成图 16 的两块图件；`python scripts/Q4/make_daily_cost_distribution.py` 只更新日费用分布。需要 NumPy、Matplotlib 及 SimSun 字体。PNG/PDF/SVG 同时输出至 `assets/figures/` 与 `figures/`，正文使用 PDF。

两块图在正文上下通栏放置，宽度均为 160 mm；费用结构高 112 mm，日费用分布高 59 mm。三种策略沿用原图配色及 N0、LA、M0L 顺序，图例为 9 pt；散点横向抖动使用固定种子 42，仅用于显示。
