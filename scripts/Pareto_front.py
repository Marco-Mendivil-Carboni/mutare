import numpy as np

from scipy.optimize import minimize, basinhopping

from tqdm import tqdm

from typing import Tuple, List, Callable


def check_p_e(p_e: np.ndarray) -> int:
    n_e = p_e.shape[1]
    assert p_e.shape[0] == 1
    assert np.all(p_e > 0)
    assert np.isclose(np.sum(p_e), 1)
    return n_e


def check_p_sge(p_sge: np.ndarray, n_e: int) -> int:
    n_s = p_sge.shape[0]
    assert p_sge.shape[1] == n_e
    assert np.all(p_sge > 0)
    assert np.all(np.isclose(np.sum(p_sge, axis=0), 1))
    return n_s


def check_f_cge(f_cge: np.ndarray, n_e: int) -> int:
    n_c = f_cge.shape[0]
    assert f_cge.shape[1] == n_e
    assert np.all(f_cge > 0)
    return n_c


def check_dists(
    p_e: np.ndarray, p_sge: np.ndarray, f_cge: np.ndarray
) -> Tuple[int, int, int]:
    n_e = check_p_e(p_e)
    n_s = check_p_sge(p_sge, n_e)
    n_c = check_f_cge(f_cge, n_e)
    return n_e, n_s, n_c


def calc_Pareto_front(
    p_e: np.ndarray, p_sge: np.ndarray, f_cge: np.ndarray
) -> Tuple[List[np.ndarray], List[float], List[float]]:
    _, n_s, n_c = check_dists(p_e, p_sge, f_cge)

    prng = np.random.default_rng(1234)

    def gen_random_b_cgs() -> np.ndarray:
        b_cgs = prng.uniform(size=(n_c, n_s))
        b_cgs = b_cgs / np.sum(b_cgs, axis=0, keepdims=True)
        return b_cgs

    def avg_W(b_cgs: np.ndarray) -> float:
        b_cge = b_cgs @ p_sge
        f_b_c = np.sum(f_cge * b_cge, axis=0, keepdims=True)
        return np.sum(p_e * np.log(f_b_c))

    def sig_W(b_cgs: np.ndarray) -> float:
        b_cge = b_cgs @ p_sge
        f_b_c = np.sum(f_cge * b_cge, axis=0, keepdims=True)
        return np.sqrt(np.sum(p_e * np.log(f_b_c) ** 2) - avg_W(b_cgs) ** 2)

    def obj_func(b_cgs_f: np.ndarray, alpha: float) -> float:
        b_cgs = np.reshape(b_cgs_f, (n_c, n_s))
        return -(alpha * avg_W(b_cgs) - (1 - alpha) * sig_W(b_cgs))

    def gen_g_s(i_s: int) -> Callable[[np.ndarray], float]:
        def g_s(b_cgs_f: np.ndarray) -> float:
            b_cgs = np.reshape(b_cgs_f, (n_c, n_s))
            return np.sum(b_cgs[:, i_s]) - 1

        return g_s

    bnds = tuple((0.0, 1.0) for _ in range(n_c * n_s))

    g_s_l = [gen_g_s(i_s) for i_s in range(n_s)]
    cons = [{"type": "eq", "fun": g_s} for g_s in g_s_l]

    b_cgs = gen_random_b_cgs()
    b_cgs_f_i = b_cgs.flatten()

    alpha_l = list(np.linspace(1, 0, num=1024, endpoint=False))

    class TakeStep:
        def __call__(self, _: np.ndarray) -> np.ndarray:
            b_cgs = gen_random_b_cgs()
            b_cgs_f = b_cgs.flatten()
            return b_cgs_f

    take_step = TakeStep()

    class ShowMessage:
        def __init__(self) -> None:
            self.f_min = np.inf
            self.niter = 0
            self.niter_eq = 0

        def __call__(self, _: np.ndarray, f: float, accept: bool) -> None:
            self.niter += 1
            self.niter_eq += 1
            if accept and f < self.f_min:
                self.f_min = f
                self.niter_eq = 0
            print(
                "f_min={: .16f}".format(self.f_min),
                "niter={:04d}".format(self.niter),
                "niter_eq={:04d}".format(self.niter_eq),
                end="\r",
            )

    show_message = ShowMessage()

    res = basinhopping(
        obj_func,
        b_cgs_f_i,
        niter=1024,
        minimizer_kwargs={
            "args": (1,),
            "method": "SLSQP",
            "bounds": bnds,
            "constraints": cons,
            "tol": 4e-12,
        },
        take_step=take_step,
        callback=show_message,
        niter_success=256,
        rng=prng,
    )
    b_cgs_f = res.x
    b_cgs_f_i = b_cgs_f

    print("")

    b_cgs_l: List[np.ndarray] = []
    avg_W_l: List[float] = []
    sig_W_l: List[float] = []

    for alpha in tqdm(alpha_l, ncols=80):
        res = minimize(
            obj_func,
            b_cgs_f_i,
            args=(alpha,),
            method="SLSQP",
            bounds=bnds,
            constraints=cons,
            tol=4e-12,
        )
        b_cgs_f = res.x
        b_cgs_f_i = b_cgs_f
        b_cgs = np.reshape(b_cgs_f, (n_c, n_s))
        b_cgs_l.append(b_cgs)
        avg_W_l.append(avg_W(b_cgs))
        sig_W_l.append(sig_W(b_cgs))

    return b_cgs_l, avg_W_l, sig_W_l
