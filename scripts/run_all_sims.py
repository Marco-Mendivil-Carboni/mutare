#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

from config import DEFAULT_CONFIG, save_config
from runner import mutare_make_sim
from results import read_results, print_results

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

fig, ax = plt.subplots()

sim_dir = Path("simulations/with_mut/")
sim_dir.mkdir(parents=True, exist_ok=True)

config = DEFAULT_CONFIG
save_config(config, sim_dir)

mutare_make_sim(sim_dir, 1, 64)
print_results(sim_dir, 0)

results = read_results(sim_dir, 0)
n_agt = config["init"]["n_agt"]
mean = results["n_agt_diff"][0]["mean"]
std_dev = results["n_agt_diff"][0]["std_dev"]
sem = results["n_agt_diff"][0]["sem"]
n_eff = (std_dev / sem) ** 2
avg_W = mean
avg_W_err = sem
sig_W = std_dev
sig_W_err = std_dev / np.sqrt(2 * (n_eff - 1))

ax.errorbar(avg_W, sig_W, avg_W_err, sig_W_err, c="r")

n_sims = 16
prob_phe_l = list(np.linspace(0, 1, num=n_sims))

config["model"]["prob_mut"] = 0.0

for sim_idx, prob_phe in enumerate(prob_phe_l):
    sim_dir = Path(f"simulations/fixed-{sim_idx:02d}/")
    sim_dir.mkdir(parents=True, exist_ok=True)

    config["init"]["prob_phe"] = [float(prob_phe), float(1 - prob_phe)]
    save_config(config, sim_dir)

    mutare_make_sim(sim_dir, 1, 64)
    print_results(sim_dir, 0)

    results = read_results(sim_dir, 0)
    n_agt = config["init"]["n_agt"]
    mean = results["n_agt_diff"][0]["mean"]
    std_dev = results["n_agt_diff"][0]["std_dev"]
    sem = results["n_agt_diff"][0]["sem"]
    n_eff = (std_dev / sem) ** 2
    avg_W = mean
    avg_W_err = sem
    sig_W = std_dev
    sig_W_err = std_dev / np.sqrt(2 * (n_eff - 1))

    ax.errorbar(avg_W, sig_W, avg_W_err, sig_W_err, c="b")

fig.savefig("simulations/test-plot.pdf")

plt.close(fig)
