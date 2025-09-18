from pathlib import Path
import pandas as pd
import matplotlib as mpl
from matplotlib import pyplot as plt
from typing import Optional, Tuple

from .config import load_config
from .results import NormResults, read_results

mpl.use("pdf")

mpl.rcParams["text.usetex"] = True
mpl.rcParams["text.latex.preamble"] = "\\usepackage{lmodern}"
mpl.rcParams["font.family"] = "lmodern"
mpl.rcParams["font.size"] = 11

cm = 1 / 2.54

mpl.rcParams["figure.constrained_layout.use"] = True


def collect_all_scalar_results(base_dir: Path, time_step: float) -> pd.DataFrame:
    all_scalar_results = []

    for sim_dir in [entry for entry in base_dir.iterdir() if entry.is_dir()]:
        norm_results = NormResults.from_results(read_results(sim_dir, 0), time_step)

        scalar_results = pd.concat(
            [
                df.rename(columns=lambda col: (name, col))
                for name, df in {
                    "norm_growth_rate": norm_results.norm_growth_rate,
                    "rate_extinct": norm_results.rate_extinct,
                }.items()
            ],
            axis=1,
        )

        scalar_results["with_mut"] = load_config(sim_dir)["model"]["prob_mut"] > 0.0

        all_scalar_results.append(scalar_results)

    return pd.concat(all_scalar_results)


def plot_scalar_results(
    base_dir: Path,
    time_step: float,
    xlabel: str,
    ylabel: str,
    yscale: Optional[str],
    x_col: Tuple[str, str],
    y_col: Tuple[str, str],
    xerr_col: Optional[Tuple[str, str]],
    yerr_col: Optional[Tuple[str, str]],
    filename: str,
) -> None:
    fig, ax = plt.subplots(figsize=(16.0 * cm, 10.0 * cm))

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    if yscale:
        ax.set_yscale(yscale)

    all_scalar_results = collect_all_scalar_results(base_dir, time_step)
    with_mut = all_scalar_results["with_mut"]

    for scalar_results, color, label in [
        (all_scalar_results[~with_mut], "b", "fixed"),
        (all_scalar_results[with_mut], "r", "with mutations"),
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
    fig.savefig(base_dir / filename)
    plt.close(fig)


def make_std_dev_plot(base_dir: Path, time_step: float) -> None:
    plot_scalar_results(
        base_dir,
        time_step,
        xlabel="$\\langle\\mu\\rangle$",
        ylabel="$\\sigma_{\\mu}$",
        yscale=None,
        x_col=("norm_growth_rate", "mean"),
        y_col=("norm_growth_rate", "std_dev"),
        xerr_col=("norm_growth_rate", "sem"),
        yerr_col=None,
        filename="std_dev.pdf",
    )


def make_rate_extinct_plot(base_dir: Path, time_step: float) -> None:
    plot_scalar_results(
        base_dir,
        time_step,
        xlabel="$\\langle\\mu\\rangle$",
        ylabel="$r_e$",
        x_col=("norm_growth_rate", "mean"),
        y_col=("rate_extinct", "mean"),
        xerr_col=("norm_growth_rate", "sem"),
        yerr_col=("rate_extinct", "sem"),
        yscale="log",
        filename="rate_extinct.pdf",
    )
