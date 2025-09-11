#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

import numpy as np
import copy
from pathlib import Path

from utils.config import DEFAULT_CONFIG, Config, hash_sim_dir
from utils.runner import set_signal_handler, build_bin, RunOptions
from utils.manager import SimJob, execute_sim_jobs
from utils.results import compute_growth_rate_result
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

    config = copy.deepcopy(DEFAULT_CONFIG)
    sim_job: SimJob = {
        "sim_dir": hash_sim_dir(sim_base_dir, config),
        "run_options": common_run_options,
    }

    sim_jobs = [sim_job]

    prob_phe_0_list = list(map(float, np.linspace(9 / 16, 15 / 16, 7)))
    for sim_idx, prob_phe_0 in enumerate(prob_phe_0_list):
        config: Config = copy.deepcopy(DEFAULT_CONFIG)
        config["model"]["prob_mut"] = 0.0
        config["init"]["prob_phe"] = [prob_phe_0, 1 - prob_phe_0]
        sim_jobs.append(
            {
                "sim_dir": hash_sim_dir(sim_base_dir, config),
                "run_options": common_run_options,
            }
        )

    execute_sim_jobs(sim_jobs)

    growth_rate_results = [
        compute_growth_rate_result(sim_job["sim_dir"], 0) for sim_job in sim_jobs
    ]

    make_growth_rate_plot(
        growth_rate_results[0],
        growth_rate_results[1:],
        sim_base_dir / "growth_rate.pdf",
    )
