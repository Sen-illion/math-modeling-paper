"""Rebuild Q4-3 panel (b) at its 76.8 mm manuscript width.

Inputs: assets/tables/Q4/q43_daily_costs.csv (yuan, 334 dates per strategy).
Outputs: fixed-canvas PNG/PDF/SVG in assets/figures and PNG/PDF in figures.
Requires Python 3, NumPy, Matplotlib, and the manuscript's SimSun font.
Run from any directory: python scripts/Q4/make_daily_cost_distribution.py
"""

from __future__ import annotations

import csv
from pathlib import Path
import shutil

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
KEYS = ("N0", "LA", "M0L")
COLORS = {"N0": "#4E79A7", "LA": "#F28E2B", "M0L": "#59A14F"}
WIDTH_MM = 76.8  # 0.48 of the manuscript's 160 mm text width.
HEIGHT_MM = WIDTH_MM * 3877 / 4197  # Same ratio as panel (a)'s existing PNG.
FONT = "SimSun"
STEM = "q4_daily_cost_distribution"


def make_figure():
    font_manager.findfont(FONT, fallback_to_default=False)
    plt.rcParams.update({
        "font.family": FONT,
        "font.size": 5.5,
        "axes.labelsize": 5.5,
        "xtick.labelsize": 5.0,
        "ytick.labelsize": 5.0,
        "legend.fontsize": 4.8,
        "mathtext.fontset": "stix",
        "axes.unicode_minus": True,
        "axes.linewidth": 0.55,
        "axes.edgecolor": "#444444",
        "axes.axisbelow": True,
        "xtick.major.size": 2,
        "ytick.major.size": 2,
        "xtick.major.width": 0.45,
        "ytick.major.width": 0.45,
        "xtick.major.pad": 1.6,
        "ytick.major.pad": 1.6,
        "axes.labelpad": 2.0,
        "figure.dpi": 160,
        "savefig.dpi": 600,
        "savefig.bbox": None,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    })
    with (ROOT / "assets/tables/Q4/q43_daily_costs.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 334 or len({row["date"] for row in rows}) != 334:
        raise ValueError("Expected 334 distinct calendar dates")
    values = {k: np.asarray([float(row[k]) / 10000 for row in rows]) for k in KEYS}

    fig = plt.figure(figsize=(WIDTH_MM / 25.4, HEIGHT_MM / 25.4))
    box_ax = fig.add_axes((0.16, 0.61, 0.82, 0.35))
    ecdf_ax = fig.add_axes((0.16, 0.115, 0.82, 0.35))
    axes = (box_ax, ecdf_ax)
    for ax in axes:
        ax.grid(color="#E5E5E5", linewidth=0.4)

    boxes = box_ax.boxplot(
        [values[k] for k in KEYS],
        patch_artist=True,
        widths=0.5,
        showfliers=False,
        medianprops={"color": "#222222", "linewidth": 0.85},
        whiskerprops={"linewidth": 0.65},
        capprops={"linewidth": 0.65},
    )
    rng = np.random.default_rng(42)
    tick_labels = []
    for i, k in enumerate(KEYS):
        y = values[k]
        boxes["boxes"][i].set(facecolor=COLORS[k], edgecolor=COLORS[k], alpha=0.30)
        box_ax.scatter(
            rng.normal(i + 1, 0.055, len(y)), y,
            s=1.1, color=COLORS[k], alpha=0.35, linewidths=0,
        )
        tick_labels.append(f"{k}\n均值 {y.mean():.2f}\n中位 {np.median(y):.2f}")
    box_ax.set_xticks((1, 2, 3), tick_labels)
    box_ax.set_ylim(0, 18.2)
    box_ax.set_yticks((0, 5, 10, 15))
    box_ax.set_ylabel("日总成本（万元）")

    for k in KEYS:
        x = np.sort(values[k])
        probability = np.arange(1, len(x) + 1) / len(x)
        p90 = np.percentile(x, 90)
        ecdf_ax.plot(
            x, probability, color=COLORS[k], linewidth=1.0,
            label=f"{k}（$P_{{90}}={p90:.2f}$）",
        )
        ecdf_ax.plot((p90, p90), (0, 0.9), color=COLORS[k], linestyle=":", linewidth=0.65)
    ecdf_ax.axhline(0.9, color="#888888", linestyle="--", linewidth=0.55)
    ecdf_ax.set_xlim(0, 18.2)
    ecdf_ax.set_ylim(0, 1.03)
    ecdf_ax.set_xticks((0, 5, 10, 15))
    ecdf_ax.set_yticks((0, 0.5, 1.0))
    ecdf_ax.set_xlabel("日总成本（万元）")
    ecdf_ax.set_ylabel(r"累积概率 $F(x)$")
    ecdf_ax.legend(
        loc="lower right", frameon=True, facecolor="white", edgecolor="#D5D5D5",
        handlelength=1.35, handletextpad=0.4, borderpad=0.4, labelspacing=0.4,
    )
    return fig, axes


def export_figure(fig):
    assets = ROOT / "assets/figures"
    assets.mkdir(parents=True, exist_ok=True)
    for extension in ("png", "pdf", "svg"):
        fig.savefig(assets / f"{STEM}.{extension}")
    svg = assets / f"{STEM}.svg"
    svg.write_text(
        "\n".join(line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines()) + "\n",
        encoding="utf-8",
    )
    for extension in ("png", "pdf"):
        shutil.copyfile(assets / f"{STEM}.{extension}", ROOT / "figures" / f"{STEM}.{extension}")


if __name__ == "__main__":
    figure, _ = make_figure()
    export_figure(figure)
    plt.close(figure)
