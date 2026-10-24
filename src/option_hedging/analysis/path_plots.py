"""GBM learning figures: paths, dispersion, measure choice and mean diagnostics."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def make_path_figures(physical, risk_neutral, times, time_rows, validation, *, market, preview_paths):
    """Return open figures; caller saves and closes them."""
    figures = {}
    style = {"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
             "axes.spines.right": False, "axes.titleweight": "bold", "figure.facecolor": "#f8fafc",
             "axes.facecolor": "white", "axes.labelcolor": "#334155"}
    physical_rows = [r for r in time_rows if r["measure"] == "physical"]
    neutral_rows = [r for r in time_rows if r["measure"] == "risk_neutral"]
    with plt.rc_context(style):
        fig, axes = plt.subplots(2, 1, figsize=(11, 8), layout="constrained")
        for path_id in range(preview_paths):
            axes[0].plot(times, physical[path_id], linewidth=1.1, alpha=.75)
        axes[0].set(title=f"First {preview_paths} fixed path IDs (no visual selection)",
                    xlabel="Time (years)", ylabel="Simulated stock price")
        axes[1].fill_between(times, [r["q05"] for r in physical_rows], [r["q95"] for r in physical_rows],
                             color="#008b8b", alpha=.18, label="5th–95th percentiles across paths")
        axes[1].plot(times, [r["median"] for r in physical_rows], color="#008b8b", lw=2, label="Sample median")
        axes[1].plot(times, [r["mean"] for r in physical_rows], color="#dd7935", lw=1.8, label="Sample mean")
        axes[1].plot(times, [r["theoretical_mean"] for r in physical_rows], color="#334155", ls="--", label="Theoretical mean")
        axes[1].set(title=f"All {physical.shape[0]:,} paths: dispersion grows with the horizon",
                    xlabel="Time (years)", ylabel="Simulated stock price")
        axes[1].legend(fontsize=8)
        fig.suptitle(f"GBM MARKET PATHS  |  S0={market['spot']:g}, mu={market['physical_drift']:.1%}, "
                     f"sigma={market['volatility']:.1%}\nExact transitions; shaded fan is path dispersion, not a confidence interval for the mean",
                     fontsize=13, fontweight="bold")
        figures["paths.png"] = fig

        fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.5), layout="constrained")
        for rows, name, color in ((physical_rows, "Physical (mu)", "#008b8b"),
                                  (neutral_rows, "Risk-neutral (r)", "#dd7935")):
            axes[0, 0].plot(times, [r["mean"] for r in rows], color=color, lw=2, label=name + " sample")
            axes[0, 0].plot(times, [r["theoretical_mean"] for r in rows], color=color, ls="--", alpha=.7,
                            label=name + " theory")
        axes[0, 0].set(title="Same shocks; different explicit drift", xlabel="Time (years)", ylabel="Mean stock price")
        axes[0, 0].legend(fontsize=8)
        mean = np.array([r["discounted_mean"] for r in neutral_rows])
        se = np.array([r["discounted_standard_error"] for r in neutral_rows])
        axes[0, 1].fill_between(times, mean - 1.959963984540054 * se, mean + 1.959963984540054 * se,
                                color="#5967a9", alpha=.18, label="Pointwise approximate 95% mean CI")
        axes[0, 1].plot(times, mean, color="#5967a9", label="Discounted RN sample mean")
        axes[0, 1].axhline(market["spot"], color="#334155", ls="--", lw=1, label="Theoretical expectation S0")
        axes[0, 1].set(title="RN discounted expectation stays at S0 in theory", xlabel="Time (years)", ylabel="Discounted mean price")
        axes[0, 1].legend(fontsize=8)
        bins = np.histogram_bin_edges(np.concatenate((physical[:, -1], risk_neutral[:, -1])), bins=40)
        axes[1, 0].hist(physical[:, -1], bins=bins, density=True, histtype="step", linewidth=1.8,
                        color="#008b8b", label="Physical")
        axes[1, 0].hist(risk_neutral[:, -1], bins=bins, density=True, histtype="step", linewidth=1.8,
                        color="#dd7935", label="Risk-neutral")
        axes[1, 0].set(title="Terminal distributions (paired Brownian shocks)", xlabel="Terminal stock price", ylabel="Density")
        axes[1, 0].legend(fontsize=8)
        for measure, offset, color in (("physical", -.12, "#008b8b"), ("risk_neutral", .12, "#dd7935")):
            subset = [r for r in validation if r["measure"] == measure]
            axes[1, 1].errorbar(np.array([r["repeat"] for r in subset]) + offset,
                                [r["mean"] - r["theoretical_mean"] for r in subset],
                                yerr=[1.959963984540054 * r["standard_error"] for r in subset],
                                fmt="o", ms=3, lw=.8, alpha=.8, color=color,
                                label="Physical" if measure == "physical" else "Risk-neutral")
        axes[1, 1].axhline(0, color="#334155", ls="--", lw=1)
        axes[1, 1].set(title="Independent repeats: terminal mean errors and CIs", xlabel="Repeat ID (paired within each ID)",
                        ylabel="Sample mean minus theoretical mean")
        axes[1, 1].legend(fontsize=8)
        fig.suptitle("MEASURE & VALIDATION  |  Market scenarios and pricing use different drifts\n"
                     "Intervals are pointwise / per-repeat approximations; paired measures are not independent evidence",
                     fontsize=13, fontweight="bold")
        figures["diagnostics.png"] = fig
        for figure in figures.values():
            for ax in figure.axes:
                ax.grid(alpha=.18)
    return figures
