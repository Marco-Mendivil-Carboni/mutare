#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

import argparse
from dotenv import load_dotenv
import os
import requests

from utils.exec import SimsConfig, create_sim_jobs, exec_sim_jobs
from utils.plots import plot_sim_jobs

from sims_configs import SIMS_DIR, SIMS_CONFIGS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="make_all_sims", description="make all the simulations for the project"
    )
    parser.add_argument(
        "--notify", action="store_true", help="send Telegram notifications"
    )
    return parser.parse_args()


load_dotenv()
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


def log(message: str, notify: bool) -> None:
    print(message, flush=True)
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


def make_sims(sims_config: SimsConfig, notify: bool) -> None:
    base_dir = sims_config.init_sim_job.base_dir
    if not base_dir.resolve().is_relative_to(SIMS_DIR.resolve()):
        raise ValueError(f"'{base_dir}' must be inside '{SIMS_DIR}'")

    sim_jobs = create_sim_jobs(sims_config)
    exec_sim_jobs(sim_jobs)
    plot_sim_jobs(sim_jobs)

    log(f"'{base_dir.name}' simulations finished", notify)


if __name__ == "__main__":
    args = parse_args()
    notify = args.notify

    try:
        for sims_config in SIMS_CONFIGS:
            make_sims(sims_config, notify)

    except Exception as exception:
        log(f"'make_all_sims' failed: {exception}", notify)
        raise
    else:
        log("'make_all_sims' finished", notify)
