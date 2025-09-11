from pathlib import Path
import matplotlib as mpl
from matplotlib import pyplot as plt
from typing import List

from .results import GrowthRateResult

mpl.use("pdf")

mpl.rcParams["text.usetex"] = True

mpl.rcParams["font.family"] = "serif"

cm = 1 / 2.54
mpl.rcParams["figure.figsize"] = [16.0 * cm, 10.0 * cm]

mpl.rcParams["figure.constrained_layout.use"] = True


def make_growth_rate_plot(
    with_mut_result: GrowthRateResult,
    fixed_results: List[GrowthRateResult],
    output_file: Path,
) -> None:
    fig, ax = plt.subplots()
    ax.set_xlabel("$\\langle\\mu\\rangle$")
    ax.set_ylabel("$\\sigma_{\\mu}$")

    ax.errorbar(
        [res["avg_W"] for res in fixed_results],
        [res["sig_W"] for res in fixed_results],
        xerr=[res["avg_W_err"] for res in fixed_results],
        yerr=[res["sig_W_err"] for res in fixed_results],
        c="b",
        ls="",
        label="fixed",
    )

    ax.errorbar(
        with_mut_result["avg_W"],
        with_mut_result["sig_W"],
        xerr=with_mut_result["avg_W_err"],
        yerr=with_mut_result["sig_W_err"],
        c="r",
        ls="",
        label="with mutations",
    )

    ax.legend()

    fig.savefig(output_file)
    plt.close(fig)
