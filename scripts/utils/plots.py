from pathlib import Path
import matplotlib as mpl
import numpy as np
from matplotlib.figure import Figure
from typing import Dict, List, Any

from .exec import SimJob
from .analysis import collect_avg_analyses

mpl.use("pdf")

mpl.rcParams["text.usetex"] = True
mpl.rcParams["text.latex.preamble"] = "\\usepackage{lmodern}"
mpl.rcParams["font.family"] = "lmodern"
mpl.rcParams["font.size"] = 11

cm = 1 / 2.54

mpl.rcParams["figure.constrained_layout.use"] = True

colors = [
    "#df591f",
    "#d81e2c",
    "#d21e6f",
    "#cc1dad",
    "#a31cc5",
    "#611bbf",
    "#221ab9",
    "#194bb2",
    "#1880ac",
    "#17a69b",
    "#169f62",
    "#15992c",
]

plot_style: Dict[str, Any] = dict(ls=":", marker="o", markersize=2)
fill_style: Dict[str, Any] = dict(lw=0.0, alpha=0.5)
line_style: Dict[str, Any] = dict(ls=":", lw=1.0, alpha=0.5)


def make_plots(sim_jobs: List[SimJob], fig_dir: Path) -> None:
    avg_analyses = collect_avg_analyses(sim_jobs)

    sim_type = avg_analyses["sim_type"]

    fig_1 = Figure(figsize=(16.0 * cm, 10.0 * cm))
    ax_1 = fig_1.add_subplot()
    ax_1.set_xlabel("$\\langle\\mu\\rangle$")
    ax_1.set_ylabel("$r_e$")
    ax_1.set_yscale("log")

    fig_2 = Figure(figsize=(16.0 * cm, 10.0 * cm))
    ax_2 = fig_2.add_subplot()
    ax_2.set_xlabel("$p_{\\phi}(0)_i$")
    ax_2.set_ylabel("$\\langle\\mu\\rangle$")

    fig_3 = Figure(figsize=(12.0 * cm, 10.0 * cm))
    ax_3 = fig_3.add_subplot()
    ax_3.set_xlabel("$p_{\\phi}(0)_i$")
    ax_3.set_ylabel("$\\langle p_{\\phi}(0)\\rangle$")

    fig_4 = Figure(figsize=(12.0 * cm, 10.0 * cm))
    ax_4 = fig_4.add_subplot()
    ax_4.set_xlabel("$p_{\\phi}(0)_i$")
    ax_4.set_ylabel("$p_{\\phi}(0)$")

    heatmap = list()
    max_mu_strat: Any = None

    for avg_analyses, color, label in [
        (avg_analyses[sim_type == "fixed"], colors[1], "fixed"),
        (avg_analyses[sim_type == "with mutations"], colors[7], "with mutations"),
        (avg_analyses[sim_type == "random init"], colors[11], "random init"),
    ]:
        ax_1.errorbar(
            avg_analyses[("growth_rate", "mean")],
            avg_analyses[("extinct_rate", "mean")],
            xerr=avg_analyses[("growth_rate", "sem")],
            yerr=avg_analyses[("extinct_rate", "sem")],
            c=color,
            label=label,
            **plot_style,
        )
        ax_1.axvline(
            avg_analyses[("growth_rate", "mean")].mean(), c=color, **line_style
        )
        ax_1.axhline(
            avg_analyses[("extinct_rate", "mean")].mean(), c=color, **line_style
        )

        if label == "fixed":
            max_mu_strat = avg_analyses["strat_phe_0"][
                avg_analyses[("growth_rate", "mean")].idxmax()
            ]

        if label != "random init":
            ax_2.errorbar(
                avg_analyses["strat_phe_0"],
                avg_analyses[("growth_rate", "mean")],
                yerr=avg_analyses[("growth_rate", "sem")],
                c=color,
                label=label,
                **plot_style,
            )
        else:
            for growth_rate_mean, growth_rate_sem in avg_analyses[
                [("growth_rate", "mean"), ("growth_rate", "sem")]
            ].itertuples(index=False):
                ax_2.axhline(growth_rate_mean, c=color, label=label, ls=":")
                ax_2.axhspan(
                    growth_rate_mean + growth_rate_sem,
                    growth_rate_mean - growth_rate_sem,
                    color=color,
                    **fill_style,
                )

        if label != "random init":
            ax_3.plot(
                avg_analyses["strat_phe_0"],
                avg_analyses[("avg_strat_phe_0", "mean")],
                c=color,
                label=label,
                **plot_style,
            )
            ax_3.fill_between(
                avg_analyses["strat_phe_0"],
                avg_analyses[("avg_strat_phe_0", "mean")]
                - avg_analyses[("std_dev_strat_phe", "mean")],
                avg_analyses[("avg_strat_phe_0", "mean")]
                + avg_analyses[("std_dev_strat_phe", "mean")],
                color=color,
                **fill_style,
            )
        else:
            for avg_strat_phe_0, std_dev_strat_phe in avg_analyses[
                [("avg_strat_phe_0", "mean"), ("std_dev_strat_phe", "mean")]
            ].itertuples(index=False):
                ax_3.axhline(avg_strat_phe_0, c=color, label=label, ls=":")
                ax_3.axhspan(
                    avg_strat_phe_0 + std_dev_strat_phe,
                    avg_strat_phe_0 - std_dev_strat_phe,
                    color=color,
                    **fill_style,
                )
        if label == "with mutations":
            # fix the following line
            for bin in reversed(range(24)):
                heatmap.append(avg_analyses[(f"dist_strat_phe_0_{bin}", "mean")])

    heatmap = np.array([heatmap])
    # fix the following line, remove [0] and addhoc extent.
    im = ax_4.imshow(heatmap[0], cmap="coolwarm", extent=(1 / 24, 1, 0.0, 1.0))

    cbar = fig_4.colorbar(im, ax=ax_4, aspect=64, pad=1 / 64)
    cbar.ax.set_ylabel("$p(p_{\\phi}(0))$")

    ax_1.legend()
    fig_1.savefig(fig_dir / "extinct_rate.pdf")

    ax_2.axvline(max_mu_strat, color="gray", ls="-.")
    ax_2.legend()
    fig_2.savefig(fig_dir / "growth_rate.pdf")

    ax_3.axhline(max_mu_strat, color="gray", ls="-.")
    ax_3.legend()
    fig_3.savefig(fig_dir / "avg_strat_phe.pdf")

    ax_4.axhline(max_mu_strat, color="gray", ls="-.")
    fig_4.savefig(fig_dir / "dist_strat_phe.pdf")

    print("plots made")
