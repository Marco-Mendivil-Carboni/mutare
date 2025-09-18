#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

from pathlib import Path
import numpy as np

from utils.config import Config, NormModelParams
from utils.runner import RunOptions
from utils.manager import SimJob, execute_sim_jobs
from utils.plotting import make_std_dev_plot


if __name__ == "__main__":
    # base_dir = Path("simulations/explore_configs_2/")
    base_dir = Path("simulations/explore_configs/")

    time_step = 0.01

    config: Config = {
        # "model": NormModelParams(
        #     n_env=2,
        #     n_phe=2,
        #     rate_trans_env=[[-1.0, 1.0], [1.0, -1.0]],
        #     rate_rep=[[1.2, 0.0], [0.0, 0.8]],
        #     rate_dec=[[0.0, 1.6], [1.2, 0.0]],
        #     rate_mut=0.1,
        #     std_dev_mut=1 / 16,
        #     time_step=time_step,
        # ).to_model_params(),
        "model": {
            "n_env": 2,
            "n_phe": 2,
            "prob_trans_env": [[0.99, 0.01], [0.01, 0.99]],
            "prob_rep": [[0.012, 0.0], [0.0, 0.008]],
            "prob_dec": [[0.0, 0.016], [0.012, 0.0]],
            "prob_mut": 1 / 1024,
            "std_dev_mut": 1 / 16,
        },
        "init": {
            "n_agt": 16384,
            "prob_phe": [0.5, 0.5],
        },
        "output": {
            "steps_per_file": 262144,
            "steps_per_save": 4096,
            # "steps_per_save": int(16 / time_step),
        },
    }

    run_options = RunOptions(clean=False, n_runs=1, n_files=64, analyze=False)

    sim_jobs = [SimJob.from_config(base_dir, config, run_options)]

    config["model"]["prob_mut"] = 0.0
    config["output"].pop("steps_per_save")
    prob_phe_0_list = list(map(float, np.linspace(1 / 16, 15 / 16, 15)))
    for prob_phe_0 in prob_phe_0_list:
        config["init"]["prob_phe"] = [prob_phe_0, 1 - prob_phe_0]
        sim_jobs.append(SimJob.from_config(base_dir, config, run_options))

    execute_sim_jobs(sim_jobs)

    make_std_dev_plot(base_dir, time_step)
