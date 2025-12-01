#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

import argparse
from pathlib import Path
from shutil import rmtree
import numpy as np
from copy import deepcopy
from dotenv import load_dotenv
import os
import requests

from utils.exec import RunOptions, SimJob, create_sim_jobs, execute_sim_jobs
from utils.plots import plot_sim_jobs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="make_all_sims", description="make all the simulations for the project"
    )
    parser.add_argument(
        "--notify", action="store_true", help="send Telegram notifications"
    )
    parser.add_argument(
        "--skip-analysis", action="store_true", help="skip simulation analysis"
    )
    parser.add_argument(
        "--prune-sims-dir", action="store_true", help="prune simulations directory"
    )
    return parser.parse_args()


notify = False
prune_sims_dir = False

load_dotenv()
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


def print_and_notify(message: str) -> None:
    print(message)
    if not notify:
        return
    if TOKEN and CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                params={"chat_id": CHAT_ID, "text": message},
                timeout=16,
            )
        except Exception as exception:
            print(f"failed to send notification: {exception}")
    else:
        print("failed to find Telegram credentials")


SIMS_DIR = Path("sims")


def make_sims(
    init_sim_job: SimJob,
    strat_phe_sweep: bool,
    prob_mut_sweep: bool,
    n_agents_sweep: bool,
) -> None:
    strat_phe_0_values = np.linspace(start=1 / 16, stop=15 / 16, num=15)
    prob_mut_values = np.logspace(start=-8, stop=0, num=17)
    n_agents_values = np.logspace(start=1.5, stop=3.5, num=9).round().astype(int)
    sim_jobs = create_sim_jobs(
        init_sim_job,
        strat_phe_0_values.tolist() if strat_phe_sweep else [],
        prob_mut_values.tolist() if prob_mut_sweep else [],
        n_agents_values.tolist() if n_agents_sweep else [],
    )
    execute_sim_jobs(sim_jobs)

    if prune_sims_dir:
        norm_sim_dirs = [sim_job.sim_dir.resolve() for sim_job in sim_jobs]
        for entry in init_sim_job.base_dir.iterdir():
            norm_entry = entry.resolve()
            if not norm_entry.is_relative_to(SIMS_DIR.resolve()):
                raise ValueError(f"path outside SIMS_DIR: {norm_entry}")
            if norm_entry not in norm_sim_dirs:
                print(f"removing {entry}")
                if entry.is_dir():
                    rmtree(norm_entry)
                else:
                    norm_entry.unlink()

    plot_sim_jobs(sim_jobs)

    print_and_notify(f"Simulations finished: {init_sim_job.base_dir}")


def main() -> None:
    args = parse_args()

    global notify, prune_sims_dir
    notify = args.notify
    prune_sims_dir = args.prune_sims_dir

    symmetric_sim_job = SimJob(
        base_dir=SIMS_DIR / "symmetric",
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
                "steps_per_save": 1_024,
                "hist_bins": 16,
            },
        },
        run_options=RunOptions(
            n_runs=16,
            n_files=64,
            analyze=not args.skip_analysis,
        ),
    )

    make_sims(
        init_sim_job=symmetric_sim_job,
        strat_phe_sweep=True,
        prob_mut_sweep=True,
        n_agents_sweep=True,
    )

    asymmetric_sim_job = deepcopy(symmetric_sim_job)
    asymmetric_sim_job.base_dir = SIMS_DIR / "asymmetric"
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
        prob_mut_sweep=True,
        n_agents_sweep=True,
    )

    extended_sim_job = deepcopy(asymmetric_sim_job)
    extended_sim_job.base_dir = SIMS_DIR / "extended"
    extended_sim_job.config["init"]["n_agents"] = 1000

    make_sims(
        init_sim_job=extended_sim_job,
        strat_phe_sweep=True,
        prob_mut_sweep=False,
        n_agents_sweep=False,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        print_and_notify(f"Program execution failed: {exception}")
        raise
    else:
        print_and_notify("All simulations finished successfully")
