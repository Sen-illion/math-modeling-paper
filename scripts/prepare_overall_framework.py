"""Reflow the supplied first-slide framework for a portrait manuscript.

Requires Matplotlib and an installed Chinese font (Microsoft YaHei or Noto Sans
CJK SC). The original first slide remains in assets/figures/sources/ for tracing
the condensed labels. No additional slides or numerical results are used.
"""

import hashlib
import io
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

WIDTH_MM, HEIGHT_MM = 160, 102
INK = "#253D4C"
COLORS = {"q1": "#2A718A", "q2": "#267F89", "q3": "#3C6594", "q4": "#916323"}


def build_figure():
    available = {f.name for f in font_manager.fontManager.ttflist}
    family = next((f for f in ("Microsoft YaHei", "Noto Sans CJK SC", "SimHei")
                   if f in available), None)
    if family is None:
        raise RuntimeError("Install Microsoft YaHei or Noto Sans CJK SC to render Chinese labels.")
    plt.rcParams.update({"font.family": family, "font.size": 8.0,
                         "pdf.fonttype": 42, "svg.fonttype": "none",
                         "axes.unicode_minus": False, "savefig.bbox": None})
    fig = plt.figure(figsize=(WIDTH_MM / 25.4, HEIGHT_MM / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set(xlim=(0, WIDTH_MM), ylim=(HEIGHT_MM, 0))
    ax.axis("off")

    def box(x, y, w, h, edge, fill):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2",
                                   edgecolor=edge, facecolor=fill, linewidth=0.65))

    def text(x, y, value, size=8.0, color=INK, bold=False, ha="left"):
        return ax.text(x, y, value, fontsize=size, color=color, ha=ha, va="center",
                       fontweight="bold" if bold else "normal", linespacing=1.25)

    def arrow(start, end, color):
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=8,
                                     linewidth=0.9, color=color, shrinkA=0, shrinkB=0))

    box(2, 1, 156, 12, "#B9CBD3", "#F5F8FA")
    text(5, 4.7, "统一输入：负荷 / 光伏观测与已发布预报、电价信息", size=8.3, bold=True)
    text(5, 9.2, "按时段起点对齐 · 10 min × 144 段 / 日 · 电量 = 功率 × 1/6 h")

    cards = [
        (2, "q1", "Q1  确定性日前调度", [
            "已知电价、负荷和光伏",
            "全天 144 时段线性规划",
            "首末储电量均为 6000 kWh",
            "输出购电与充放电计划",
            "对照：无储能 / 分时贪婪"]),
        (56, "q2", "Q2  不确定日前调度", [
            "XGBoost + 光伏 7 日同刻均值",
            "净负荷残差分位 α = 0.8",
            "日前 LP；日末 2400 kWh",
            "锁定合同；保护回放 ρ = 0.625",
            "缺口按 5π 紧急购电"]),
        (110, "q3", "Q3  日内滚动调度", [
            "负荷预测 + 已发布光伏预报",
            "0 / 6 / 12 / 18 点滚动 LP",
            "48 h；分源分位 0.60 / 0.50",
            "更新剩余合同 + 贪心回放",
            "少买退 0.5π；多买付 1.5π"]),
    ]
    for x, key, heading, lines in cards:
        color = COLORS[key]
        box(x, 17, 46, 36, color, "#F8FAFC")
        text(x + 2.3, 21.8, heading, size=8.7, bold=True, color=color)
        ax.plot([x + 2, x + 44], [25.3, 25.3], color=color, linewidth=0.45, alpha=0.55)
        for n, line in enumerate(lines):
            text(x + 2.3, 29 + n * 4.6, line)
    arrow((48.5, 35), (55.5, 35), COLORS["q2"])
    arrow((102.5, 35), (109.5, 35), COLORS["q3"])

    box(2, 60, 46, 41, "#9EB7C5", "#F5F8FA")
    text(4.5, 65, "公共储能与供需约束", size=8.7, bold=True)
    for n, line in enumerate([
            "容量 12000 kWh",
            "SOC 1200–10800 kWh",
            "效率 0.9；接口 ≤ 5000 kW",
            "禁止售电，允许弃光",
            "逐时段电量平衡",
            "Q2–Q4 缺口按 5π 外购"]):
        text(4.5, 72 + n * 4.7, line)

    box(56, 60, 100, 28, "#CDB387", "#FCFAF5")
    text(106, 64.4, "Q4  波动电价：两个策略分别扩展", size=9.0,
         color=COLORS["q4"], bold=True, ha="center")
    ax.plot([106, 106], [68, 85.5], color="#D8C6A7", linewidth=0.5)
    text(58.5, 71, "Q4-2  沿用 Q2 日前策略", size=8.3, bold=True, color=COLORS["q2"])
    text(58.5, 77, "沿用 α、日末储电量与 ρ")
    text(58.5, 82.5, "预测价排计划，实际价结算")
    text(108.5, 71, "Q4-3  沿用 Q3 滚动策略", size=8.3, bold=True, color=COLORS["q3"])
    text(108.5, 77, "日内更新负荷 / 光伏")
    text(108.5, 82.5, "决策电价日内不更新")
    arrow((79, 53.5), (79, 59.5), COLORS["q2"])
    arrow((133, 53.5), (133, 59.5), COLORS["q3"])
    box(56, 90, 100, 11, "#E1CCA3", "#F7EFDD")
    text(58.5, 93.5, "电价预测：历史同刻均值 + 同星期残差均值", color=COLORS["q4"])
    text(58.5, 98, "+ 近 7 日残差均值；按当日实际电价结算", color=COLORS["q4"])
    return fig


def main():
    root = Path(__file__).resolve().parents[1]
    assets = root / "assets" / "figures"
    source = assets / "sources" / "overall_framework_slide1.pdf"
    fig = build_figure()
    for extension in ("pdf", "svg", "png"):
        buffer = io.BytesIO()
        fig.savefig(buffer, format=extension, dpi=300, facecolor="white")
        output = buffer.getvalue()
        if extension == "svg":
            output = ("\n".join(line.rstrip() for line in output.decode("utf-8").splitlines())
                      + "\n").encode("utf-8")
        for folder in (assets, root / "figures"):
            (folder / f"fig_overall_framework.{extension}").write_bytes(output)
    plt.close(fig)
    metadata = {
        "source": "sources/overall_framework_slide1.pdf",
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_slide": 1,
        "changes": "Reflow first-slide content to a compact portrait-page figure; remove decorative icons and repeated explanations while retaining methods, parameters and inheritance links.",
        "paper_placement": "Section 3.5, normal portrait page, before Q1.",
        "canvas_mm": [WIDTH_MM, HEIGHT_MM],
        "body_font_pt": 8.0,
        "purpose": "Explain the Q1-Q3 progression and the two Q4 extensions.",
        "format": "Vector PDF and editable SVG, with PNG preview.",
    }
    (assets / "fig_overall_framework_provenance.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
