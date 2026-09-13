# 图2绘图数据与复现

用途：复现论文图2“全年日电量与净负载持续曲线”的两个子图。此次修改仅压缩画布并对齐排版，保留原图的全部绘制样本、平滑方式、统计口径和配色。

数据来自建模仓库 `Sen-illion/math-modeling` 的 `problem_files/附件/附件2.xlsx`，使用原脚本 `code/figures/make_attachment_figures.py` 的绘图数组导出。源文件及数据指纹、原图统计量见 `assets/figures/figure2_layout_provenance.json`。

| 文件 | 行数 | 字段及含义 |
| --- | ---: | --- |
| `daily_energy.csv` | 365 | `day_index`：原图日序号0–364；`load_mwh`：负荷日电量，MWh；`load_ma7_mwh`、`pv_ma7_mwh`、`net_ma7_mwh`：负荷、光伏、净缺口日电量的7日均值，MWh。 |
| `net_load_duration.csv` | 720 | `duration_percent`：持续时间占比，%；`net_load_kw`：降序净负荷，kW。 |

7日均值沿用原图的居中滑动平均，窗口为7，边界处使用现有样本（`min_periods=1`）。持续曲线沿用原图从52,560个观测中每隔73个观测取一点的绘图抽样方式，CSV不是全部原始观测。每日分组沿用原描述性图件，不用于重算模型结算或更新冻结结果。

在论文仓库根目录运行：

```sh
python scripts/make_figure2_energy_panels.py
```

依赖：Python 3、NumPy、Matplotlib，以及已安装的宋体（SimSun）和 Times New Roman 字体。中文使用宋体，Times New Roman 补充数学负号等字形。

输出：`assets/figures/att2_energy_a` 和 `att2_energy_b` 的 PNG、PDF、SVG，并将 PNG、PDF 复制至 `figures/`。两图画布均为76.8 × 52 mm，坐标区位置相同；论文插入PDF，小标题由LaTeX排版。
