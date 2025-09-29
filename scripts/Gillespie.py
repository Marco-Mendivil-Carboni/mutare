#!/home/marcomc/Documents/Doctorado/mutare/.venv/bin/python3

import numpy as np
from typing import List
import matplotlib.pyplot as plt

from utils.config import NormModelParams


def make_uniform_strategy_vector(
    b_vec: List[float], params: NormModelParams
) -> np.ndarray:
    n_e, n_p = params.n_env, params.n_phe
    b = np.zeros((n_e, n_p, n_p))
    for e in range(n_e):
        for j in range(n_p):
            b[e, :, j] = np.array(b_vec)
    return b


def gillespie_mu(params: NormModelParams, b: np.ndarray, N0, T_total=100.0):
    rng = np.random.default_rng()

    n_e, n_p = params.n_env, params.n_phe
    W = np.array(params.rate_trans_env)
    omega_r = np.array(params.rate_rep)
    omega_d = np.array(params.rate_dec)

    e = 0
    n = rng.multinomial(N0, b[0, :, 0])
    t = 0.0

    mu_values = []
    n_extinct = 0

    while t < T_total:
        events = []
        rates = []

        # births
        for j in range(n_p):
            for i in range(n_p):
                r = n[j] * omega_r[e, j] * b[e, i, j]
                if r > 0:
                    events.append(("birth", i))
                    rates.append(r)

        # deaths
        for i in range(n_p):
            r = n[i] * omega_d[e, i]
            if r > 0:
                events.append(("death", i))
                rates.append(r)

        # env switches
        for e2 in range(n_e):
            if e2 != e and W[e, e2] > 0:
                events.append(("env", e2))
                rates.append(W[e, e2])

        R = sum(rates)
        if R == 0:
            break  # absorbing state

        # step
        tau = rng.exponential(1.0 / R)
        t += tau
        event = rng.choice(len(events), p=np.array(rates) / R)

        kind, target = events[event]
        if kind == "birth":
            mu_values.append(+1.0 / n.sum())
            n[target] += 1
        elif kind == "death":
            mu_values.append(-1.0 / n.sum())
            n[target] -= 1
        elif kind == "env":
            e = target

        if n.sum() == 0:
            n_extinct += 1
            n = rng.multinomial(N0, b[0, :, 0])

        while n.sum() > N0:
            idx = rng.choice(len(n), p=n / n.sum())
            n[idx] -= 1

        print(t, end="\r")

    print(f"{np.array(mu_values).sum() / T_total}, {n_extinct / T_total}")

    return np.array(mu_values).sum() / T_total, n_extinct / T_total


if __name__ == "__main__":
    params = NormModelParams(
        n_env=2,
        n_phe=2,
        rate_trans_env=[[-1.0, 1.0], [1.0, -1.0]],
        rate_rep=[[1.2, 0.0], [0.0, 0.8]],
        rate_dec=[[0.0, 1.4], [1.0, 0.0]],
        prob_mut=0.0,
        std_dev_mut=0.0,
        time_step=1 / 64,
    )

    i = 0

    prob_phe_0_list = list(map(float, np.linspace(1 / 16, 1, 16)))
    for prob_phe_0 in prob_phe_0_list:
        b_vec = [prob_phe_0, 1 - prob_phe_0]
        b = make_uniform_strategy_vector(b_vec, params)

        print(f"{i}:")
        i += 1

        avg_mu, rate_extinct = gillespie_mu(params, b, 256, 16384)

        plt.scatter(avg_mu, rate_extinct)

    plt.yscale("log")

    plt.show()
