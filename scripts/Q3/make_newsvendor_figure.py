"""Draw Q3's analytical settlement-loss illustration, not an empirical fit.

Run from any directory: python scripts/Q3/make_newsvendor_figure.py
Requires Python 3.10+, numpy and matplotlib; uses the repository's SimSun font.
"""

from pathlib import Path
import csv
import json
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
WIDTH_MM, HEIGHT_MM = 144, 55


def build_figure():
    font_file = ROOT / "simsun.ttc"
    font_manager.fontManager.addfont(str(font_file))
    font_name = font_manager.FontProperties(fname=str(font_file)).get_name()
    plt.rcParams.update({
        "font.family": font_name,
        "font.size": 9,
        "axes.labelsize": 9,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8.5,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.unicode_minus": False,
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "savefig.bbox": None,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
    })
    # e = planned purchase minus realized requirement (kWh).
    # Loss is relative to purchasing exactly the realized requirement at pi.
    # Locked: shortage adds 5*pi but saves pi; unused excess has zero salvage.
    # Revisable: shortage adds 1.5*pi but saves pi; excess refunds 0.5*pi.
    e = np.linspace(-1.2, 1.2, 241)
    locked_loss = 4 * np.maximum(-e, 0) + np.maximum(e, 0)
    open_loss = 0.5 * np.abs(e)
    fig, ax = plt.subplots(figsize=(WIDTH_MM / 25.4, HEIGHT_MM / 25.4), dpi=180)
    fig.subplots_adjust(left=0.12, right=0.975, bottom=0.235, top=0.955)
    blue, orange = "#315F87", "#B36B32"
    ax.plot(e, locked_loss, color=blue, linewidth=1.8,
            label="锁死段：参考分位 0.80")
    ax.plot(e, open_loss, color=orange, linewidth=1.8, linestyle="--",
            label="可改段：参考分位 0.50")
    ax.axvline(0, color="#A4A9AE", linewidth=0.8, linestyle=":", zorder=0)
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-0.12, 5.2)
    ax.set_xticks([-1, -0.5, 0, 0.5, 1])
    ax.set_yticks([0, 1, 2, 3, 4, 5])
    ax.set_xlabel("计划购电偏差 e（kWh；负值为缺购，正值为多购）", labelpad=5)
    ax.set_ylabel("增量损失 / π（kWh）", labelpad=5)
    ax.grid(axis="y", color="#E4E6E8", linewidth=0.6)
    ax.set_axisbelow(True)
    ax.legend(loc="upper right", frameon=False, handlelength=2.7, labelspacing=0.8)
    ax.text(-0.68, 3.9, "缺购边际损失：4π", color=blue, fontsize=8.5)
    ax.text(0.24, 1.55, "多购边际损失：π", color=blue, fontsize=8.5)
    ax.text(-1.13, 1.2, "可改段两侧：0.5π", color=orange, fontsize=8.5)
    return fig, e, locked_loss, open_loss, font_name


def main():
    fig, e, locked_loss, open_loss, font_name = build_figure()
    figure_dir = ROOT / "assets" / "figures"
    table_dir = ROOT / "assets" / "tables" / "Q3"
    figure_dir.mkdir(parents=True, exist_ok=True)
    table_dir.mkdir(parents=True, exist_ok=True)
    stem = "fig_q3_newsvendor"
    for extension in ("png", "pdf", "svg"):
        fig.savefig(figure_dir / f"{stem}.{extension}", dpi=400)
    svg_path = figure_dir / f"{stem}.svg"
    svg_path.write_text("\n".join(line.rstrip() for line in svg_path.read_text(encoding="utf-8").splitlines()) + "\n", encoding="utf-8")
    # Retain the established PNG path for previews and existing consumers.
    shutil.copyfile(figure_dir / f"{stem}.png", ROOT / "figures" / f"{stem}.png")
    with (table_dir / "q3_newsvendor_loss_curve.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["purchase_error_kwh", "locked_loss_divided_by_pi_kwh", "open_loss_divided_by_pi_kwh"])
        writer.writerows(zip(e, locked_loss, open_loss))
    metadata = {
        "question": "Q3",
        "figure_label": "fig:q3_newsvendor",
        "kind": "analytical illustration, not empirical observations or fitted costs",
        "source": "sections/q3.tex: eq:q3_cost and eq:q3_newsvendor",
        "error_definition": "e = planned purchase - realized requirement, kWh",
        "locked_loss_over_pi": "4*max(-e,0) + max(e,0)",
        "open_loss_over_pi": "0.5*abs(e)",
        "locked_reference_quantile": 4 / 5,
        "open_reference_quantile": 0.5 / (0.5 + 0.5),
        "assumptions": ["single-period comparison with exact purchasing at pi", "no storage or inter-period coupling", "unused excess in a locked period has zero salvage"],
        "claim_limit": "0.80 is a single-period reference, not a proved bound or the optimal rolling-policy quantile; q_L=0.60 is selected by January calibration",
        "canvas_mm": [WIDTH_MM, HEIGHT_MM],
        "font": font_name,
        "plot_source": "scripts/Q3/make_newsvendor_figure.py",
        "curve_values": "assets/tables/Q3/q3_newsvendor_loss_curve.csv",
        "ai_assistance": "Codex, GPT-6 family (exact build not exposed); user requested the 5pi/0.83 correction and explanation of Figures 10 and 11",
    }
    (figure_dir / "q3_newsvendor_provenance.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    plt.close(fig)


if __name__ == "__main__":
    main()
