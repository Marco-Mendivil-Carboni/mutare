#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

import numpy as np
import copy
from pathlib import Path
import matplotlib as mpl
from matplotlib import pyplot as plt
from typing import TypedDict

from utils.config import DEFAULT_CONFIG, Config
from utils.runner import set_signal_handler, build_bin, RunOptions
from utils.manager import SimJob, execute_sim_jobs
from utils.results import read_results

mpl.use("pdf")
mpl.rcParams["text.usetex"] = True
mpl.rcParams["font.family"] = "serif"
cm = 1 / 2.54
mpl.rcParams["figure.figsize"] = [16.0 * cm, 10.0 * cm]
mpl.rcParams["figure.constrained_layout.use"] = True


class GrowthRateResult(TypedDict):
    avg_W: float
    avg_W_err: float
    sig_W: float
    sig_W_err: float


def compute_growth_rate_result(sim_dir: Path, run_idx: int) -> GrowthRateResult:
    results = read_results(sim_dir, run_idx)
    mean = results["discrete_growth_rate"][0]["mean"]
    std_dev = results["discrete_growth_rate"][0]["std_dev"]
    sem = results["discrete_growth_rate"][0]["sem"]
    n_eff = (std_dev / sem) ** 2
    return {
        "avg_W": mean,
        "avg_W_err": sem,
        "sig_W": std_dev,
        "sig_W_err": std_dev / np.sqrt(2 * (n_eff - 1)),
    }


if __name__ == "__main__":
    set_signal_handler()

    build_bin()

    common_run_options: RunOptions = {
        "clean": True,
        "n_runs": 1,
        "n_files": 16,
        "analyze": True,
    }

    sim_dir = Path("simulations/with_mut/")
    config = copy.deepcopy(DEFAULT_CONFIG)
    sim_job: SimJob = {
        "sim_dir": sim_dir,
        "config": config,
        "run_options": common_run_options,
    }

    sim_jobs = [sim_job]

    prob_phe_0_list = list(map(float, np.linspace(1 / 8, 7 / 8, 7)))
    for sim_idx, prob_phe_0 in enumerate(prob_phe_0_list):
        sim_dir = Path(f"simulations/fixed-{sim_idx:02d}/")
        config: Config = copy.deepcopy(DEFAULT_CONFIG)
        config["model"]["prob_mut"] = 0.0
        config["init"]["prob_phe"] = [prob_phe_0, 1 - prob_phe_0]
        sim_jobs.append(
            {
                "sim_dir": sim_dir,
                "config": config,
                "run_options": common_run_options,
            }
        )

    execute_sim_jobs(sim_jobs)

    growth_rate_results = [
        compute_growth_rate_result(sim_job["sim_dir"], 0) for sim_job in sim_jobs
    ]

    fig, ax = plt.subplots()
    ax.set_xlabel("$\\langle\\mu\\rangle$")
    ax.set_ylabel("$\\sigma_{\\mu}$")

    ax.errorbar(
        [r["avg_W"] for r in growth_rate_results[1:]],
        [r["sig_W"] for r in growth_rate_results[1:]],
        xerr=[r["avg_W_err"] for r in growth_rate_results[1:]],
        yerr=[r["sig_W_err"] for r in growth_rate_results[1:]],
        c="b",
        ls="",
        label="fixed",
    )
    ax.errorbar(
        growth_rate_results[0]["avg_W"],
        growth_rate_results[0]["sig_W"],
        xerr=growth_rate_results[0]["avg_W_err"],
        yerr=growth_rate_results[0]["sig_W_err"],
        c="r",
        ls="",
        label="with mutations",
    )
    ax.legend()

    fig.savefig("simulations/growth_rate.pdf")
    plt.close(fig)
