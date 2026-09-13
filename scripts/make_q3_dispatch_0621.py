"""6月21日 Q3 储能调度运行曲线图（美化版）.

输入：
    assets/tables/q3_figure14_20250621/plot_data_10min.csv
    assets/tables/q3_figure14_20250621/soc_145_points.csv
输出：
    figures/fig_q3_dispatch_0621.{png,pdf,svg}
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

# 莫兰迪低饱和配色（与论文其他图统一）
C = {
    "load": "#5A6B85",      # 雾蓝
    "load_fill": "#8FA3C0",
    "pv": "#8FA983",        # 灰绿
    "net": "#8A8F98",       # 净负荷（灰）
    "plan": "#94A6BC",      # 计划购电（浅雾蓝）
    "adjust": "#8A5F57",    # 调整购电（灰粉）
    "save": "#8FA983",      # 少购区域
    "add": "#C49891",       # 增购区域
    "soc": "#7A6848",       # 灰棕
    "soc_fill": "#B8A47E",
    "limit": "#C4A35A",
    "price": "#B8BDC4",     # 电价辅轴
    "night": "#F1F3F6",     # 夜间底纹
    "ink": "#1F2933",
    "muted": "#5B6770",
    "grid": "#E6E9ED",
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


def merge_segs(t: np.ndarray, mask: np.ndarray, min_len: float = 0.4) -> list[tuple[float, float]]:
    """把布尔掩码合并为连续时段，过滤掉短于 min_len 小时的碎片。"""
    segs: list[tuple[float, float]] = []
    i = 0
    n = len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j + 1 < n and mask[j + 1]:
                j += 1
            if t[j] - t[i] >= min_len:
                segs.append((float(t[i]), float(t[j])))
            i = j + 1
        else:
            i += 1
    return segs


def main() -> None:
    font = pick_font()
    apply_style(font)

    df = pd.read_csv(DATA_DIR / "plot_data_10min.csv")
    soc_df = pd.read_csv(DATA_DIR / "soc_145_points.csv")

    t = df["hour_start"].to_numpy(float)
    load = df["load_kw"].to_numpy(float)
    pv = df["pv_kw"].to_numpy(float)
    plan = df["planned_purchase_kw"].to_numpy(float)
    adj = df["adjusted_purchase_kw"].to_numpy(float)
    price = df["price_yuan_per_kwh"].to_numpy(float)
    charge = df["charge_kw"].to_numpy(float)
    discharge = df["discharge_kw"].to_numpy(float)
    soc = soc_df["soc_kwh"].to_numpy(float)
    if len(soc) == len(t) + 1:
        soc = soc[:-1]
    soc_min = float(soc_df["soc_min_kwh"].iloc[0])
    soc_max = float(soc_df["soc_max_kwh"].iloc[0])
    net = load - pv

    total_cost = float(df["total_cost_yuan"].sum())
    net_peak = float(net.max())
    net_peak_h = float(t[net.argmax()])
    pv_peak = float(pv.max())
    pv_peak_h = float(t[pv.argmax()])
    load_peak = float(load.max())
    load_peak_h = float(t[load.argmax()])

    # 白天窗口（光伏>1kW）与充放电主时段
    day_idx = np.where(pv > 1.0)[0]
    day_start, day_end = float(t[day_idx[0]]), float(t[day_idx[-1]])
    chg_segs = merge_segs(t, charge > 0.01)
    dis_segs = merge_segs(t, discharge > 0.01)
    soc_full_h = float(t[np.argmax(soc >= soc_max - 1e-6)]) if (soc >= soc_max - 1e-6).any() else None

    fig, axes = plt.subplots(3, 1, sharex=True, figsize=(160 / 25.4, 158 / 25.4))
    fig.subplots_adjust(left=0.085, right=0.90, top=0.97, bottom=0.11, hspace=0.22)
    ax1, ax2, ax3 = axes

    for ax in axes:
        # 夜间底纹（跨面板统一）
        ax.axvspan(0, day_start, color=C["night"], lw=0, zorder=0)
        ax.axvspan(day_end, 24, color=C["night"], lw=0, zorder=0)
        ax.grid(axis="y", color=C["grid"], lw=0.55, zorder=0)

    # ---------- 面板1：负荷 / 光伏 / 净负荷 ----------
    ax1.fill_between(t, 0, load, color=C["load_fill"], alpha=0.16, lw=0, zorder=1)
    ax1.fill_between(t, 0, pv, color=C["pv"], alpha=0.30, lw=0, zorder=2)
    ax1.plot(t, load, color=C["load"], lw=1.6, label="小区负荷", zorder=4)
    ax1.plot(t, pv, color=C["pv"], lw=1.4, label="光伏出力", zorder=4)
    ax1.plot(t, net, color=C["net"], lw=1.1, ls=(0, (4, 3)), label="净负荷（负荷-光伏）", zorder=3)
    ax1.set_ylabel("功率 / kW")
    ax1.set_ylim(0, max(pv_peak, load_peak) * 1.32)
    ax1.legend(loc="upper right", frameon=False, ncol=1, handlelength=1.8)

    # 峰值标注：小圆点 + 引线文字
    for x, y, txt, col, dx, dy in (
        (pv_peak_h, pv_peak, f"光伏峰 {pv_peak:.0f} kW", C["pv"], -4.6, 520),
        (load_peak_h, load_peak, f"负荷峰 {load_peak:.0f} kW", C["load"], -6.4, 950),
    ):
        ax1.scatter([x], [y], s=14, color=col, zorder=6, edgecolor="white", linewidth=0.6)
        ax1.annotate(
            txt, xy=(x, y), xytext=(x + dx, y + dy),
            fontsize=8, color=C["ink"], ha="left", va="bottom",
            arrowprops=dict(arrowstyle="-", color=col, lw=0.7, shrinkA=2, shrinkB=3),
        )

    # ---------- 面板2：计划/调整购电 + 实时电价（右轴） ----------
    ax2.plot(t, plan, color=C["plan"], lw=1.2, ls=(0, (4, 2)), label="计划购电 $G^{plan}$", zorder=3)
    ax2.plot(t, adj, color=C["adjust"], lw=1.7, label="调整购电 $G^{adj}$", zorder=4)
    # 调整相对计划的增/减购电区域
    ax2.fill_between(t, adj, plan, where=adj < plan, color=C["save"], alpha=0.28, lw=0, zorder=2)
    ax2.fill_between(t, adj, plan, where=adj > plan, color=C["add"], alpha=0.45, lw=0, zorder=2)
    ax2.set_ylabel("购电功率 / kW")
    ax2.set_ylim(0, max(plan.max(), adj.max()) * 1.16)
    ax2.legend(loc="upper left", frameon=False, handlelength=1.8)
    ax2.annotate(
        "光伏大发时段，调整购电降为 0",
        xy=(13.0, 120), xytext=(16.0, 5000),
        fontsize=8, color=C["ink"], ha="left", va="center",
        arrowprops=dict(arrowstyle="->", color=C["muted"], lw=0.8, shrinkA=2, shrinkB=2),
    )

    # 电价辅轴（浅灰细线，解释购电转移的动机）
    axp = ax2.twinx()
    axp.plot(t, price, color=C["price"], lw=1.0, zorder=1)
    axp.set_ylim(0.0, 1.6)
    axp.set_yticks([0.4, 0.8, 1.2])
    axp.set_ylabel("实时电价 / (元/kWh)", fontsize=8.5, color="#98A0AA")
    axp.tick_params(colors="#98A0AA", labelsize=7.5, length=2.5)
    axp.spines["right"].set_visible(True)
    axp.spines["right"].set_color("#C9CFD6")
    axp.spines["top"].set_visible(False)

    # ---------- 面板3：储电量与充放电时段 ----------
    for a, b in chg_segs:
        ax3.axvspan(a, b, color=C["pv"], alpha=0.12, lw=0, zorder=1)
    for a, b in dis_segs:
        ax3.axvspan(a, b, color=C["add"], alpha=0.22, lw=0, zorder=1)
    ax3.fill_between(t, soc, soc_min, color=C["soc_fill"], alpha=0.18, lw=0, zorder=2)
    ax3.plot(t, soc, color=C["soc"], lw=1.7, zorder=4)
    ax3.axhline(soc_min, color=C["limit"], lw=0.9, ls="--", zorder=3)
    ax3.axhline(soc_max, color=C["limit"], lw=0.9, ls="--", zorder=3)
    ax3.text(24.3, soc_max, f"上限 {soc_max:.0f}", fontsize=7.5, color=C["muted"], va="center", clip_on=False)
    ax3.text(24.3, soc_min, f"下限 {soc_min:.0f}", fontsize=7.5, color=C["muted"], va="center", clip_on=False)
    # 直接标注 SOC 曲线，避免图例占位
    ax3.text(0.5, soc[0] + 1000, "储电量 $E_t$", fontsize=8.5, color=C["soc"], ha="left", va="bottom", clip_on=False)
    ax3.set_ylabel("储电量 / kWh")
    ax3.set_xlabel("时间 / h")
    ax3.set_xlim(0, 24)
    ax3.set_xticks(np.arange(0, 25, 2))
    ax3.set_ylim(soc_min - 900, soc_max + 1600)

    # 充/放电时段文字（放在主时段顶部）
    for a, b in chg_segs + dis_segs:
        if b - a < 1.2:
            continue
    for a, b, txt, col in (
        [(a, b, "充电", C["pv"]) for a, b in chg_segs if b - a >= 1.2]
        + [(a, b, "放电", C["adjust"]) for a, b in dis_segs if b - a >= 1.2]
    ):
        ax3.text((a + b) / 2, soc_max + 900, txt, fontsize=8.5, color=col,
                 ha="center", va="center")
    if soc_full_h is not None:
        ax3.annotate(
            f"{soc_full_h:.1f} h 充至上限",
            xy=(soc_full_h, soc_max), xytext=(soc_full_h - 5.6, soc_max - 2500),
            fontsize=8, color=C["ink"], ha="left", va="center",
            arrowprops=dict(arrowstyle="->", color=C["muted"], lw=0.8, shrinkA=2, shrinkB=2),
        )

    for ax in axes:
        ax.tick_params(length=3.0, width=0.7)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)

    # 底部摘要
    cost_text = (
        f"全天无紧急购电，总费用 {total_cost:.2f} 元；"
        f"净负荷晚高峰 {net_peak:.0f} kW（{net_peak_h:.1f} h）由储能放电削峰；"
        f"绿色带为充电时段，粉色带为放电时段"
    )
    fig.text(0.5, 0.012, cost_text, ha="center", va="bottom", fontsize=8, color=C["muted"])

    ASSET_FIG_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf", "svg"):
        dest = FIGURES_DIR / f"fig_q3_dispatch_0621.{ext}"
        fig.savefig(dest, bbox_inches="tight", pad_inches=0.03)
        shutil.copyfile(dest, ASSET_FIG_DIR / f"fig_q3_dispatch_0621.{ext}")

    plt.close(fig)
    print("wrote fig_q3_dispatch_0621 to", FIGURES_DIR)


if __name__ == "__main__":
    main()
