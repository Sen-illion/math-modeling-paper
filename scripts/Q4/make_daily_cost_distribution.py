"""Regenerate the readable Q4-3 daily cost panel at its final manuscript size."""
from make_figure16_readable import setup_style, load_data, make_distribution, export, plt

if __name__ == "__main__":
    setup_style()
    figure, _ = make_distribution(load_data())
    export(figure, "q4_daily_cost_distribution")
    plt.close(figure)
