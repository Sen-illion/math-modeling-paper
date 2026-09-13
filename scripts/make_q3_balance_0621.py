"""6月21日 Q3 单幅能量平衡堆叠图.

一张图同时呈现：负荷、储能充电、光伏（利用+弃光）、调整购电、储能放电、
计划购电（虚线）、储电量 SOC（右轴）。

能量平衡（数据中严格成立）：
    负荷 + 充电 = 光伏利用 + 调整购电 + 储能放电
    光伏总出力 = 光伏利用 + 弃光

输入：
    assets/tables/q3_figure14_20250621/plot_data_10min.csv
    assets/tables/q3_figure14_20250621/soc_145_points.csv
输出：
    figures/fig_q3_balance_0621.{png,pdf,svg}
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
    "pv": "#E6C229",         # 光伏出力（ColorBrewer 暖黄）
    "curtail_face": "#FCF3C9",  # 弃光底色
    "curtail_edge": "#CCA02D",  # 弃光斜纹
    "purchase": "#8DA0CB",   # 调整购电（ColorBrewer 蓝紫）
    "discharge": "#E85D5D",  # 储能放电（玫瑰红）
    "charge": "#C8D4D9",     # 储能充电（冷灰蓝）
    "load": "#1C2024",       # 负荷线（近黑）
    "plan": "#B3B3B3",       # 计划购电（浅灰虚线）
    "soc": "#4B5563",        # SOC（钢灰）
    "limit": "#C4A35A",
    "night": "#F4F6F9",
    "ink": "#1C2024",
    "muted": "#5B6770",
    "grid": "#E7EAEE",
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
            "legend.fontsize": 8,
            "axes.linewidth": 0.7,
            "axes.edgecolor": "#334155",
            "axes.labelcolor": C["ink"],
            "xtick.color": "#334155",
            "ytick.color": "#334155",
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
    font = pick_font()
    apply_style(font)

    df = pd.read_csv(DATA_DIR / "plot_data_10min.csv")
    soc_df = pd.read_csv(DATA_DIR / "soc_145_points.csv")

    t = df["hour_start"].to_numpy(float)
    load = df["load_kw"].to_numpy(float)
    pv = df["pv_kw"].to_numpy(float)
    cur = df["curtailed_pv_kw"].to_numpy(float)
    pv_used = pv - cur
    adj = df["adjusted_purchase_kw"].to_numpy(float)
    dis = df["discharge_kw"].to_numpy(float)
    ch = df["charge_kw"].to_numpy(float)
    plan = df["planned_purchase_kw"].to_numpy(float)
    price = df["price_yuan_per_kwh"].to_numpy(float)
    soc = soc_df["soc_kwh"].to_numpy(float)
    if len(soc) == len(t) + 1:
        soc = soc[:-1]
    soc_min = float(soc_df["soc_min_kwh"].iloc[0])
    soc_max = float(soc_df["soc_max_kwh"].iloc[0])
    demand = load + ch  # 总需求线 = 负荷 + 充电

    total_cost = float(df["total_cost_yuan"].sum())
    cur_kwh = float(df["curtailed_pv_kwh"].sum())
    day_idx = np.where(pv > 1.0)[0]
    day_start, day_end = float(t[day_idx[0]]), float(t[day_idx[-1]])

    fig, ax = plt.subplots(figsize=(160 / 25.4, 92 / 25.4))
    fig.subplots_adjust(left=0.085, right=0.90, top=0.96, bottom=0.32)

    # 夜间底纹
    ax.axvspan(0, day_start, color=C["night"], lw=0, zorder=0)
    ax.axvspan(day_end, 24, color=C["night"], lw=0, zorder=0)
    ax.grid(axis="y", color=C["grid"], lw=0.55, zorder=0)

    # ---------- 供给侧堆叠（自下而上：光伏 → 购电 → 放电） ----------
    ax.fill_between(t, 0, pv, color=C["pv"], alpha=0.92, lw=0, zorder=2, label="光伏出力")
    # 弃光：光伏带中高出需求线的部分（斜纹覆盖）
    ax.fill_between(
        t, demand, pv, where=pv > demand,
        facecolor=C["curtail_face"], alpha=1.0, hatch="///",
        edgecolor=C["curtail_edge"], linewidth=0.0, zorder=3, label="弃光",
    )
    # 调整购电：光伏顶 → +购电
    ax.fill_between(t, pv, pv + adj, color=C["purchase"], alpha=0.95, lw=0, zorder=2, label="调整购电")
    # 储能放电：+购电 → 需求线
    ax.fill_between(t, pv + adj, demand, color=C["discharge"], alpha=0.95, lw=0, zorder=2, label="储能放电")

    # ---------- 需求侧 ----------
    # 充电带：负荷线 → 负荷+充电
    ax.fill_between(t, load, demand, color=C["charge"], alpha=0.85, lw=0, zorder=2, label="储能充电")
    ax.plot(t, load, color=C["load"], lw=1.8, zorder=5, label="小区负荷")
    ax.plot(t, plan, color=C["plan"], lw=1.1, ls=(0, (5, 3)), zorder=4, label="计划购电")

    # ---------- SOC 右轴 ----------
    axr = ax.twinx()
    axr.plot(t, soc, color=C["soc"], lw=1.4, zorder=4, label="储电量 $E_t$（右轴）")
    axr.set_ylim(0, soc_max + 2200)
    axr.set_yticks([0, 4000, 8000, 12000])
    axr.set_ylabel("储电量 / kWh", fontsize=9, color=C["soc"], labelpad=10)
    axr.tick_params(colors=C["soc"], labelsize=8)
    axr.spines["right"].set_color(C["soc"])
    axr.spines["right"].set_linewidth(0.7)
    axr.spines["top"].set_visible(False)

    # 峰值与关键节点标注
    pv_peak_h, pv_peak = float(t[pv.argmax()]), float(pv.max())
    ax.scatter([pv_peak_h], [pv_peak], s=14, color=C["pv"], zorder=6, edgecolor="white", linewidth=0.6)
    ax.annotate(
        f"光伏峰 {pv_peak:.0f} kW", xy=(pv_peak_h, pv_peak),
        xytext=(pv_peak_h - 6.2, pv_peak + 400), fontsize=8, color=C["ink"],
        ha="left", va="bottom",
        arrowprops=dict(arrowstyle="-", color=C["pv"], lw=0.7, shrinkA=2, shrinkB=3),
    )
    cur_max_h, cur_max = float(t[cur.argmax()]), float(cur.max())
    ax.annotate(
        f"SOC 充满后弃光 {cur_max:.0f} kW",
        xy=(cur_max_h, demand[cur.argmax()] + cur_max * 0.55),
        xytext=(cur_max_h - 7.6, cur_max + 1250), fontsize=8, color=C["ink"],
        ha="left", va="center",
        arrowprops=dict(arrowstyle="->", color=C["muted"], lw=0.8, shrinkA=2, shrinkB=2),
    )
    # 晚高峰放电削峰
    net = load - pv
    net_peak_h, net_peak = float(t[net.argmax()]), float(net.max())
    ax.annotate(
        f"晚高峰放电削峰 {net_peak:.0f} kW",
        xy=(net_peak_h, demand[net.argmax()]),
        xytext=(net_peak_h - 2.2, demand[net.argmax()] + 2800), fontsize=8, color=C["ink"],
        ha="right", va="center",
        arrowprops=dict(arrowstyle="->", color=C["muted"], lw=0.8, shrinkA=2, shrinkB=2),
    )

    ax.set_ylabel("功率 / kW")
    ax.set_xlabel("时间 / h")
    ax.set_xlim(0, 24)
    ax.set_xticks(np.arange(0, 25, 2))
    ax.set_ylim(0, max(demand.max(), pv.max()) * 1.12)
    ax.tick_params(length=3.0, width=0.7)

    # 图例：主轴 + 右轴句柄合并，置于图下方两行
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = axr.get_legend_handles_labels()
    fig.legend(
        h1 + h2, l1 + l2, loc="lower center", bbox_to_anchor=(0.5, 0.05),
        ncol=4, frameon=False, handlelength=1.7, columnspacing=1.4,
    )

    # 底部摘要
    cost_text = (
        f"全天无紧急购电，总费用 {total_cost:.2f} 元；弃光 {cur_kwh:.0f} kWh（集中于 SOC 充满后的午间）"
    )
    fig.text(0.5, 0.17, cost_text, ha="center", va="bottom", fontsize=8, color=C["muted"])

    ASSET_FIG_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf", "svg"):
        dest = FIGURES_DIR / f"fig_q3_balance_0621.{ext}"
        fig.savefig(dest, bbox_inches="tight", pad_inches=0.03)
        shutil.copyfile(dest, ASSET_FIG_DIR / f"fig_q3_balance_0621.{ext}")

    plt.close(fig)
    print("wrote fig_q3_balance_0621 to", FIGURES_DIR)


if __name__ == "__main__":
    main()
