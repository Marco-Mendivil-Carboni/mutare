#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

from config import create_config  # , save_config

# from runner import mutare_create, mutare_resume, mutare_analyze, mutare_clean
from results import read_results, print_results
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

p_x = np.array([[stats["mean"] for stats in read_results(sim_dir, 0)["prob_env"]]])
print(p_x)

avg_prob_phe = np.array(
    [[stats["mean"] for stats in read_results(sim_dir, 0)["avg_prob_phe"]]]
)
print(avg_prob_phe)

p_sgx_0 = np.array([[0.5, 0.5], [0.5, 0.5]])

# p_e = p_x
# f_cge = np.exp((np.array(config["prob_rep"]) - np.array(config["prob_dec"])) / p_e)

r_x = np.array([[0.75, 0.25]])  # placeholder, I have to use B (Bio) functions.

b_xgs_l, avg_W_l, sig_W_l = calc_Pareto_front_W(p_x, p_sgx_0, r_x)
print(b_xgs_l[0])

fig, ax = plt.subplots()

ax.plot(avg_W_l, sig_W_l, c="b")

# tmp ------------------------------------------------------------

p_x_s, p_s, p_xgs = calc_aux_dists(p_sgx_0, p_x)


def avg_W(b_xgs: np.ndarray) -> float:
    return np.sum(p_x_s * np.log(b_xgs / r_x))


def sig_W(b_xgs: np.ndarray) -> float:
    return np.sqrt(np.sum(p_x_s * (np.log(b_xgs / r_x) ** 2)) - avg_W(b_xgs) ** 2)


avg_W_sim = avg_W(avg_prob_phe)
sig_W_sim = sig_W(avg_prob_phe)

print(avg_W_sim, sig_W_sim)

# tmp ------------------------------------------------------------

ax.scatter(avg_W_sim, sig_W_sim, c="r", s=20)

fig.savefig("simulations/test-plot.pdf")

plt.close(fig)
