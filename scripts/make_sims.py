#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

from pathlib import Path
import numpy as np
from typing import List

from utils.config import Config
from utils.exec import RunOptions, SimJob, execute_sim_jobs
from utils.plots import make_plots

if __name__ == "__main__":
    base_dir = Path("simulations/")

    sim_jobs: List[SimJob] = []

    prob_phe_0_list = list(map(float, np.linspace(1 / 16, 1, 16)))
    for prob_phe_0 in prob_phe_0_list:
        config: Config = {
            "model": {
                "n_env": 2,
                "n_phe": 2,
                "rates_trans_env": [[-1.0, 1.0], [1.0, -1.0]],
                "rates_rep": [[1.2, 0.0], [0.0, 0.8]],
                "rates_dec": [[0.0, 1.4], [1.0, 0.0]],
                "prob_mut": 1 / 256,
                "std_dev_mut": 1 / 4,
            },
            "init": {
                "n_agt": 256,
                "strat_phe": [prob_phe_0, 1 - prob_phe_0],
            },
            "output": {
                "steps_per_file": 1_048_576,
                "steps_per_save": 1_024,
            },
        }

        run_options = RunOptions()

        sim_jobs.append(SimJob(base_dir, config, run_options))

        config["model"]["prob_mut"] = 0.0
        config["model"]["std_dev_mut"] = 0.0

        sim_jobs.append(SimJob(base_dir, config, run_options))

    execute_sim_jobs(sim_jobs)

    make_plots(sim_jobs, Path("plots/"))
