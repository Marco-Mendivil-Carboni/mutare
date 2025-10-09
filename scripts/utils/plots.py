from pathlib import Path
import pandas as pd
import matplotlib as mpl
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from typing import List, Tuple, Optional

from .exec import SimJob
from .results import collect_all_scalar_results

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
    all_scalar_results: pd.DataFrame,
    ax: Axes,
    x_col: str,
    y_col: str,
    xerr_col: Optional[Tuple[str, str]] = None,
    yerr_col: Optional[Tuple[str, str]] = None,
) -> None:
    ax.errorbar(
        [
            -0.09508156056432987,
            -0.03774792891502479,
            0.0013609663988248652,
            0.03200975895020236,
            0.056389884387800945,
            0.0786173901945924,
            0.09346665751850095,
            0.11285324736168942,
            0.12328334805233479,
            0.13593906247885082,
            0.14957781731616562,
            0.15360716160211996,
            0.15970682502384057,
            0.15890150297149205,
            0.15017192855892708,
            0.10595251617378937,
        ],
        [
            0.0300140380859375,
            0.0182342529296875,
            0.0093994140625,
            0.0034637451171875,
            0.000732421875,
            0.0001068115234375,
            0.0,
            3.0517578125e-05,
            0.0,
            3.0517578125e-05,
            0.000152587890625,
            0.0003814697265625,
            0.001251220703125,
            0.003204345703125,
            0.0078582763671875,
            0.0202484130859375,
        ],
        yerr=2 / 65536,
        c=colors[11],
        marker="o",
        markersize=1,
        ls="",
        label="Gillespie",
    )

    with_mut = all_scalar_results["with_mut"]
    for scalar_results, color, label in [
        (all_scalar_results[~with_mut], colors[7], "fixed"),
        (all_scalar_results[with_mut], colors[1], "with mutations"),
    ]:
        ax.scatter(
            scalar_results[x_col] / scalar_results["time_step"],
            scalar_results[y_col] / scalar_results["time_step"],
            # xerr=scalar_results[xerr_col] if xerr_col else None,
            # yerr=scalar_results[yerr_col] if yerr_col else None,
            c=color,
            # ls="",
            label=label,
        )
        ax.axvline(
            (scalar_results[x_col] / scalar_results["time_step"]).mean(),
            c=color,
            ls="--",
            alpha=0.5,
        )
        ax.axhline(
            (scalar_results[y_col] / scalar_results["time_step"]).mean(),
            c=color,
            ls="--",
            alpha=0.5,
        )

    ax.legend()


def make_plots(sim_jobs: List[SimJob], fig_dir: Path) -> None:
    all_scalar_results = collect_all_scalar_results(sim_jobs)
    print(all_scalar_results.to_string())

    fig = Figure(figsize=(16.0 * cm, 10.0 * cm))
    ax = fig.add_subplot(1, 1, 1)
    ax.set_xlabel("$\\langle\\mu\\rangle$")
    ax.set_ylabel("$r_e$")
    ax.set_yscale("log")
    plot_scalar_results(
        all_scalar_results,
        ax,
        x_col="growth_rate",
        y_col="extinction_rate",
    )
    fig.savefig(fig_dir / "plot.pdf")
