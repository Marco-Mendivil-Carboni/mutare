#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

from pathlib import Path
import numpy as np
from typing import List

from utils.config import Config, NormModelParams
from utils.runner import RunOptions, SimJob, execute_sim_jobs
from utils.plotting import make_plots

if __name__ == "__main__":
    base_dir = Path("simulations/std_sims/")

    time_step = 1 / 64

    config: Config = {
        "model": NormModelParams(
            n_env=2,
            n_phe=2,
            rate_trans_env=[[-1.0, 1.0], [1.0, -1.0]],
            rate_rep=[[1.2, 0.0], [0.0, 0.8]],
            rate_dec=[[0.0, 1.6], [1.2, 0.0]],
            rate_mut=1 / 16,
            std_dev_mut=1 / 16,
            time_step=time_step,
        ).to_model_params(),
        "init": {
            "n_agt": 16384,
            "prob_phe": [0.0, 0.0],
        },
        "output": {
            "steps_per_file": 262144,
            "steps_per_save": int(64 / time_step),
        },
    }

    run_options = RunOptions(clean=False, n_runs=1, n_files=64, analyze=True)

    sim_jobs: List[SimJob] = []

    prob_phe_0_list = list(map(float, np.linspace(1 / 4, 4 / 4, 4)))
    for prob_phe_0 in prob_phe_0_list:
        config["init"]["prob_phe"] = [prob_phe_0, 1 - prob_phe_0]
        sim_jobs.append(SimJob.from_config(base_dir, config, run_options))

    config["model"]["prob_mut"] = 0.0
    config["output"].pop("steps_per_save")
    prob_phe_0_list = list(map(float, np.linspace(4 / 16, 15 / 16, 12)))
    for prob_phe_0 in prob_phe_0_list:
        config["init"]["prob_phe"] = [prob_phe_0, 1 - prob_phe_0]
        sim_jobs.append(SimJob.from_config(base_dir, config, run_options))

    execute_sim_jobs(sim_jobs)

    make_plots(base_dir, time_step)
