from pathlib import Path
import matplotlib as mpl
from matplotlib import pyplot as plt
from typing import List

from .results import GrowthRate

mpl.use("pdf")

mpl.rcParams["text.usetex"] = True
mpl.rcParams["text.latex.preamble"] = "\\usepackage{lmodern}"
mpl.rcParams["font.family"] = "lmodern"
mpl.rcParams["font.size"] = 11

cm = 1 / 2.54

mpl.rcParams["figure.constrained_layout.use"] = True


def make_growth_rate_plot(
    rate_with_mut: GrowthRate,
    rates_fixed: List[GrowthRate],
    output_file: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(16.0 * cm, 10.0 * cm))

    ax.set_xlabel("$\\langle\\mu\\rangle$")
    ax.set_ylabel("$\\sigma_{\\mu}$")

    ax.errorbar(
        [rate["avg"] for rate in rates_fixed],
        [rate["sig"] for rate in rates_fixed],
        xerr=[rate["avg_err"] for rate in rates_fixed],
        yerr=[rate["sig_err"] for rate in rates_fixed],
        c="b",
        ls="",
        label="fixed",
    )

    ax.errorbar(
        rate_with_mut["avg"],
        rate_with_mut["sig"],
        xerr=rate_with_mut["avg_err"],
        yerr=rate_with_mut["sig_err"],
        c="r",
        ls="",
        label="with mutations",
    )

    ax.legend()

    fig.savefig(output_file)

    plt.close(fig)
