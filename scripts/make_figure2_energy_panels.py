"""Render Figure 2 as aligned 76.8 x 52 mm panels.

Input CSVs retain the original descriptive figure's plotted samples.
Requires Python 3, NumPy, Matplotlib, SimSun and Times New Roman fonts.
Run: python scripts/make_figure2_energy_panels.py
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

ROOT = Path(__file__).resolve().parents[1]
WIDTH_MM, HEIGHT_MM = 76.8, 52.0
AXES_RECT = (0.19, 0.22, 0.78, 0.74)
COLORS = {"load": "#2F5F8A", "pv": "#C4A35A", "net": "#A33B3B"}
MONTH_START = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)


def read_columns(filename):
    with (ROOT / "assets/tables/figure2" / filename).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {key: np.asarray([float(row[key]) for row in rows]) for key in rows[0]}


def make_figures():
    font_manager.findfont("SimSun", fallback_to_default=False)
    font_manager.findfont("Times New Roman", fallback_to_default=False)
    plt.rcParams.update({
        "font.family": ["SimSun", "Times New Roman"],
        "font.size": 7.0,
        "axes.labelsize": 7.0,
        "xtick.labelsize": 6.5,
        "ytick.labelsize": 6.5,
        "axes.labelpad": 2.5,
        "axes.linewidth": 0.65,
        "axes.edgecolor": "#334155",
        "axes.labelcolor": "#1F2933",
        "xtick.color": "#334155",
        "ytick.color": "#334155",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.unicode_minus": True,
        "axes.axisbelow": True,
        "xtick.major.size": 2.5,
        "ytick.major.size": 2.5,
        "xtick.major.width": 0.65,
        "ytick.major.width": 0.65,
        "xtick.major.pad": 2.0,
        "ytick.major.pad": 2.0,
        "figure.dpi": 160,
        "savefig.dpi": 600,
        "savefig.bbox": None,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    })
    daily = read_columns("daily_energy.csv")
    duration = read_columns("net_load_duration.csv")
    figures = []
    for stem in ("att2_energy_a", "att2_energy_b"):
        fig = plt.figure(figsize=(WIDTH_MM / 25.4, HEIGHT_MM / 25.4))
        ax = fig.add_axes(AXES_RECT)
        ax.grid(axis="y", color="#E4E7EB", linewidth=0.5)
        figures.append((stem, fig, ax))

    ax = figures[0][2]
    day = daily["day_index"]
    ax.plot(day, daily["load_mwh"], color=COLORS["load"], linewidth=0.4, alpha=0.22)
    for column, key, label in (
        ("load_ma7_mwh", "load", "负荷 7 日均值"),
        ("pv_ma7_mwh", "pv", "光伏 7 日均值"),
        ("net_ma7_mwh", "net", "净缺口 7 日均值"),
    ):
        ax.plot(day, daily[column], color=COLORS[key], linewidth=1.15, label=label)
    ax.set_xlim(0, 364)
    ax.set_ylim(0, float(daily["load_mwh"].max()) * 1.06)
    ax.set_xticks(MONTH_START, [str(i) for i in range(1, 13)])
    ax.set_yticks((0, 40, 80, 120))
    ax.set_xlabel("月份")
    ax.set_ylabel("日电量（MWh）")
    ax.legend(
        loc="lower left", frameon=False, fontsize=6.0,
        labelspacing=0.25, handlelength=1.6, borderaxespad=0.35,
    )

    ax = figures[1][2]
    x, y = duration["duration_percent"], duration["net_load_kw"]
    ax.plot(x, y, color=COLORS["net"], linewidth=1.15)
    ax.axhline(0, color="#94A3B8", linewidth=0.65, linestyle="--")
    ax.fill_between(x, y, 0, where=y >= 0, color=COLORS["net"], alpha=0.16, linewidth=0)
    ax.fill_between(x, y, 0, where=y < 0, color=COLORS["pv"], alpha=0.22, linewidth=0)
    ax.set_xlim(0, 100)
    ax.set_xticks((0, 20, 40, 60, 80, 100))
    ax.set_yticks((-6000, -3000, 0, 3000, 6000))
    ax.set_xlabel("时长占比（%）")
    ax.set_ylabel("净负荷（kW）")
    ax.grid(axis="x", color="#E4E7EB", linewidth=0.45)
    return figures


def export_figures(figures):
    assets = ROOT / "assets/figures"
    assets.mkdir(parents=True, exist_ok=True)
    for stem, fig, _ in figures:
        for extension in ("png", "pdf", "svg"):
            fig.savefig(assets / f"{stem}.{extension}")
        svg = assets / f"{stem}.svg"
        svg.write_text(
            "\n".join(line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines()) + "\n",
            encoding="utf-8",
        )
        for extension in ("png", "pdf"):
            shutil.copyfile(assets / f"{stem}.{extension}", ROOT / "figures" / f"{stem}.{extension}")


if __name__ == "__main__":
    export_figures(make_figures())
    plt.close("all")
