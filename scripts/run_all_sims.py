#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

from config import create_config, save_config
from runner import mutare_create, mutare_resume, mutare_analyze, mutare_clean
from reports import read_reports, print_reports
from Pareto_front import calc_aux_dists
from Pareto_front import calc_Pareto_front_W

import numpy as np
from pathlib import Path
import matplotlib as mpl
from matplotlib import pyplot as plt

mpl.use("pdf")

mpl.rcParams["text.usetex"] = True
mpl.rcParams["font.family"] = "serif"

cm = 1 / 2.54
mpl.rcParams["figure.figsize"] = [16.00 * cm, 10.00 * cm]
mpl.rcParams["figure.constrained_layout.use"] = True


sim_dir = Path("simulations")

sim_dir.mkdir(parents=True, exist_ok=True)

config = create_config()

save_config(config, sim_dir)

mutare_clean(sim_dir)

mutare_create(sim_dir)
mutare_create(sim_dir)

mutare_resume(sim_dir, 0)
mutare_resume(sim_dir, 0)

mutare_resume(sim_dir, 1)
mutare_resume(sim_dir, 1)

mutare_analyze(sim_dir)

print_reports(sim_dir, 0)
print_reports(sim_dir, 1)


def get_prob_env_means(sim_dir: Path, run_idx: int) -> float | None:
    for report in read_reports(sim_dir, run_idx):
        if "prob_env" in report:
            print("hey")
            return report["prob_env"][:]["mean"]
    return None


p_x = get_prob_env_means(sim_dir, 0)
print(p_x)
