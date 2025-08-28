#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

from config import create_config  # , save_config

# from runner import mutare_create, mutare_resume, mutare_analyze, mutare_clean
from results import read_results, print_results
from Pareto_front import calc_Pareto_front

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

# save_config(config, sim_dir)

# mutare_clean(sim_dir)

# mutare_create(sim_dir)
# mutare_create(sim_dir)

# mutare_resume(sim_dir, 0)
# mutare_resume(sim_dir, 0)

# mutare_resume(sim_dir, 1)
# mutare_resume(sim_dir, 1)

# mutare_analyze(sim_dir)

print_results(sim_dir, 0)
print_results(sim_dir, 1)

p_e = np.array([[stats["mean"] for stats in read_results(sim_dir, 0)["prob_env"]]])
print(p_e)

avg_prob_phe = np.array(
    [[stats["mean"] for stats in read_results(sim_dir, 0)["avg_prob_phe"]]]
)
print(avg_prob_phe)

p_sge = np.array([[1.0, 1.0]])

f_cge = np.exp((np.array(config["prob_rep"]) - np.array(config["prob_dec"])) / p_e)

b_cgs_l, avg_W_l, sig_W_l = calc_Pareto_front(p_e, p_sge, f_cge)
print(b_cgs_l[0])

fig, ax = plt.subplots()

ax.plot(avg_W_l, sig_W_l, c="b")

# tmp ------------------------------------------------------------


def avg_W(b_cgs: np.ndarray) -> float:
    b_cge = b_cgs @ p_sge
    f_b_c = np.sum(f_cge * b_cge, axis=0, keepdims=True)
    return np.sum(p_e * np.log(f_b_c))


def sig_W(b_cgs: np.ndarray) -> float:
    b_cge = b_cgs @ p_sge
    f_b_c = np.sum(f_cge * b_cge, axis=0, keepdims=True)
    return np.sqrt(np.sum(p_e * np.log(f_b_c) ** 2) - avg_W(b_cgs) ** 2)


avg_W_sim = avg_W(avg_prob_phe.T)
sig_W_sim = sig_W(avg_prob_phe.T)

print(avg_W_sim, sig_W_sim)

# tmp ------------------------------------------------------------

ax.scatter(avg_W_sim, sig_W_sim, c="r", s=20)

fig.savefig("simulations/test-plot.pdf")

plt.close(fig)
