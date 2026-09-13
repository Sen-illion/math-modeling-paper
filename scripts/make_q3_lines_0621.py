"""6月21日 Q3 极简运行曲线图（线图版）.

两幅共享横轴的面板：
    上：小区负荷、光伏出力、计划购电（虚线）、调整购电
    下：储电量 SOC 及上下限

风格：无填充、无底纹、无图内标注，仅顶部一行无边框图例；
     SOC 曲线端点直接标注。

输入：
    assets/tables/q3_figure14_20250621/plot_data_10min.csv
    assets/tables/q3_figure14_20250621/soc_145_points.csv
输出：
    figures/fig_q3_lines_0621.{png,pdf,svg}
"""

from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "assets" / "tables" / "q3_figure14_20250621"
FIGURES_DIR = REPO_ROOT / "figures"
ASSET_FIG_DIR = REPO_ROOT / "assets" / "figures"
FONT_PATH = REPO_ROOT / "simsun.ttc"

C = {
    "load": "#232A31",
    "pv": "#D9A23A",
    "plan": "#9AA3AD",
    "adj": "#3E7CB1",
    "soc": "#4B5563",
    "soc_fill": "#8DA0B5",
    "limit": "#B9C0C7",
    "grid": "#EBEEF1",
}


def pick_font() -> str:
    if FONT_PATH.exists():
        from matplotlib import font_manager

        font_manager.fontManager.addfont(str(FONT_PATH))
        return "SimSun"
    for name in ("Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "PingFang SC"):
        try:
            mpl.font_manager.findfont(name, fallback_to_default=False)
            return name
        except (ValueError, OSError):
            continue
    return "DejaVu Sans"


def apply_style(font: str) -> None:
    mpl.rcParams.update(
        {
            "font.family": font,
            "font.size": 9,
            "axes.labelsize": 9.5,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "legend.fontsize": 8.2,
            "axes.linewidth": 0.7,
            "axes.edgecolor": "#4A545E",
            "xtick.color": "#4A545E",
            "ytick.color": "#4A545E",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.unicode_minus": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "savefig.dpi": 400,
            "savefig.facecolor": "white",
            "figure.facecolor": "white",
        }
    )


def main() -> None:
    apply_style(pick_font())

    df = pd.read_csv(DATA_DIR / "plot_data_10min.csv")
    soc_df = pd.read_csv(DATA_DIR / "soc_145_points.csv")

    t = df["hour_start"].to_numpy(float)
    load = df["load_kw"].to_numpy(float)
    pv = df["pv_kw"].to_numpy(float)
    plan = df["planned_purchase_kw"].to_numpy(float)
    adj = df["adjusted_purchase_kw"].to_numpy(float)
    soc = soc_df["soc_kwh"].to_numpy(float)
    if len(soc) == len(t) + 1:
        soc = soc[:-1]
    soc_min = float(soc_df["soc_min_kwh"].iloc[0])
    soc_max = float(soc_df["soc_max_kwh"].iloc[0])

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(160 / 25.4, 92 / 25.4), sharex=True,
        gridspec_kw={"height_ratios": [1.0, 0.42], "hspace": 0.10},
    )
    fig.subplots_adjust(left=0.088, right=0.985, top=0.885, bottom=0.115)

    # ---- 上：功率曲线（纯线条） ----
    ax1.plot(t, load, color=C["load"], lw=1.8, label="小区负荷", solid_capstyle="round")
    ax1.plot(t, pv, color=C["pv"], lw=1.6, label="光伏出力", solid_capstyle="round")
    ax1.plot(t, plan, color=C["plan"], lw=1.1, ls=(0, (5, 3)), label="计划购电")
    ax1.plot(t, adj, color=C["adj"], lw=1.6, label="调整购电", solid_capstyle="round")
    ax1.grid(axis="y", color=C["grid"], lw=0.55)
    ax1.set_ylabel("功率 / kW")
    ax1.set_ylim(0, max(pv.max(), plan.max()) * 1.10)
    ax1.tick_params(length=3.0, width=0.7)
    ax1.legend(
        loc="lower left", bbox_to_anchor=(0.0, 1.01), ncol=4, frameon=False,
        handlelength=1.9, columnspacing=1.5, borderaxespad=0.0,
    )

    # ---- 下：储电量（浅填充 + 端点标注） ----
    ax2.fill_between(t, 0, soc, color=C["soc_fill"], alpha=0.18, lw=0)
    ax2.plot(t, soc, color=C["soc"], lw=1.7)
    ax2.axhline(soc_max, color=C["limit"], lw=0.9, ls=(0, (4, 3)))
    ax2.axhline(soc_min, color=C["limit"], lw=0.9, ls=(0, (4, 3)))
    ax2.text(0.3, soc_max + 260, f"上限 {soc_max:.0f}", fontsize=7.5, color="#7A838C", va="bottom")
    ax2.text(0.3, soc_min + 260, f"下限 {soc_min:.0f}", fontsize=7.5, color="#7A838C", va="bottom")
    ax2.text(24.3, soc[-1], "储电量", fontsize=8.5, color=C["soc"], va="center", ha="left", clip_on=False)
    ax2.grid(axis="y", color=C["grid"], lw=0.55)
    ax2.set_ylabel("储电量 / kWh")
    ax2.set_xlabel("时间 / h")
    ax2.set_xlim(0, 24)
    ax2.set_ylim(0, soc_max + 1500)
    ax2.set_xticks(np.arange(0, 25, 2))
    ax2.tick_params(length=3.0, width=0.7)

    ASSET_FIG_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf", "svg"):
        dest = FIGURES_DIR / f"fig_q3_lines_0621.{ext}"
        fig.savefig(dest, bbox_inches="tight", pad_inches=0.03)
        shutil.copyfile(dest, ASSET_FIG_DIR / f"fig_q3_lines_0621.{ext}")

    plt.close(fig)
    print("wrote fig_q3_lines_0621 to", FIGURES_DIR)


if __name__ == "__main__":
    main()
