from pathlib import Path
import pandas as pd
import matplotlib as mpl
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from typing import Tuple, Optional

from .config import load_config
from .results import NormResults, read_results

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


def collect_all_scalar_results(base_dir: Path, time_step: float) -> pd.DataFrame:
    all_scalar_results = []

    for sim_dir in [entry for entry in base_dir.iterdir() if entry.is_dir()]:
        norm_results = NormResults.from_results(read_results(sim_dir, 0), time_step)

        scalar_results = []
        for name, df in {
            "norm_growth_rate": norm_results.norm_growth_rate,
            "rate_extinct": norm_results.rate_extinct,
        }.items():
            df.columns = pd.MultiIndex.from_product([[name], df.columns])
            scalar_results.append(df)

        scalar_results = pd.concat(scalar_results, axis=1)

        scalar_results["with_mut"] = load_config(sim_dir)["model"]["prob_mut"] > 0.0

        all_scalar_results.append(scalar_results)

    return pd.concat(all_scalar_results)


def plot_scalar_results(
    all_scalar_results: pd.DataFrame,
    ax: Axes,
    x_col: Tuple[str, str],
    y_col: Tuple[str, str],
    xerr_col: Optional[Tuple[str, str]],
    yerr_col: Optional[Tuple[str, str]],
) -> None:
    with_mut = all_scalar_results["with_mut"]
    for scalar_results, color, label in [
        (all_scalar_results[~with_mut], colors[7], "fixed"),
        (all_scalar_results[with_mut], colors[1], "with mutations"),
    ]:
        ax.errorbar(
            scalar_results[x_col],
            scalar_results[y_col],
            xerr=scalar_results[xerr_col] if xerr_col else None,
            yerr=scalar_results[yerr_col] if yerr_col else None,
            c=color,
            ls="",
            label=label,
        )

    ax.legend()


def make_plots(base_dir: Path, time_step: float) -> None:
    all_scalar_results = collect_all_scalar_results(base_dir, time_step)
    print(all_scalar_results.to_string())

    fig = Figure(figsize=(16.0 * cm, 10.0 * cm))
    ax = fig.add_subplot(1, 1, 1)
    ax.set_xlabel("$\\langle\\mu\\rangle$")
    ax.set_ylabel("$\\sigma_{\\mu}$")
    plot_scalar_results(
        all_scalar_results,
        ax,
        x_col=("norm_growth_rate", "mean"),
        y_col=("norm_growth_rate", "std_dev"),
        xerr_col=("norm_growth_rate", "sem"),
        yerr_col=None,
    )
    fig.savefig(base_dir / "std_dev.pdf")

    fig = Figure(figsize=(16.0 * cm, 10.0 * cm))
    ax = fig.add_subplot(1, 1, 1)
    ax.set_xlabel("$\\langle\\mu\\rangle$")
    ax.set_ylabel("$r_e$")
    ax.set_yscale("log")
    plot_scalar_results(
        all_scalar_results,
        ax,
        x_col=("norm_growth_rate", "mean"),
        y_col=("rate_extinct", "mean"),
        xerr_col=("norm_growth_rate", "sem"),
        yerr_col=("rate_extinct", "sem"),
    )
    fig.savefig(base_dir / "rate_extinct.pdf")
