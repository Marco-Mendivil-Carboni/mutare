#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

from pathlib import Path
from copy import deepcopy
from typing import List

from utils.config import Config
from utils.exec import RunOptions, SimJob, execute_sim_jobs
from utils.plots import make_plots


def make_sims(base_dir: Path, base_config: Config, run_options: RunOptions):
    sim_jobs: List[SimJob] = []

    sim_jobs.append(SimJob(base_dir, base_config, run_options))

    config = deepcopy(base_config)
    strat_phe_0_values = [(i + 1) / 16 for i in range(15)]

    for strat_phe_0 in strat_phe_0_values:
        config["init"]["strat_phe"] = [strat_phe_0, 1 - strat_phe_0]

        config["model"]["prob_mut"] = 0.0
        sim_jobs.append(SimJob(base_dir, config, run_options))

        config["model"]["prob_mut"] = base_config["model"]["prob_mut"]
        sim_jobs.append(SimJob(base_dir, config, run_options))

    execute_sim_jobs(sim_jobs)

    fig_dir = Path("plots") / base_dir
    fig_dir.mkdir(parents=True, exist_ok=True)

    make_plots(sim_jobs, fig_dir)


if __name__ == "__main__":
    base_dir = Path("simulations/default/")

    base_config: Config = {
        "model": {
            "n_env": 2,
            "n_phe": 2,
            "rates_trans": [[-1.0, 1.0], [1.0, -1.0]],
            "rates_birth": [[1.2, 0.0], [0.0, 0.9]],
            "rates_death": [[0.0, 1.6], [1.0, 0.0]],
            "prob_mut": 0.002,
        },
        "init": {"n_agents": 240},
        "output": {
            "steps_per_file": 1_048_576,
            "steps_per_save": 256,
            "hist_bins": 16,
        },
    }

    run_options = RunOptions(
        clean=False,
        n_runs=4,
        n_files=64,
        analyze=True,
    )

    make_sims(base_dir, base_config, run_options)

    # base_dir = Path("simulations/more_noise/")

    # base_config: Config = {
    #     "model": {
    #         "n_env": 2,
    #         "n_phe": 2,
    #         "rates_trans": [[-1.0, 1.0], [1.0, -1.0]],
    #         "rates_birth": [[1.4, 0.2], [0.2, 1.0]],
    #         "rates_death": [[0.2, 1.6], [1.2, 0.2]],
    #         "prob_mut": 0.002,
    #     },
    #     "init": {"n_agents": 240},
    #     "output": {
    #         "steps_per_file": 1_048_576,
    #         "steps_per_save": 256,
    #         "hist_bins": 16,
    #     },
    # }

    # run_options = RunOptions(
    #     clean=False,
    #     n_runs=4,
    #     n_files=64,
    #     analyze=True,
    # )

    # make_sims(base_dir, base_config, run_options)
