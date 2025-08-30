#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

from config import DEFAULT_CONFIG, save_config
from runner import mutare_create, mutare_resume, mutare_analyze, mutare_clean
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

config = DEFAULT_CONFIG

save_config(config, sim_dir)

mutare_clean(sim_dir)

mutare_create(sim_dir)
mutare_create(sim_dir)

for _ in range(16):
    mutare_resume(sim_dir, 0)
    mutare_resume(sim_dir, 1)

mutare_analyze(sim_dir)

print_results(sim_dir, 0)
print_results(sim_dir, 1)

p_e = np.array([[stats["mean"] for stats in read_results(sim_dir, 0)["prob_env"]]])
print(p_e)

p_e = np.array([[0.5, 0.5]])
p_sge = np.array([[1.0, 1.0]])

# probability of duplication
p_d_cge = np.array(config["model"]["prob_rep"]) - np.array(config["model"]["prob_dec"])
print(p_d_cge)

# expected sojourn time
prob_trans_env = config["model"]["prob_trans_env"]
tau_env = np.array(
    [[1 / (1 - prob_trans_env[i][i]) for i in range(len(prob_trans_env))]]
).transpose()
print(tau_env)

f_cge = np.exp(p_d_cge * tau_env).transpose()
print(f_cge)
print(np.trace(1 / f_cge**2))

b_cgs_l, avg_W_l, sig_W_l = calc_Pareto_front(p_e, p_sge, f_cge)
print(b_cgs_l[+0])
print(b_cgs_l[-1])

fig, ax = plt.subplots()

ax.plot(avg_W_l, sig_W_l, c="b")

# tmp ------------------------------------------------------------

avg_prob_phe = np.array(
    [[stats["mean"] for stats in read_results(sim_dir, 0)["avg_prob_phe"]]]
).transpose()
print(avg_prob_phe)


def avg_W(b_cgs: np.ndarray) -> float:
    b_cge = b_cgs @ p_sge
    f_b_c = np.sum(f_cge * b_cge, axis=0, keepdims=True)
    return np.sum(p_e * np.log(f_b_c))


def sig_W(b_cgs: np.ndarray) -> float:
    b_cge = b_cgs @ p_sge
    f_b_c = np.sum(f_cge * b_cge, axis=0, keepdims=True)
    return np.sqrt(np.sum(p_e * np.log(f_b_c) ** 2) - avg_W(b_cgs) ** 2)


avg_W_sim = avg_W(avg_prob_phe)
sig_W_sim = sig_W(avg_prob_phe)

print(avg_W_sim, sig_W_sim)

ax.scatter(avg_W_sim, sig_W_sim, c="r", s=20)

# tmp ------------------------------------------------------------

fig.savefig("simulations/test-plot.pdf")

plt.close(fig)
