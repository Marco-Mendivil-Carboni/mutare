#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

from pathlib import Path
from copy import deepcopy

from utils.config import Config
from utils.exec import RunOptions, SimJob, create_strat_phe_jobs, execute_sim_jobs
from utils.plots import plot_strat_phe_jobs


def make_strat_phe_sims(sim_job: SimJob) -> None:
    strat_phe_jobs = create_strat_phe_jobs(sim_job, 16)
    execute_sim_jobs(strat_phe_jobs)
    plot_strat_phe_jobs(strat_phe_jobs, "plots" / sim_job.base_dir)


if __name__ == "__main__":
    sims_dir = Path("sims")

    default_dir = sims_dir / "default"

    default_config: Config = {
        "model": {
            "n_env": 2,
            "n_phe": 2,
            "rates_trans": [[-1.0, 1.0], [1.0, -1.0]],
            "rates_birth": [[1.2, 0.0], [0.0, 0.8]],
            "rates_death": [[0.0, 1.0], [1.0, 0.0]],
            "prob_mut": 0.001,
        },
        "init": {"n_agents": 100},
        "output": {
            "steps_per_file": 1_048_576,
            "steps_per_save": 256,
            "hist_bins": 16,
        },
    }

    run_options = RunOptions(
        clean=False,
        n_runs=4,
        n_files=96,
        analyze=True,
    )

    make_strat_phe_sims(SimJob(default_dir, default_config, run_options))

    biological_dir = sims_dir / "biological"

    biological_config = deepcopy(default_config)
    biological_config["model"]["rates_birth"] = [[1.0, 0.2], [0.0, 0.0]]
    biological_config["model"]["rates_death"] = [[0.0, 0.0], [1.0, 0.1]]

    make_strat_phe_sims(SimJob(biological_dir, biological_config, run_options))

    extended_dir = sims_dir / "extended"

    extended_config = deepcopy(biological_config)
    extended_config["init"]["n_agents"] = 1000

    make_strat_phe_sims(SimJob(extended_dir, extended_config, run_options))
