"""Draw Q4-3 cost panels for a 160 mm wide manuscript slot.

Run: python scripts/Q4/make_figure16_readable.py
Requires NumPy, Matplotlib and SimSun. Inputs are the three archived daily
result CSVs in assets/tables/Q4; no model fitting or result updates occur.
"""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
import shutil

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
KEYS = ('N0', 'LA', 'M0L')
COLORS = {'N0': '#4E79A7', 'LA': '#F28E2B', 'M0L': '#59A14F'}
STYLES = {'N0': '-', 'LA': '--', 'M0L': '-.'}
LABELS = {'N0': 'N0（不调整）', 'LA': 'LA（本文）', 'M0L': 'M0L（选择性调整）'}
FONT = 'SimSun'
WIDTH_MM = 160


def setup_style():
    font_manager.findfont(FONT, fallback_to_default=False)
    plt.rcParams.update({
        'font.family': FONT, 'font.size': 9.5,
        'axes.labelsize': 9.5, 'xtick.labelsize': 9,
        'ytick.labelsize': 9, 'legend.fontsize': 9,
        'axes.linewidth': 0.7, 'axes.edgecolor': '#444444',
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.axisbelow': True, 'axes.unicode_minus': True,
        'axes.labelpad': 3, 'xtick.major.pad': 2, 'ytick.major.pad': 2,
        'xtick.major.size': 2.5, 'ytick.major.size': 2.5,
        'xtick.major.width': 0.6, 'ytick.major.width': 0.6,
        'figure.dpi': 160, 'savefig.dpi': 600,
        'savefig.bbox': None, 'svg.fonttype': 'none', 'pdf.fonttype': 42,
        'figure.facecolor': 'white', 'savefig.facecolor': 'white',
    })


def load_data():
    data = {}
    for key in KEYS:
        with (ROOT / 'assets/tables/Q4' / f'q43_{key}_daily.csv').open(
            encoding='utf-8-sig', newline=''
        ) as stream:
            rows = list(csv.DictReader(stream))
        dates = [datetime.strptime(row['date'], '%Y-%m-%d') for row in rows]
        if len(rows) != 334 or len(set(dates)) != 334:
            raise ValueError('Expected 334 unique decision dates per strategy')
        total = np.array([float(row['total_cost']) for row in rows]) / 10000
        emergency = np.array([float(row['emergency_cost']) for row in rows]) / 10000
        data[key] = {'dates': dates, 'total': total, 'emergency': emergency}
    if not all(data[k]['dates'] == data['N0']['dates'] for k in KEYS):
        raise ValueError('Strategy dates must align')
    # Independently archived daily totals used in the previous distribution plot.
    with (ROOT / 'assets/tables/Q4/q43_daily_costs.csv').open(
        encoding='utf-8', newline=''
    ) as stream:
        archived = list(csv.DictReader(stream))
    for key in KEYS:
        np.testing.assert_allclose(
            data[key]['total'], [float(row[key]) / 10000 for row in archived],
            rtol=0, atol=1e-10,
        )
    return data


def make_cost_structure(data):
    fig = plt.figure(figsize=(WIDTH_MM / 25.4, 112 / 25.4))
    axes = [fig.add_axes((0.12, bottom, 0.74, height))
            for bottom, height in ((0.66, 0.205), (0.365, 0.205), (0.09, 0.205))]
    legend = [Line2D([], [], color=COLORS[k], linestyle=STYLES[k],
                     linewidth=1.6, label=LABELS[k]) for k in KEYS]
    fig.legend(handles=legend, loc='upper center', bbox_to_anchor=(0.51, 1.0),
               ncol=3, frameon=False, columnspacing=1.2, handlelength=2.1)
    fig.legend(handles=[Patch(facecolor='#8D8D8D', label='非紧急费用'),
                        Patch(facecolor='white', edgecolor='#777777', hatch='///',
                              label='紧急购电费用')],
               loc='upper center', bbox_to_anchor=(0.50, 0.945), ncol=2,
               frameon=False, columnspacing=1.7)
    months = np.arange(2, 13)
    monthly = {}
    for i, key in enumerate(KEYS):
        source = data[key]
        date_month = np.array([d.month for d in source['dates']])
        total = np.array([source['total'][date_month == m].sum() for m in months])
        emergency = np.array([source['emergency'][date_month == m].sum() for m in months])
        monthly[key] = (total, emergency)
        x = np.arange(11) + (i - 1) * 0.25
        axes[0].bar(x, total - emergency, width=0.25, color=COLORS[key], alpha=0.9)
        axes[0].bar(x, emergency, bottom=total - emergency, width=0.25,
                    facecolor='white', edgecolor=COLORS[key], hatch='////', linewidth=0.55)
        axes[1].plot(np.arange(11), 100 * emergency / total, color=COLORS[key],
                     linestyle=STYLES[key], marker='o', markersize=2.8, linewidth=1.3)
        cumulative = np.cumsum(source['total'])
        axes[2].plot(source['dates'], cumulative, color=COLORS[key],
                     linestyle=STYLES[key], linewidth=1.3)
    pooled_share = 100 * sum(data[k]['emergency'].sum() for k in KEYS) / sum(
        data[k]['total'].sum() for k in KEYS)
    axes[1].axhline(pooled_share, color='#777777', linestyle=':', linewidth=0.8)
    axes[1].text(1.025, pooled_share / 30, f'总体\n{pooled_share:.1f}%',
                 transform=axes[1].transAxes, ha='left', va='center', color='#555555')
    for key, height in (('N0', 0.91), ('M0L', 0.62), ('LA', 0.33)):
        source = data[key]
        total = source['total'].sum()
        axes[2].text(1.025, height, f'{total:,.1f}', transform=axes[2].transAxes,
                      ha='left', va='center', color=COLORS[key], fontsize=9)
    for ax in axes:
        ax.grid(axis='y', color='#E2E2E2', linewidth=0.45)
    for ax in axes[:2]:
        ax.set_xticks(np.arange(11), [str(m) for m in months])
        ax.set_xlim(-0.65, 10.65)
        ax.set_xlabel('月份', labelpad=1)
    axes[0].set_ylim(0, 225)
    axes[0].set_yticks((0, 100, 200))
    axes[0].set_ylabel('月费用（万元）')
    axes[1].set_ylim(0, 30)
    axes[1].set_yticks((0, 10, 20, 30))
    axes[1].set_ylabel('紧急费用占比（%）')
    axes[2].set_ylim(0, 1750)
    axes[2].set_yticks((0, 800, 1600))
    axes[2].set_xlim(data['N0']['dates'][0], data['N0']['dates'][-1])
    axes[2].xaxis.set_major_locator(mdates.MonthLocator(bymonth=(2, 4, 6, 8, 10, 12)))
    axes[2].xaxis.set_major_formatter(mdates.DateFormatter('%m'))
    axes[2].set_ylabel('累计费用（万元）')
    axes[2].set_xlabel('月份（2025 年）', labelpad=1)
    return fig, axes


def make_distribution(data):
    fig = plt.figure(figsize=(WIDTH_MM / 25.4, 59 / 25.4))
    left = fig.add_axes((0.10, 0.25, 0.35, 0.70))
    right = fig.add_axes((0.615, 0.25, 0.35, 0.70))
    boxes = left.boxplot([data[k]['total'] for k in KEYS], patch_artist=True,
                         widths=0.5, showfliers=False,
                         medianprops={'color': '#222222', 'linewidth': 1.15},
                         whiskerprops={'linewidth': 0.8}, capprops={'linewidth': 0.8})
    rng = np.random.default_rng(42)
    ticks = []
    for i, key in enumerate(KEYS):
        values = data[key]['total']
        boxes['boxes'][i].set(facecolor=COLORS[key], edgecolor=COLORS[key], alpha=0.30)
        left.scatter(rng.normal(i + 1, 0.055, len(values)), values,
                     s=3, color=COLORS[key], alpha=0.35, linewidths=0)
        ticks.append(f'{key}\n均值 {values.mean():.2f}\n中位 {np.median(values):.2f}')
        x = np.sort(values)
        probability = np.arange(1, len(x) + 1) / len(x)
        p90 = np.percentile(x, 90)
        right.plot(x, probability, color=COLORS[key], linestyle=STYLES[key],
                    linewidth=1.35, label=f'{key}：{p90:.2f}')
        right.plot((p90, p90), (0, 0.9), color=COLORS[key], linestyle=':', linewidth=0.7)
    left.set_xticks((1, 2, 3), ticks)
    left.tick_params(axis='x', labelsize=8.5)
    left.set_ylim(0, 18.2)
    left.set_yticks((0, 5, 10, 15))
    left.set_ylabel('日费用（万元）')
    right.axhline(0.9, color='#777777', linestyle='--', linewidth=0.6)
    right.set(xlim=(0, 18.2), ylim=(0, 1.03), xticks=(0, 5, 10, 15),
              yticks=(0, 0.5, 1), xlabel='日费用（万元）', ylabel='累计概率')
    right.legend(title='90%分位（万元）', title_fontsize=9, loc='lower right',
                  frameon=True, facecolor='white', edgecolor='#D5D5D5',
                  borderpad=0.35, labelspacing=0.30, handlelength=1.8)
    for ax in (left, right):
        ax.grid(axis='y', color='#E2E2E2', linewidth=0.45)
    return fig, (left, right)


def export(fig, stem):
    for directory in ('assets/figures', 'figures'):
        (ROOT / directory).mkdir(parents=True, exist_ok=True)
    for extension in ('pdf', 'svg', 'png'):
        target = ROOT / 'assets/figures' / f'{stem}.{extension}'
        fig.savefig(target)
        if extension == 'svg':
            target.write_text('\n'.join(line.rstrip() for line in target.read_text(
                encoding='utf-8').splitlines()) + '\n', encoding='utf-8')
        shutil.copyfile(target, ROOT / 'figures' / target.name)


if __name__ == '__main__':
    setup_style()
    data = load_data()
    for builder, stem in ((make_cost_structure, 'q4_cost_structure'),
                          (make_distribution, 'q4_daily_cost_distribution')):
        figure, _ = builder(data)
        export(figure, stem)
        plt.close(figure)
