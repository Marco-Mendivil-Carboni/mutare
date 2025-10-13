from pathlib import Path
import pandas as pd
import matplotlib as mpl
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from typing import List

from .exec import SimJob
from .results import collect_sim_jobs_results

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


def plot_scalar_results(
    sim_jobs_results: pd.DataFrame,
    ax: Axes,
    x_col: str,
    y_col: str,
) -> None:
    with_mut = sim_jobs_results["with_mut"]
    for scalar_results, color, label in [
        (sim_jobs_results[~with_mut], colors[7], "fixed"),
        (sim_jobs_results[with_mut], colors[1], "with mutations"),
    ]:
        ax.errorbar(
            scalar_results[x_col]["mean"],
            scalar_results[y_col]["mean"],
            xerr=scalar_results[x_col]["sem"],
            yerr=scalar_results[y_col]["sem"],
            c=color,
            ls="",
            marker="o",
            markersize=4,
            label=label,
        )

    ax.legend()


def make_plots(sim_jobs: List[SimJob], fig_dir: Path) -> None:
    sim_jobs_results = collect_sim_jobs_results(sim_jobs)
    print(sim_jobs_results.to_string())

    fig = Figure(figsize=(16.0 * cm, 10.0 * cm))
    ax = fig.add_subplot(1, 1, 1)
    ax.set_xlabel("$\\langle\\mu\\rangle$")
    ax.set_ylabel("$r_e$")
    ax.set_yscale("log")
    plot_scalar_results(
        sim_jobs_results,
        ax,
        x_col="growth_rate",
        y_col="extinct_rate",
    )
    fig.savefig(fig_dir / "extinct_rate.pdf")

    fig = Figure(figsize=(16.0 * cm, 10.0 * cm))
    ax = fig.add_subplot(1, 1, 1)
    ax.set_xlabel("$\\langle\\mu\\rangle$")
    ax.set_ylabel("$\\sigma_{p(\\phi)}$")
    plot_scalar_results(
        sim_jobs_results,
        ax,
        x_col="growth_rate",
        y_col="std_dev_strat_phe",
    )
    fig.savefig(fig_dir / "std_dev_strat_phe.pdf")
