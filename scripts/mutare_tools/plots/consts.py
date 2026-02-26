import pandas as pd
import matplotlib as mpl
from typing import Any

from ..exec import SimJob
from ..analysis import SimType

mpl.use("pdf")

mpl.rcParams["text.usetex"] = True
mpl.rcParams["text.latex.preamble"] = "\\usepackage{lmodern}\\usepackage{mathtools}"
mpl.rcParams["font.family"] = "lmodern"
mpl.rcParams["font.size"] = 10
mpl.rcParams["figure.dpi"] = 1200
mpl.rcParams["figure.constrained_layout.use"] = True

CM = 1 / 2.54
FIGSIZE = (8.0 * CM, 4.94 * CM)

PLOT_STYLE: dict[str, Any] = dict(ls="--", marker="o", markersize=2)
FILL_STYLE: dict[str, Any] = dict(lw=0.0, alpha=0.5)
LINE_STYLE: dict[str, Any] = dict(c="k", lw=1.0, alpha=0.5)

COLORS = {
    "blue": "#4e79a7",
    "orange": "#f28e2b",
    "red": "#e15759",
    "teal": "#76b7b2",
    "green": "#59a14f",
    "yellow": "#edc948",
    "mauve": "#b07aa1",
    "pink": "#ff9da7",
    "brown": "#9c755f",
    "gray": "#bab0ac",
}

CMAP = mpl.colormaps["magma_r"]

SIM_COLORS: dict[SimType, Any] = {
    SimType.FIXED: COLORS["blue"],
    SimType.EVOL: COLORS["teal"],
    SimType.RANDOM: COLORS["green"],
}
SIM_LABELS: dict[SimType, str] = {
    SimType.FIXED: "\\texttt{fixed}",
    SimType.EVOL: "\\texttt{evol}",
    SimType.RANDOM: "\\texttt{evol(r)}",
}

COL_TEX_LABELS: dict[str, str] = {
    "strat_phe_0_i": "$s(A)_{\\text{ini}}$",
    "prob_mut": "$p_{\\text{mut}}$",
    "n_agents_i": "$N_{\\text{ini}}$",
    "time": "$t$",
    "n_agents": "$N$",
    "n_extinct": "$n_{\\text{ext}}$",
    "norm_n_agents": "$N/N_{\\text{ini}}$",
    "dist_n_agents": "$p(N/N_{\\text{ini}})$",
    "avg_growth_rate": "$\\langle\\mu\\rangle$",
    "extinct_rate": "$r_{\\text{ext}}$",
    "avg_strat_phe_0": "$\\langle s(A)\\rangle$",
    "dist_avg_strat_phe_0": "$p(\\langle s(A)\\rangle)$",
    "dist_phe_0": "$p(A)$",
    "std_dev_growth_rate": "$\\sigma_{\\mu}$",
    "avg_birth_rate": "$\\langle\\mu_b\\rangle$",
}

N_EVALS = 64


def strat_phe_0_i_filter(df: pd.DataFrame, job: SimJob) -> pd.DataFrame:
    return df[
        ((df["prob_mut"] == job.config["model"]["prob_mut"]) | (df["prob_mut"] == 0))
        & (df["n_agents_i"] == job.config["init"]["n_agents"])
    ]


def prob_mut_filter(df: pd.DataFrame, job: SimJob) -> pd.DataFrame:
    return df[
        (df["sim_type"] == SimType.RANDOM)
        & (df["n_agents_i"] == job.config["init"]["n_agents"])
    ]


def n_agents_i_filter(df: pd.DataFrame, job: SimJob) -> pd.DataFrame:
    return df[
        (df["sim_type"] == SimType.RANDOM)
        & (df["prob_mut"] == job.config["model"]["prob_mut"])
    ]


def random_filter(df: pd.DataFrame, job: SimJob) -> pd.DataFrame:
    return df[(df["sim_type"] == SimType.RANDOM)]


def fixed_filter(df: pd.DataFrame, job: SimJob) -> pd.DataFrame:
    return df[(df["sim_type"] == SimType.FIXED)]


def fixed_i_filter(df: pd.DataFrame, job: SimJob) -> pd.DataFrame:
    return df[
        (df["sim_type"] == SimType.FIXED)
        & (df["n_agents_i"] == job.config["init"]["n_agents"])
    ]


FILTERS = {
    "strat_phe_0_i": strat_phe_0_i_filter,
    "prob_mut": prob_mut_filter,
    "n_agents_i": n_agents_i_filter,
    "random": random_filter,
    "fixed": fixed_filter,
    "fixed_i": fixed_i_filter,
}
