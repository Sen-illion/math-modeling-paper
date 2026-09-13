"""6月21日 Q3 全天能量流向桑基图.

供给侧（左）→ 需求侧（右）：
    光伏出力 → 小区负荷 / 储能充电 / 弃光
    购电     → 小区负荷 / 储能充电
    储能放电 → 小区负荷

路径归属按每个 10 分钟时段逐段推算（光伏优先自用），
全天能量平衡严格成立（|供给-需求| < 1e-9 kWh）。

输入：
    assets/tables/q3_figure14_20250621/plot_data_10min.csv
输出：
    figures/fig_q3_sankey_0621.{png,pdf,svg}
"""

from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.path import Path as MplPath

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "assets" / "tables" / "q3_figure14_20250621"
FIGURES_DIR = REPO_ROOT / "figures"
ASSET_FIG_DIR = REPO_ROOT / "assets" / "figures"
FONT_PATH = REPO_ROOT / "simsun.ttc"

GOLD = "#E6C229"
BLUE = "#6F9EC9"
RED = "#E85D5D"
INK = "#3A4148"
TEAL = "#8FB0AA"
TAN = "#D3B67A"

STEP_KWH = 1.0 / 6.0  # 10 min


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
            "axes.unicode_minus": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "savefig.dpi": 400,
            "savefig.facecolor": "white",
            "figure.facecolor": "white",
        }
    )


def ribbon(ax, x0, y0a, y0b, x1, y1a, y1b, color, alpha=0.45):
    """两条三次贝塞尔曲线围成的能带."""
    cx0 = x0 + (x1 - x0) * 0.45
    cx1 = x1 - (x1 - x0) * 0.45
    verts = [
        (x0, y0a),
        (cx0, y0a), (cx1, y1a), (x1, y1a),
        (x1, y1b),
        (cx1, y1b), (cx0, y0b), (x0, y0b),
        (x0, y0a),
    ]
    codes = [
        MplPath.MOVETO,
        MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
        MplPath.LINETO,
        MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
        MplPath.CLOSEPOLY,
    ]
    ax.add_patch(mpl.patches.PathPatch(MplPath(verts, codes), facecolor=color, edgecolor="none", alpha=alpha, lw=0))


def main() -> None:
    apply_style(pick_font())

    df = pd.read_csv(DATA_DIR / "plot_data_10min.csv")
    load = df["load_kw"].to_numpy(float)
    pv = df["pv_kw"].to_numpy(float)
    cur = df["curtailed_pv_kw"].to_numpy(float)
    adj = df["adjusted_purchase_kw"].to_numpy(float)
    dis = df["discharge_kw"].to_numpy(float)
    ch = df["charge_kw"].to_numpy(float)
    pv_used = pv - cur

    # ---- 逐时段路径归属：光伏优先自用，放电只供给负荷 ----
    pv_to_load = np.minimum(pv_used, load)
    pv_to_charge = pv_used - pv_to_load
    rem_load = load - pv_to_load
    rem_charge = ch - pv_to_charge
    dis_to_load = np.minimum(dis, rem_load)
    grid_to_load = rem_load - dis_to_load
    grid_to_charge = rem_charge

    kwh = lambda a: float(a.sum() * STEP_KWH)
    flows = {
        ("光伏出力", "小区负荷"): kwh(pv_to_load),
        ("光伏出力", "储能充电"): kwh(pv_to_charge),
        ("光伏出力", "弃光"): kwh(cur),
        ("购电", "小区负荷"): kwh(grid_to_load),
        ("购电", "储能充电"): kwh(grid_to_charge),
        ("储能放电", "小区负荷"): kwh(dis_to_load),
    }

    src_order = ["光伏出力", "购电", "储能放电"]
    snk_order = ["小区负荷", "储能充电", "弃光"]
    src_total = {s: sum(v for (a, _), v in flows.items() if a == s) for s in src_order}
    snk_total = {s: sum(v for (_, b), v in flows.items() if b == s) for s in src_order + snk_order}
    total = sum(src_total.values())

    pv_kwh = kwh(pv)
    cur_kwh = kwh(cur)
    total_cost = float(df["total_cost_yuan"].sum())
    pv_util = (pv_kwh - cur_kwh) / pv_kwh * 100

    # ---- 布局（间隙按 kWh 比例换算，保证两侧总高度一致且 ≤ H） ----
    H = 100.0                # 画布逻辑高度
    gap_kwh = 2200.0       # 节点间保留的等效 kWh 间隙
    src_gap_n = len(src_order) - 1
    snk_gap_n = len(snk_order) - 1
    unit_l = H / (total + gap_kwh * src_gap_n)
    unit_r = H / (total + gap_kwh * snk_gap_n)
    gap_l = gap_kwh * unit_l
    gap_r = gap_kwh * unit_r

    x0, x1 = 3.05, 8.95      # 左右节点条中心 x
    bar_w = 0.28

    fig, ax = plt.subplots(figsize=(160 / 25.4, 102 / 25.4))
    ax.set_xlim(0, 12)
    ax.set_ylim(-7, H + 7)
    ax.axis("off")

    node_col = {"光伏出力": GOLD, "购电": BLUE, "储能放电": RED,
                "小区负荷": INK, "储能充电": TEAL, "弃光": TAN}

    # 左侧节点
    y = 0.0
    src_y = {}
    for s in src_order:
        h = src_total[s] * unit_l
        src_y[s] = (y, y + h)
        ax.add_patch(mpl.patches.Rectangle((x0 - bar_w / 2, y), bar_w, h,
                                           facecolor=node_col[s], edgecolor="none"))
        ax.text(x0 - bar_w / 2 - 0.38, y + h / 2 + 3.4, f"{s}",
                ha="right", va="center", fontsize=10.5, color="#232A31")
        ax.text(x0 - bar_w / 2 - 0.38, y + h / 2 - 3.4, f"{src_total[s]:,.0f} kWh".replace(",", ""),
                ha="right", va="center", fontsize=8.5, color="#7A838C")
        y += h + gap_l
    # 右侧节点
    y = 0.0
    snk_y = {}
    for s in snk_order:
        h = snk_total[s] * unit_r
        snk_y[s] = (y, y + h)
        ax.add_patch(mpl.patches.Rectangle((x1 - bar_w / 2, y), bar_w, h,
                                           facecolor=node_col[s], edgecolor="none"))
        ax.text(x1 + bar_w / 2 + 0.38, y + h / 2 + 3.4, f"{s}",
                ha="left", va="center", fontsize=10.5, color="#232A31")
        ax.text(x1 + bar_w / 2 + 0.38, y + h / 2 - 3.4, f"{snk_total[s]:,.0f} kWh".replace(",", ""),
                ha="left", va="center", fontsize=8.5, color="#7A838C")
        y += h + gap_r

    # 能带：同侧按节点顺序依次取条带
    src_cur = {s: src_y[s][0] for s in src_order}
    snk_cur = {s: snk_y[s][0] for s in snk_order}
    for (a, b), v in flows.items():
        h_s = v * unit_l
        h_t = v * unit_r
        y0a, y0b = src_cur[a], src_cur[a] + h_s
        y1a, y1b = snk_cur[b], snk_cur[b] + h_t
        ribbon(ax, x0 + bar_w / 2, y0a, y0b, x1 - bar_w / 2, y1a, y1b, node_col[a])
        src_cur[a] += h_s
        snk_cur[b] += h_t

    # 底部摘要
    ax.text(6.0, -5.4,
            f"光伏利用率 {pv_util:.1f}%（弃光 {cur_kwh:,.0f} kWh）    全天购电费用 {total_cost:,.0f} 元".replace(",", ""),
            ha="center", va="center", fontsize=8.5, color="#5B6770")

    ASSET_FIG_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf", "svg"):
        dest = FIGURES_DIR / f"fig_q3_sankey_0621.{ext}"
        fig.savefig(dest, bbox_inches="tight", pad_inches=0.03)
        shutil.copyfile(dest, ASSET_FIG_DIR / f"fig_q3_sankey_0621.{ext}")

    plt.close(fig)
    print("wrote fig_q3_sankey_0621 to", FIGURES_DIR)
    print("flows:", {f"{a}->{b}": round(v) for (a, b), v in flows.items()})


if __name__ == "__main__":
    main()
