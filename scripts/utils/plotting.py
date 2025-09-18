from pathlib import Path
import pandas as pd
import matplotlib as mpl
from matplotlib import pyplot as plt

from .config import load_config
from .results import NormResults, read_results

mpl.use("pdf")

mpl.rcParams["text.usetex"] = True
mpl.rcParams["text.latex.preamble"] = "\\usepackage{lmodern}"
mpl.rcParams["font.family"] = "lmodern"
mpl.rcParams["font.size"] = 11

cm = 1 / 2.54

mpl.rcParams["figure.constrained_layout.use"] = True


def make_std_dev_plot(base_dir: Path, time_step: float) -> None:
    fig, ax = plt.subplots(figsize=(16.0 * cm, 10.0 * cm))

    ax.set_xlabel("$\\langle\\mu\\rangle$")
    ax.set_ylabel("$\\sigma_{\\mu}$")

    sim_dirs = [entry for entry in base_dir.iterdir() if entry.is_dir()]

    growth_rates = []
    for sim_dir in sim_dirs:
        norm_results = NormResults.from_results(read_results(sim_dir, 0), time_step)
        df = norm_results.norm_growth_rate.copy()
        df["fixed"] = load_config(sim_dir)["model"]["prob_mut"] == 0.0
        growth_rates.append(df)
    growth_rates = pd.concat(growth_rates, ignore_index=True)

    growth_rates_fixed = growth_rates[growth_rates["fixed"]]
    ax.errorbar(
        growth_rates_fixed["mean"],
        growth_rates_fixed["std_dev"],
        xerr=growth_rates_fixed["sem"],
        c="b",
        ls="",
        label="fixed",
    )

    growth_rates_with_mut = growth_rates[~growth_rates["fixed"]]

    ax.errorbar(
        growth_rates_with_mut["mean"],
        growth_rates_with_mut["std_dev"],
        xerr=growth_rates_with_mut["sem"],
        c="r",
        ls="",
        label="with mutations",
    )

    ax.legend()

    fig.savefig(base_dir / "std_dev.pdf")

    plt.close(fig)
