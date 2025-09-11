#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

import numpy as np
from pathlib import Path

from utils.runner import set_signal_handler, build_bin, RunOptions
from utils.config import Config, hash_sim_dir
from utils.manager import SimJob, execute_sim_jobs
from utils.results import compute_growth_rate
from utils.plotting import make_growth_rate_plot


if __name__ == "__main__":
    set_signal_handler()

    build_bin()

    sim_base_dir = Path("simulations/")

    common_run_options: RunOptions = {
        "clean": False,
        "n_runs": 1,
        "n_files": 64,
        "analyze": True,
    }

    config: Config = {
        "model": {
            "n_env": 2,
            "n_phe": 2,
            "prob_trans_env": [[0.99, 0.01], [0.01, 0.99]],
            "prob_rep": [[0.016, 0.0], [0.0, 0.012]],
            "prob_dec": [[0.0, 0.024], [0.016, 0.0]],
            "prob_mut": 0.001,
            "std_dev_mut": 0.1,
        },
        "init": {
            "n_agt": 1024,
            "prob_phe": [0.5, 0.5],
        },
        "output": {
            "steps_per_save": 1024,
            "saves_per_file": 1024,
        },
    }

    sim_job: SimJob = {
        "sim_dir": hash_sim_dir(sim_base_dir, config),
        "run_options": common_run_options,
    }

    sim_jobs = [sim_job]

    config["model"]["prob_mut"] = 0.0
    prob_phe_0_list = list(map(float, np.linspace(9 / 16, 15 / 16, 7)))
    for sim_idx, prob_phe_0 in enumerate(prob_phe_0_list):
        config["init"]["prob_phe"] = [prob_phe_0, 1 - prob_phe_0]
        sim_jobs.append(
            {
                "sim_dir": hash_sim_dir(sim_base_dir, config),
                "run_options": common_run_options,
            }
        )

    execute_sim_jobs(sim_jobs)

    growth_rates = [compute_growth_rate(sim_job["sim_dir"], 0) for sim_job in sim_jobs]

    make_growth_rate_plot(
        growth_rates[0], growth_rates[1:], sim_base_dir / "growth_rate.pdf"
    )
