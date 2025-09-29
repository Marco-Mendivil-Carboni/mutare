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

    sim_jobs: List[SimJob] = []

    prob_phe_0_list = list(map(float, np.linspace(1 / 16, 1, 16)))
    for prob_phe_0 in prob_phe_0_list:
        config: Config = {
            "model": NormModelParams(
                n_env=2,
                n_phe=2,
                rate_trans_env=[[-1.0, 1.0], [1.0, -1.0]],
                rate_rep=[[1.2, 0.0], [0.0, 0.8]],
                rate_dec=[[0.0, 1.4], [1.0, 0.0]],
                prob_mut=1 / 256,
                std_dev_mut=1 / 4,
                time_step=time_step,
            ).to_model_params(),
            "init": {
                "n_agt": 256,
                "prob_phe": [prob_phe_0, 1 - prob_phe_0],
            },
            "output": {
                "steps_per_file": int(4096 / time_step),
                "steps_per_save": int(256 / time_step),
            },
        }

        run_options = RunOptions(n_files=256)

        sim_jobs.append(SimJob.from_config(base_dir, config, run_options))

        config["model"]["prob_mut"] = 0.0
        config["model"]["std_dev_mut"] = 0.0

        config["output"].pop("steps_per_save")

        sim_jobs.append(SimJob.from_config(base_dir, config, run_options))

    execute_sim_jobs(sim_jobs)

    make_plots(sim_jobs, time_step, Path("plots/"))
