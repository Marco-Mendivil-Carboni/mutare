#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

import numpy as np
import copy
from pathlib import Path
import matplotlib as mpl
from matplotlib import pyplot as plt

from utils.config import DEFAULT_CONFIG, Config
from utils.manager import SimJob, execute_sim_jobs
from utils.results import read_results

# ------------------ Matplotlib setup ------------------ #
mpl.use("pdf")
mpl.rcParams["text.usetex"] = True
mpl.rcParams["font.family"] = "serif"
cm = 1 / 2.54
mpl.rcParams["figure.figsize"] = [16.0 * cm, 10.0 * cm]
mpl.rcParams["figure.constrained_layout.use"] = True

if __name__ == "__main__":
    # # ------------------ Base simulation ------------------ #
    # base_sim_dir = Path("simulations/with_mut/")
    # base_sim_dir.mkdir(parents=True, exist_ok=True)

    # base_config: Config = copy.deepcopy(DEFAULT_CONFIG)
    # base_config["model"]["prob_mut"] = 0.0001  # Base run uses mutations

    # base_job: SimJob = {
    #     "sim_dir": base_sim_dir,
    #     "config": base_config,
    #     "run_options": {"clean": True, "n_runs": 1, "n_files": 16, "analyze": True},
    # }

    # execute_sim_jobs([base_job])

    # results = read_results(base_sim_dir, 0)
    # mean = results["n_agt_diff"][0]["mean"]
    # std_dev = results["n_agt_diff"][0]["std_dev"]
    # sem = results["n_agt_diff"][0]["sem"]
    # n_eff = (std_dev / sem) ** 2

    # avg_W = mean
    # sig_W = std_dev
    # avg_W_err = sem
    # sig_W_err = std_dev / np.sqrt(2 * (n_eff - 1))

    # ------------------ Sweep over fixed probabilities ------------------ #
    n_sims = 24
    prob_phe_list = np.linspace(0, 1, n_sims)

    sim_jobs: list[SimJob] = []
    for sim_idx, prob_phe in enumerate(prob_phe_list):
        sim_dir = Path(f"simulations/fixed-{sim_idx:02d}/")
        job_config: Config = copy.deepcopy(DEFAULT_CONFIG)
        job_config["model"]["prob_mut"] = 0.0
        job_config["init"]["prob_phe"] = [float(prob_phe), float(1 - prob_phe)]

        sim_jobs.append(
            {
                "sim_dir": sim_dir,
                "config": job_config,
                "run_options": {
                    "clean": True,
                    "n_runs": 1,
                    "n_files": 1,
                    "analyze": True,
                },
            }
        )

    # Execute jobs in parallel
    execute_sim_jobs(sim_jobs)

    # ------------------ Collect results ------------------ #
    avg_W_list, sig_W_list = [], []
    avg_W_err_list, sig_W_err_list = [], []

    for sim_idx in range(n_sims):
        sim_dir = Path(f"simulations/fixed-{sim_idx:02d}/")
        results = read_results(sim_dir, 0)

        mean = results["n_agt_diff"][0]["mean"]
        std_dev = results["n_agt_diff"][0]["std_dev"]
        sem = results["n_agt_diff"][0]["sem"]
        n_eff = (std_dev / sem) ** 2

        avg_W_list.append(mean)
        sig_W_list.append(std_dev)
        avg_W_err_list.append(sem)
        sig_W_err_list.append(std_dev / np.sqrt(2 * (n_eff - 1)))

    # ------------------ Plotting ------------------ #
    fig, ax = plt.subplots()
    ax.set_xlabel("$\\langle\\Delta N\\rangle$")
    ax.set_ylabel("$\\sigma_{\\Delta N}$")

    ax.errorbar(
        avg_W_list,
        sig_W_list,
        xerr=avg_W_err_list,
        yerr=sig_W_err_list,
        c="b",
        ls="",
        label="fixed",
    )
    # ax.errorbar(
    #     avg_W,
    #     sig_W,
    #     xerr=avg_W_err,
    #     yerr=sig_W_err,
    #     c="r",
    #     label="with mutations",
    # )
    ax.legend()

    fig.savefig("simulations/Delta-N-plot.pdf")
    plt.close(fig)
