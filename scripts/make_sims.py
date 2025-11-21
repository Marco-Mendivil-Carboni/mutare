#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

from pathlib import Path
import numpy as np
from copy import deepcopy

from utils.exec import RunOptions, SimJob, create_sim_jobs, execute_sim_jobs
from utils.plots import plot_sim_jobs


def make_sims(
    init_sim_job: SimJob,
    strat_phe_sweep: bool,
    prob_mut_sweep: bool,
    n_agents_sweep: bool,
) -> None:
    sim_jobs = create_sim_jobs(
        init_sim_job,
        strat_phe_0_values=np.linspace(start=1 / 16, stop=15 / 16, num=15).tolist()
        if strat_phe_sweep
        else [],
        prob_mut_values=np.logspace(start=-8, stop=0, num=17).tolist()
        if prob_mut_sweep
        else [],
        n_agents_values=np.logspace(start=1, stop=3, num=9).tolist()
        if n_agents_sweep
        else [],
    )
    execute_sim_jobs(sim_jobs)
    plot_sim_jobs(sim_jobs)


if __name__ == "__main__":
    sims_dir = Path("sims")

    symmetric_sim_job = SimJob(
        base_dir=sims_dir / "symmetric",
        config={
            "model": {
                "n_env": 2,
                "n_phe": 2,
                "rates_trans": [
                    [-1.0, 1.0],
                    [1.0, -1.0],
                ],
                "rates_birth": [
                    [1.2, 0.0],
                    [0.0, 0.8],
                ],
                "rates_death": [
                    [0.0, 1.0],
                    [1.0, 0.0],
                ],
                "prob_mut": 0.001,
            },
            "init": {"n_agents": 100},
            "output": {
                "steps_per_file": 1_048_576,
                "steps_per_save": 512,
                "hist_bins": 16,
            },
        },
        run_options=RunOptions(
            clean=False,
            n_runs=4,  # 16
            n_files=128,  # 64
            analyze=False,  # True
        ),
    )

    make_sims(
        init_sim_job=symmetric_sim_job,
        strat_phe_sweep=True,
        prob_mut_sweep=False,  # True
        n_agents_sweep=False,  # True
    )

    asymmetric_sim_job = deepcopy(symmetric_sim_job)
    asymmetric_sim_job.base_dir = sims_dir / "asymmetric"
    asymmetric_sim_job.config["model"]["rates_birth"] = [
        [1.0, 0.2],
        [0.0, 0.0],
    ]
    asymmetric_sim_job.config["model"]["rates_death"] = [
        [0.0, 0.0],
        [1.0, 0.1],
    ]

    make_sims(
        init_sim_job=asymmetric_sim_job,
        strat_phe_sweep=True,
        prob_mut_sweep=False,  # True
        n_agents_sweep=False,  # True
    )

    extended_sim_job = deepcopy(asymmetric_sim_job)
    extended_sim_job.base_dir = sims_dir / "extended"
    extended_sim_job.config["init"]["n_agents"] = 1000

    make_sims(
        init_sim_job=symmetric_sim_job,
        strat_phe_sweep=True,
        prob_mut_sweep=False,
        n_agents_sweep=False,
    )
