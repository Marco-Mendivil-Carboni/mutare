#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

import argparse
from dotenv import load_dotenv
import os
from pathlib import Path
import requests
from shutil import rmtree

from utils.exec import SimJob, SimsConfig, create_sim_jobs, execute_sim_jobs
from utils.plots import plot_sim_jobs

from sims_configs import SIMS_DIR, SIMS_CONFIGS

notify: bool
clean: bool

load_dotenv()
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="make_all_sims", description="make all the simulations for the project"
    )
    parser.add_argument(
        "--notify", action="store_true", help="send Telegram notifications"
    )
    parser.add_argument(
        "--clean", action="store_true", help="prune stale simulation directories"
    )
    return parser.parse_args()


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


def clean_base_dir(base_dir: Path, sim_jobs: list[SimJob]) -> None:
    expected_dirs = {sim_job.sim_dir.resolve() for sim_job in sim_jobs}
    expected_dirs.add((base_dir / "plots").resolve())
    for entry in base_dir.iterdir():
        entry = entry.resolve()
        if entry.is_dir() and entry not in expected_dirs:
            print(f"removing {entry}")
            rmtree(entry)


def make_sims(sims_config: SimsConfig) -> None:
    base_dir = sims_config.init_sim_job.base_dir
    if not base_dir.resolve().is_relative_to(SIMS_DIR.resolve()):
        raise ValueError(f"'{base_dir}' must be inside '{SIMS_DIR}'")

    sim_jobs = create_sim_jobs(sims_config)
    execute_sim_jobs(sim_jobs)
    plot_sim_jobs(sim_jobs)

    if clean:
        clean_base_dir(base_dir, sim_jobs)

    print_and_notify(f"'{base_dir.name}' simulations finished")


def make_all_sims() -> None:
    args = parse_args()

    global notify, clean
    notify = args.notify
    clean = args.clean

    for sims_config in SIMS_CONFIGS:
        make_sims(sims_config)


if __name__ == "__main__":
    try:
        make_all_sims()
    except Exception as exception:
        print_and_notify(f"'make_all_sims' failed: {exception}")
        raise
    else:
        print_and_notify("'make_all_sims' finished")
