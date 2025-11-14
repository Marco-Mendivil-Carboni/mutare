#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

from pathlib import Path
from copy import deepcopy

from utils.exec import RunOptions, SimJob, execute_sim_jobs
from utils.exec import create_strat_phe_jobs, create_prob_mut_jobs
from utils.plots import plot_strat_phe_jobs, plot_prob_mut_jobs


def make_strat_phe_sims(sim_job: SimJob) -> None:
    strat_phe_jobs = create_strat_phe_jobs(sim_job, 16)
    execute_sim_jobs(strat_phe_jobs)
    plot_strat_phe_jobs(strat_phe_jobs, "plots" / sim_job.base_dir)


def make_prob_mut_sims(sim_job: SimJob) -> None:
    strat_phe_jobs = create_prob_mut_jobs(sim_job, 16)
    execute_sim_jobs(strat_phe_jobs)
    plot_prob_mut_jobs(strat_phe_jobs, "plots" / sim_job.base_dir)


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
            n_runs=4,
            n_files=128,
            analyze=True,
        ),
    )

    make_strat_phe_sims(symmetric_sim_job)

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

    make_strat_phe_sims(asymmetric_sim_job)

    extended_sim_job = deepcopy(asymmetric_sim_job)
    extended_sim_job.base_dir = sims_dir / "extended"
    extended_sim_job.config["init"]["n_agents"] = 1000

    make_strat_phe_sims(extended_sim_job)

    prob_mut_job = deepcopy(symmetric_sim_job)
    prob_mut_job.base_dir = sims_dir / "prob_mut"
    prob_mut_job.config["model"]["prob_mut"] = 1e-8

    make_prob_mut_sims(prob_mut_job)
