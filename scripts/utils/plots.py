from pathlib import Path
import matplotlib as mpl
from matplotlib.figure import Figure
from typing import List

from .exec import SimJob
from .results import collect_sim_jobs_avg_results

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


def make_plots(sim_jobs: List[SimJob], fig_dir: Path) -> None:
    sim_jobs_avg_results = collect_sim_jobs_avg_results(sim_jobs)
    print(sim_jobs_avg_results.to_string())

    with_mut = sim_jobs_avg_results["with_mut"]

    fig_1 = Figure(figsize=(16.0 * cm, 10.0 * cm))
    ax_1 = fig_1.add_subplot(1, 1, 1)
    ax_1.set_xlabel("$\\langle\\mu\\rangle$")
    ax_1.set_ylabel("$r_e$")
    ax_1.set_yscale("log")

    fig_2 = Figure(figsize=(16.0 * cm, 10.0 * cm))
    ax_2 = fig_2.add_subplot(1, 1, 1)
    ax_2.set_xlabel("$p_{\\phi}(0)_i$")
    ax_2.set_ylabel("$\\langle\\mu\\rangle$")

    fig_3 = Figure(figsize=(16.0 * cm, 10.0 * cm))
    ax_3 = fig_3.add_subplot(1, 1, 1)
    ax_3.set_xlabel("$p_{\\phi}(0)_i$")
    ax_3.set_ylabel("$\\langle p_{\\phi}(0)\\rangle$")

    for avg_results, color, label in [
        (sim_jobs_avg_results[~with_mut], colors[7], "fixed"),
        (sim_jobs_avg_results[with_mut], colors[1], "with mutations"),
    ]:
        ax_1.errorbar(
            avg_results[("growth_rate", "mean")],
            avg_results[("extinct_rate", "mean")],
            xerr=avg_results[("growth_rate", "sem")],
            yerr=avg_results[("extinct_rate", "sem")],
            c=color,
            ls=":",
            marker="o",
            markersize=2,
            label=label,
        )
        ax_1.axvline(
            avg_results[("growth_rate", "mean")].mean(),
            c=color,
            ls=":",
            lw=1,
            alpha=0.5,
        )
        ax_1.axhline(
            avg_results[("extinct_rate", "mean")].mean(),
            c=color,
            ls=":",
            lw=1,
            alpha=0.5,
        )

        ax_2.errorbar(
            avg_results["strat_phe_0"],
            avg_results[("growth_rate", "mean")],
            yerr=avg_results[("growth_rate", "sem")],
            c=color,
            ls=":",
            marker="o",
            markersize=2,
            label=label,
        )

        ax_3.errorbar(
            avg_results["strat_phe_0"],
            avg_results[("avg_strat_phe_0", "mean")],
            yerr=avg_results[("std_dev_strat_phe", "mean")],
            c=color,
            ls=":",
            marker="o",
            markersize=2,
            label=label,
        )

    ax_1.legend()
    fig_1.savefig(fig_dir / "extinct_rate.pdf")

    ax_2.legend()
    fig_2.savefig(fig_dir / "growth_rate.pdf")

    ax_3.legend()
    fig_3.savefig(fig_dir / "avg_strat_phe.pdf")
