import numpy as np
from scipy.optimize import minimize
from tqdm import tqdm
from typing import Tuple, List


def check_dists_0(p_x: np.ndarray, r_x: np.ndarray) -> int:
    n_x = p_x.shape[1]
    assert p_x.shape[0] == 1
    assert r_x.shape[0] == 1
    assert r_x.shape[1] == n_x
    assert np.all(p_x > 0)
    assert np.all(r_x > 0)
    assert np.isclose(np.sum(p_x), 1)
    assert np.isclose(np.sum(r_x), 1)
    return n_x


def check_p_sgx(p_sgx: np.ndarray, n_x: int) -> int:
    n_s = p_sgx.shape[0]
    assert p_sgx.shape[1] == n_x
    assert np.all(p_sgx > 0)
    assert np.all(np.isclose(np.sum(p_sgx, axis=0), 1))
    return n_s


def check_dists(p_x: np.ndarray, p_sgx: np.ndarray, r_x: np.ndarray) -> Tuple[int, int]:
    n_x = check_dists_0(p_x, r_x)
    n_s = check_p_sgx(p_sgx, n_x)
    return n_x, n_s


def calc_aux_dists(
    p_sgx: np.ndarray, p_x: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    p_x_s = p_sgx * p_x
    p_s = np.sum(p_x_s, axis=1, keepdims=True)
    p_xgs = p_x_s / p_s
    return p_x_s, p_s, p_xgs


def calc_gamma_0(r_x: np.ndarray, p_x: np.ndarray) -> float:
    q_x = r_x / p_x
    gamma_0 = np.sqrt(np.sum(p_x * q_x**2) - 1)
    return gamma_0


def calc_gamma(r_x: np.ndarray, p_xgs: np.ndarray, p_s: np.ndarray) -> float:
    q_xgs = r_x / p_xgs
    avg_q2_xgs_s = np.sum(p_xgs * q_xgs**2, axis=1, keepdims=True)
    gamma = np.sqrt(1 / np.sum(p_s / avg_q2_xgs_s) - 1)
    return gamma


def calc_Pareto_front_W(
    p_x: np.ndarray, p_sgx: np.ndarray, r_x: np.ndarray
) -> List[List[np.ndarray] | List[float]]:
    n_x, n_s = check_dists(p_x, p_sgx, r_x)
    p_x_s, p_s, p_xgs = calc_aux_dists(p_sgx, p_x)
    gamma = calc_gamma(r_x, p_xgs, p_s)

    def avg_W(b_xgs: np.ndarray) -> float:
        return np.sum(p_x_s * np.log(b_xgs / r_x))

    def sig_W(b_xgs: np.ndarray) -> float:
        return np.sqrt(np.sum(p_x_s * (np.log(b_xgs / r_x) ** 2)) - avg_W(b_xgs) ** 2)

    def obj_func(b_xgs_f: np.ndarray, alpha: float) -> float:
        b_xgs = np.reshape(b_xgs_f, (n_s, n_x))
        return -(alpha * avg_W(b_xgs) - (1 - alpha) * sig_W(b_xgs))

    def gen_g_s(i_s: int):
        def g_s(b_xgs_f: np.ndarray) -> float:
            b_xgs = np.reshape(b_xgs_f, (n_s, n_x))
            return np.sum(b_xgs[i_s]) - 1

        return g_s

    bnds = tuple((0, 1) for _ in range(n_s * n_x))
    g_s_l = [gen_g_s(i_s) for i_s in range(n_s)]
    cons = [{"type": "eq", "fun": g_s} for g_s in g_s_l]

    b_xgs_o = p_xgs
    b_xgs_f_i = b_xgs_o.flatten()

    alpha_l = list(np.linspace(1, 1 / (1 + gamma), num=1024, endpoint=False))

    b_xgs_l: List[np.ndarray] = []
    avg_W_l: List[float] = []
    sig_W_l: List[float] = []

    for alpha in tqdm(alpha_l, ncols=80):
        res = minimize(
            obj_func,
            b_xgs_f_i,
            args=(alpha,),
            method="SLSQP",
            bounds=bnds,
            constraints=cons,
            tol=4e-12,
        )
        b_xgs_f = res.x
        b_xgs_f_i = b_xgs_f
        b_xgs = np.reshape(b_xgs_f, (n_s, n_x))
        b_xgs_l.append(b_xgs)
        avg_W_l.append(avg_W(b_xgs))
        sig_W_l.append(sig_W(b_xgs))

    res_l: List[List[np.ndarray] | List[float]] = [b_xgs_l, avg_W_l, sig_W_l]
    return res_l
