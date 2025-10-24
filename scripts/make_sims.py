#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

from pathlib import Path
from typing import List

from utils.config import Config
from utils.exec import RunOptions, SimJob, execute_sim_jobs
from utils.plots import make_plots

if __name__ == "__main__":
    base_dir = Path("simulations/")

    sim_jobs: List[SimJob] = []

    strat_phe_0_list = [(i + 1) / 16 for i in range(16)]
    for strat_phe_0 in strat_phe_0_list:
        config: Config = {
            "model": {
                "n_env": 2,
                "n_phe": 2,
                "rates_trans": [[-1.0, 1.0], [1.0, -1.0]],
                "rates_birth": [[1.2, 0.0], [0.0, 0.9]],
                "rates_death": [[0.0, 1.6], [1.0, 0.0]],
                "prob_mut": 0.0018,
            },
            "init": {
                "n_agt": 240,
                "strat_phe": [strat_phe_0, 1 - strat_phe_0],
            },
            "output": {
                "steps_per_file": 1_048_576,
                "steps_per_save": 64,
            },
        }

        run_options = RunOptions(
            clean=False,
            n_runs=4,
            n_files=64,
            analyze=True,
        )

        sim_jobs.append(SimJob(base_dir, config, run_options))

        config["model"]["prob_mut"] = 0.0

        sim_jobs.append(SimJob(base_dir, config, run_options))

    execute_sim_jobs(sim_jobs)

    make_plots(sim_jobs, Path("plots/"))
