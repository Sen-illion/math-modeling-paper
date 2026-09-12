# -*- coding: utf-8 -*-
"""Q3 PV forecast-error figure: typical days + intra-day MAE.

Data: 附件2 10 min PV and 附件3 hourly forecasts (cleaned in 国赛-integrate).
Alignment matches 国赛-integrate/code/figures/make_pv_forecast_error_figures.py:
forecast hour k = issue T+k; actual is the 10 min slot that starts at that clock hour.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
FIG_DIR = HERE / "figures"
ASSET_DIR = HERE / "assets" / "figures"
STEM = "fig_q3_pv_forecast_error"

CLEAN_CANDIDATES = [
    Path(r"C:/Users/Lenovo/Desktop/国赛-integrate/data_clean/Q3"),
    Path(r"C:/Users/Lenovo/Desktop/国赛/data_clean/Q3"),
]
FONT_CANDIDATES = [
    Path(r"C:/Users/Lenovo/Desktop/国赛-integrate/paper/simsun.ttc"),
    Path(r"C:/Users/Lenovo/Desktop/国赛/paper/simsun.ttc"),
]

ISSUES = (0, 6, 12, 18)
C_ISSUE = {0: "#2F5F8A", 6: "#C4A35A", 12: "#A33B3B", 18: "#5E4B73"}
LBL_ISSUE = {0: "0:00 发布", 6: "6:00 发布", 12: "12:00 发布", 18: "18:00 发布"}
INK = "#1F2933"
GRID = "#E4E7EB"
MM = 25.4


def find_clean() -> Path:
    for p in CLEAN_CANDIDATES:
        if (p / "pv_kw.csv").exists() and (p / "pv_hourly_forecast.npy").exists():
            return p
    raise FileNotFoundError("pv_kw.csv / pv_hourly_forecast.npy not found")


def pick_font() -> str:
    for p in FONT_CANDIDATES:
        if p.exists():
            mpl.font_manager.fontManager.addfont(str(p))
            return "SimSun"
    for name in ("Microsoft YaHei", "SimHei", "SimSun"):
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
            "font.size": 8.5,
            "axes.labelsize": 9.0,
            "xtick.labelsize": 8.0,
            "ytick.labelsize": 8.0,
            "legend.fontsize": 7.5,
            "axes.linewidth": 0.7,
            "axes.edgecolor": "#334155",
            "axes.labelcolor": INK,
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


def polish(ax: plt.Axes) -> None:
    ax.tick_params(length=3.0, width=0.7)
    ax.grid(axis="y", color=GRID, linewidth=0.55, zorder=0)
    ax.set_axisbelow(True)


def panel_label(ax: plt.Axes, text: str) -> None:
    ax.text(
        0.0,
        1.03,
        text,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=10,
        color=INK,
        clip_on=False,
    )


def load_aligned(clean: Path):
    pv_df = pd.read_csv(clean / "pv_kw.csv", encoding="utf-8-sig", index_col=0)
    dates = pd.to_datetime(pv_df.index)
    act = pv_df.to_numpy(dtype=float)
    fc = np.load(clean / "pv_hourly_forecast.npy")
    n_days = act.shape[0]
    if fc.shape != (n_days, 4, 24):
        raise ValueError(f"forecast shape {fc.shape}, expected {(n_days, 4, 24)}")

    act_at = np.full((n_days, 4, 24), np.nan)
    err = np.full((n_days, 4, 24), np.nan)
    tgt_hour = np.full((n_days, 4, 24), np.nan)
    for di in range(n_days):
        for ii, t0 in enumerate(ISSUES):
            for k in range(1, 25):
                h_abs = t0 + k
                if h_abs <= 23:
                    d2, h2 = di, h_abs
                else:
                    if di + 1 >= n_days:
                        continue
                    d2, h2 = di + 1, h_abs - 24
                a = act[d2, 6 * h2]
                act_at[di, ii, k - 1] = a
                err[di, ii, k - 1] = fc[di, ii, k - 1] - a
                tgt_hour[di, ii, k - 1] = h2
    return dates, act, fc, err, tgt_hour


def stats(err, tgt_hour):
    valid = ~np.isnan(err)
    day = valid & (tgt_hour >= 6) & (tgt_hour <= 19)
    e0 = err[:, 0, :]
    h0 = tgt_hour[:, 0, :]
    v0 = ~np.isnan(e0)
    d0 = v0 & (h0 >= 6) & (h0 <= 19)
    mae0_all = float(np.mean(np.abs(e0[v0])))
    mae0_day = float(np.mean(np.abs(e0[d0])))
    mae0_lead_mean = float(
        np.nanmean([np.mean(np.abs(e0[:, k][~np.isnan(e0[:, k])])) for k in range(24)])
    )
    mae_day_all = float(np.mean(np.abs(err[day])))
    day_mae_0 = np.array(
        [
            np.mean(np.abs(e0[d][d0_mask])) if np.any(d0_mask)
            else np.nan
            for d, d0_mask in (
                (di, (~np.isnan(e0[di])) & (h0[di] >= 6) & (h0[di] <= 19))
                for di in range(e0.shape[0])
            )
        ]
    )
    clear_d = int(np.nanargmin(day_mae_0))
    cloud_d = int(np.nanargmax(day_mae_0))
    return {
        "mae0_all": mae0_all,
        "mae0_day": mae0_day,
        "mae0_lead_mean": mae0_lead_mean,
        "mae_day_all": mae_day_all,
        "day_mae_0": day_mae_0,
        "clear_d": clear_d,
        "cloud_d": cloud_d,
    }


def draw(dates, act, fc, err, tgt_hour, st) -> mpl.figure.Figure:
    fig = plt.figure(figsize=(160 / MM, 128 / MM))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.05, 1.0], hspace=0.42, wspace=0.28)
    fig.subplots_adjust(left=0.08, right=0.99, top=0.90, bottom=0.10)
    axes_top = (fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]))
    ax_c = fig.add_subplot(gs[1, :])

    for ax, d, tag, lab in (
        (axes_top[0], st["clear_d"], "晴天", "(a)"),
        (axes_top[1], st["cloud_d"], "多云", "(b)"),
    ):
        tt = np.arange(144) * 10 / 60.0
        ax.plot(tt, act[d], color="#6B7280", lw=1.05, label="实测（10 min）")
        ax.plot(
            np.arange(1, 25),
            fc[d, 0, :],
            color=C_ISSUE[0],
            lw=1.4,
            marker="o",
            ms=3.2,
            label="0:00 预报（整点）",
        )
        ax.set_xlim(0, 24)
        ax.set_xticks(range(0, 25, 4))
        ax.set_xlabel("时刻 (h)")
        ax.set_ylabel("光伏功率 (kW)")
        polish(ax)
        panel_label(ax, lab)
        ax.text(
            0.98,
            0.94,
            f"{tag} {dates[d].strftime('%Y-%m-%d')}\n白天 MAE {st['day_mae_0'][d]:.0f} kW",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=7.5,
            color="#5B6770",
        )
        if ax is axes_top[0]:
            ax.legend(loc="upper left", frameon=False, fontsize=7.2)

    for ii, t0 in enumerate(ISSUES):
        mae_h = []
        for h in range(24):
            m = (~np.isnan(err[:, ii, :])) & (tgt_hour[:, ii, :] == h)
            mae_h.append(np.mean(np.abs(err[:, ii, :][m])) if m.sum() else np.nan)
        ax_c.plot(
            range(24),
            mae_h,
            color=C_ISSUE[t0],
            lw=1.45,
            marker="o",
            ms=3.0,
            label=LBL_ISSUE[t0],
        )
    ax_c.set_xlim(0, 23)
    ax_c.set_xticks(range(0, 24, 2))
    ax_c.set_xlabel("被预报时刻 (h)")
    ax_c.set_ylabel("MAE (kW)")
    ax_c.legend(loc="upper left", frameon=False, ncol=2, fontsize=7.5)
    polish(ax_c)
    panel_label(ax_c, "(c)")
    return fig


def save(fig: mpl.figure.Figure) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf", "svg"):
        dest = FIG_DIR / f"{STEM}.{ext}"
        fig.savefig(dest, bbox_inches="tight", pad_inches=0.03)
        shutil.copyfile(dest, ASSET_DIR / f"{STEM}.{ext}")
    plt.close(fig)


def main() -> None:
    apply_style(pick_font())
    dates, act, fc, err, tgt_hour = load_aligned(find_clean())
    st = stats(err, tgt_hour)
    print(
        f"0:00 all-sample MAE={st['mae0_all']:.1f} kW  "
        f"0:00 daytime MAE={st['mae0_day']:.1f} kW  "
        f"0:00 equal-weight lead MAE={st['mae0_lead_mean']:.1f} kW  "
        f"all-issue daytime MAE={st['mae_day_all']:.1f} kW"
    )
    print(
        f"clear {dates[st['clear_d']].date()} MAE={st['day_mae_0'][st['clear_d']]:.1f} kW; "
        f"cloudy {dates[st['cloud_d']].date()} MAE={st['day_mae_0'][st['cloud_d']]:.1f} kW"
    )
    save(draw(dates, act, fc, err, tgt_hour, st))
    print(f"saved {STEM}.png/pdf/svg")


if __name__ == "__main__":
    main()
