"""Static research figures for Monte Carlo accuracy, calibration and engineering."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from option_hedging.pricing.monte_carlo import METHODS


COLORS = {"plain": "#64748b", "antithetic": "#008b8b", "control": "#dd7935"}
LABELS = {"plain": "Plain MC", "antithetic": "Antithetic", "control": "Stock control"}


def _subset(metrics, kind, method, strike):
    return sorted([r for r in metrics if r["kind"] == kind and r["method"] == method
                   and r["strike"] == strike], key=lambda r: r["n_paths"])


def make_figures(metrics, estimates, kernels, batches, spec, summary):
    """Return open figures; caller saves and closes each one."""
    figures = {}
    style = {"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
             "axes.spines.right": False, "axes.titleweight": "bold", "axes.labelcolor": "#334155",
             "figure.facecolor": "#f8fafc", "axes.facecolor": "#ffffff", "grid.alpha": .2}
    with plt.rc_context(style):
        fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.5), layout="constrained")
        for column, kind in enumerate(("call", "put")):
            histogram_errors = [r["price"] - r["reference"] for r in estimates if r["kind"] == kind
                                and r["strike"] == spec.strike and r["n_paths"] == summary["largest_n_paths"]]
            shared_bins = np.histogram_bin_edges(histogram_errors, bins=16)
            for method in METHODS:
                rows = _subset(metrics, kind, method, spec.strike)
                n = np.array([r["n_paths"] for r in rows])
                rmse = np.array([r["rmse"] for r in rows])
                valid = rmse > 0
                axes[0, column].loglog(n[valid], rmse[valid], "o-", color=COLORS[method], label=LABELS[method])
                low = np.array([r["rmse_ci_low"] for r in rows])
                high = np.array([r["rmse_ci_high"] for r in rows])
                band = valid & (low > 0)
                axes[0, column].fill_between(n[band], low[band], high[band], color=COLORS[method], alpha=.12)
                last = rows[-1]
                errors = [r["price"] - r["reference"] for r in estimates if r["kind"] == kind
                          and r["strike"] == spec.strike and r["method"] == method
                          and r["n_paths"] == last["n_paths"]]
                axes[1, column].hist(errors, bins=shared_bins, histtype="step", linewidth=1.8,
                                     color=COLORS[method], label=LABELS[method])
            plain = _subset(metrics, kind, "plain", spec.strike)
            if plain[0]["rmse"] > 0:
                n = np.array([r["n_paths"] for r in plain])
                axes[0, column].loglog(n, plain[0]["rmse"] * np.sqrt(n[0] / n),
                                       "--", color="#94a3b8", label="N^-1/2 reference")
            axes[0, column].set(title=f"{kind.title()}: error across independent runs",
                                xlabel="Production terminal evaluations (N)", ylabel="Empirical RMSE (premium units)")
            axes[1, column].axvline(0, color="#334155", ls="--", lw=1)
            axes[1, column].set(title=f"{kind.title()}: signed errors at N={summary['largest_n_paths']:,}",
                                xlabel="Estimated premium minus Black-Scholes", ylabel="Number of independent runs")
            axes[0, column].legend(fontsize=8)
            axes[1, column].legend(fontsize=8)
        fig.suptitle("MONTE CARLO  |  Accuracy comes from algorithms and sample size\n"
                     "Baseline strike; shaded regions: 95% bootstrap intervals for RMSE", fontsize=14, fontweight="bold")
        figures["accuracy.png"] = fig

        fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.5), layout="constrained")
        for column, kind in enumerate(("call", "put")):
            for method in METHODS:
                rows = _subset(metrics, kind, method, spec.strike)
                n = np.array([r["n_paths"] for r in rows])
                cov = np.array([r["coverage"] for r in rows])
                axes[0, column].semilogx(n, cov, "o-", color=COLORS[method], label=LABELS[method])
                axes[0, column].fill_between(n, [r["coverage_ci_low"] for r in rows],
                                             [r["coverage_ci_high"] for r in rows], color=COLORS[method], alpha=.1)
                denominator = np.array([r["rms_standard_error"] for r in rows])
                valid = denominator > 0
                axes[1, column].semilogx(n[valid], np.array([r["empirical_sd"] for r in rows])[valid]
                                        / denominator[valid], "o-", color=COLORS[method], label=LABELS[method])
            axes[0, column].axhline(.95, color="#334155", ls="--", lw=1)
            axes[0, column].set(title=f"{kind.title()}: do the 95% intervals cover truth?",
                                xlabel="Production terminal evaluations (N)", ylabel="Observed CI coverage", ylim=(0, 1.03))
            axes[1, column].axhline(1, color="#334155", ls="--", lw=1)
            axes[1, column].set(title=f"{kind.title()}: uncertainty calibration",
                                xlabel="Production terminal evaluations (N)", ylabel="Empirical SD / RMS reported SE")
            axes[0, column].legend(fontsize=8)
            axes[1, column].legend(fontsize=8)
        fig.suptitle("UNCERTAINTY  |  A precise-looking estimate still needs calibration\n"
                     "Baseline strike; coverage shading: 95% Wilson intervals across independent runs", fontsize=14, fontweight="bold")
        figures["calibration.png"] = fig

        fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.5), layout="constrained")
        times = [[r["elapsed_seconds"] * 1000 for r in kernels if r["implementation"] == name]
                 for name in ("scalar", "vectorized")]
        axes[0, 0].boxplot(times, widths=.5)
        axes[0, 0].set_xticks([1, 2], ["Python scalar loop", "NumPy vectorized"])
        axes[0, 0].set(yscale="log", ylabel="Kernel milliseconds (log scale)",
                       title=f"Same normals, same payoff: {summary['kernel_speedup']:.1f}x median speedup")
        axes[0, 0].text(.02, .06, "RNG and standard error excluded from both", transform=axes[0, 0].transAxes,
                        va="bottom", fontsize=8, color="#475569",
                        bbox={"facecolor": "white", "edgecolor": "none", "alpha": .9})
        batch_summary = summary["batch_benchmark"]
        x = [r["batch_size"] for r in batch_summary]
        for batch in x:
            ys = [r["elapsed_seconds"] * 1000 for r in batches if r["batch_size"] == batch]
            axes[0, 1].scatter([batch] * len(ys), ys, color="#008b8b", alpha=.35, s=18)
        axes[0, 1].plot(x, [r["median_seconds"] * 1000 for r in batch_summary], "o-", color="#008b8b", label="Median")
        axes[0, 1].set(xscale="log", yscale="log", xlabel="Maximum batch size", ylabel="Complete pricing milliseconds",
                       title="Batch overhead versus vectorized throughput")
        axes[0, 1].legend()
        axes[1, 0].loglog(x, [r["traced_peak_bytes"] / 2 ** 20 for r in batch_summary], "o-", color="#5967a9")
        axes[1, 0].set(xlabel="Maximum batch size", ylabel="Peak traced allocations (MiB)",
                       title="Bounded workspace: O(batch size)")
        axes[1, 0].text(.02, .96, "Separate allocation pass; not process RSS", transform=axes[1, 0].transAxes,
                        va="top", fontsize=8, color="#475569")
        for method in METHODS:
            rows = [r for r in _subset(metrics, "call", method, spec.strike) if r["rmse"] > 0]
            axes[1, 1].loglog([r["median_seconds"] * 1000 for r in rows], [r["rmse"] for r in rows],
                              "o-", color=COLORS[method], label=LABELS[method])
        axes[1, 1].set(xlabel="Median complete estimator time (ms)", ylabel="Empirical RMSE",
                       title="Accuracy / time: lower and left is better")
        axes[1, 1].legend(fontsize=8)
        fig.suptitle("COMPUTER ENGINEERING  |  Measure speed, memory and useful accuracy\n"
                     "CPU measurements on the recorded machine; pilot work included in complete estimators", fontsize=14, fontweight="bold")
        figures["engineering.png"] = fig

        fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.5), layout="constrained")
        for column, kind in enumerate(("call", "put")):
            for method in METHODS:
                rows = sorted([r for r in metrics if r["kind"] == kind and r["method"] == method
                               and r["n_paths"] == summary["largest_n_paths"]], key=lambda r: r["strike"])
                valid = [r for r in rows if r["rmse"] > 0]
                axes[0, column].plot([r["strike"] for r in valid], [r["rmse"] for r in valid],
                                     "o-", color=COLORS[method], label=LABELS[method])
                valid = [r for r in rows if r["work_normalized_gain"] is not None]
                axes[1, column].plot([r["strike"] for r in valid], [r["work_normalized_gain"] for r in valid],
                                     "o-", color=COLORS[method], label=LABELS[method])
            axes[0, column].set(title=f"{kind.title()}: accuracy across strike prices", xlabel="Strike K", ylabel="RMSE")
            axes[1, column].axhline(1, color="#334155", ls="--", lw=1)
            axes[1, column].set(title=f"{kind.title()}: account for extra pilot work", xlabel="Strike K",
                                ylabel="Work-normalized MSE gain vs plain (>1 better)")
            axes[0, column].legend(fontsize=8)
            axes[1, column].legend(fontsize=8)
        fig.suptitle(f"ROBUSTNESS  |  A method's benefit depends on the payoff\n"
                     f"N={summary['largest_n_paths']:,} production evaluations; gains are finite-repeat estimates", fontsize=14, fontweight="bold")
        figures["robustness.png"] = fig
        for fig in figures.values():
            for ax in fig.axes:
                ax.grid(True, alpha=.18)
    return figures
