import pandas as pd
import numpy as np
import matplotlib as mpl
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.gridspec import GridSpec
from matplotlib.colors import Normalize, PowerNorm, LogNorm
from matplotlib.cm import ScalarMappable
from scipy.interpolate import make_splrep, LSQBivariateSpline
from typing import Any, Literal

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

N_SPLINE_VALUES = 64


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


def create_standard_figure(x_col: str, y_col: str) -> tuple[Figure, Axes]:
    fig = Figure(figsize=FIGSIZE)
    ax = fig.add_subplot()
    ax.set_xlabel(COL_TEX_LABELS[x_col])
    ax.set_ylabel(COL_TEX_LABELS[y_col])
    return fig, ax


def create_colorbar_figure(
    x_col: str, y_col: str, two_panels: bool
) -> tuple[Figure, list[Axes]]:
    fig = Figure(figsize=FIGSIZE)

    if two_panels:
        gs = GridSpec(1, 3, figure=fig, width_ratios=[64, 4, 1], wspace=0)
        ax_main = fig.add_subplot(gs[0, 0])
        ax_side = fig.add_subplot(gs[0, 1])
        ax_bar = fig.add_subplot(gs[0, 2])
        ax_main.set_xlabel(COL_TEX_LABELS[x_col])
        ax_main.set_ylabel(COL_TEX_LABELS[y_col])
        ax_side.set_xticks([])
        ax_side.set_yticks([])

        return fig, [ax_main, ax_side, ax_bar]

    else:
        gs = GridSpec(1, 2, figure=fig, width_ratios=[64, 1], wspace=0)
        ax_main = fig.add_subplot(gs[0, 0])
        ax_bar = fig.add_subplot(gs[0, 1])
        ax_main.set_xlabel(COL_TEX_LABELS[x_col])
        ax_main.set_ylabel(COL_TEX_LABELS[y_col])

        return fig, [ax_main, ax_bar]


def add_top_label(ax: Axes, label: str) -> None:
    sec_ax = ax.secondary_xaxis("top")
    sec_ax.set_xticks([])
    sec_ax.set_xticks([], minor=True)
    sec_ax.set_xlabel(label)


def get_sim_color_and_label(df: pd.DataFrame) -> tuple[str, str]:
    sim_types = df["sim_type"].unique()
    if len(sim_types) != 1:
        raise ValueError("sim_type not unique")
    sim_type = sim_types[0]
    return SIM_COLORS[sim_type], SIM_LABELS[sim_type]


def plot_horizontal_bands(
    ax: Axes, df: pd.DataFrame, mean_col: tuple[str, str], span_col: tuple[str, str]
) -> None:
    color, label = get_sim_color_and_label(df)
    for mean, span in df[[mean_col, span_col]].itertuples(index=False):
        ax.axhline(mean, c=color, label=label, ls=PLOT_STYLE["ls"])
        ax.axhspan(mean + span, mean - span, color=color, **FILL_STYLE)
        label = None


def plot_errorbar(
    ax: Axes, df: pd.DataFrame, x_col: str, y_col: str, use_xerr: bool
) -> None:
    color, label = get_sim_color_and_label(df)
    x = df[(x_col, "mean")] if use_xerr else df[x_col]
    y = df[(y_col, "mean")]
    xerr = df[(x_col, "sem")] if use_xerr else None
    yerr = df[(y_col, "sem")]
    ax.errorbar(x, y, yerr, xerr, c=color, label=label, **PLOT_STYLE)


def plot_errorband(
    ax: Axes, df: pd.DataFrame, x_col: str, y_col: str, y_span_col: str
) -> None:
    color, _ = get_sim_color_and_label(df)
    x = df[x_col]
    y = df[(y_col, "mean")]
    y_span = df[(y_span_col, "mean")]
    ax.fill_between(x, y - y_span, y + y_span, color=color, **FILL_STYLE)


def count_hist_bins(df: pd.DataFrame, y_col: str) -> int:
    hist_bins = 0
    while (f"{y_col}_{hist_bins}", "mean") in df.columns:
        hist_bins += 1
    return hist_bins


def generate_heatmap_matrix(
    df: pd.DataFrame, z_col: str, hist_bins: int
) -> list[list[float]]:
    hm_z = []
    for bin in range(hist_bins):
        hm_z.append((hist_bins * df[(f"{z_col}_{bin}", "mean")]).tolist())
    return hm_z


def get_heatmap_norm(
    type: Literal["linear"] | Literal["power"] | Literal["log"],
    vmin: float,
    vmax: float,
) -> Normalize:
    if type == "log":
        norm = LogNorm(vmin, vmax)
    elif type == "power":
        norm = PowerNorm(0.5, vmin, vmax)
    else:
        norm = Normalize(vmin, vmax)
    return norm


def set_heatmap_colorbar(
    fig: Figure, ax_bar: Axes, z_col: str, sm: ScalarMappable
) -> None:
    cbar = fig.colorbar(sm, cax=ax_bar, aspect=64)
    cbar.ax.set_ylabel(COL_TEX_LABELS[z_col])


def plot_main_heatmap(
    fig: Figure, ax_main: Axes, ax_bar: Axes, df: pd.DataFrame, x_col: str, z_col: str
) -> None:
    _, label = get_sim_color_and_label(df)
    add_top_label(ax_main, label)
    hist_bins = count_hist_bins(df, z_col)
    hm_x = df[x_col].tolist()
    hm_y = [(i + 0.5) / hist_bins for i in range(hist_bins)]
    hm_z = generate_heatmap_matrix(df, z_col, hist_bins)
    norm = get_heatmap_norm("power", 0, hist_bins)
    im = ax_main.pcolormesh(hm_x, hm_y, hm_z, norm=norm, cmap=CMAP, shading="nearest")
    ax_main.set_xlim(hm_x[0], hm_x[-1])
    set_heatmap_colorbar(fig, ax_bar, z_col, im)


def plot_side_heatmap(ax_side: Axes, df: pd.DataFrame, z_col: str) -> None:
    _, label = get_sim_color_and_label(df)
    add_top_label(ax_side, label)
    hist_bins = count_hist_bins(df, z_col)
    hm_x = [0.0, 1.0]
    hm_y = [i / hist_bins for i in range(hist_bins + 1)]
    hm_z = generate_heatmap_matrix(df, z_col, hist_bins)
    norm = get_heatmap_norm("power", 0, hist_bins)
    ax_side.pcolormesh(hm_x, hm_y, hm_z, norm=norm, cmap=CMAP)


def get_optimal_strat_phe_0(
    df: pd.DataFrame, job: SimJob, y_col: str, opt: Literal["max"] | Literal["min"]
) -> float:
    fixed_i_df = FILTERS["fixed_i"](df, job).sort_values("strat_phe_0_i")

    x = fixed_i_df["strat_phe_0_i"]
    y = fixed_i_df[(y_col, "mean")]
    if y_col == "extinct_rate":
        x, y = x[y > 0], y[y > 0]

    spline = make_splrep(x, y)

    x = np.linspace(0, 1, N_SPLINE_VALUES)
    y = spline(x)
    if opt == "max":
        opt_idx = np.argmax(y)
    else:
        opt_idx = np.argmin(y)

    return x[opt_idx]


def plot_dist_phe_0_lims(ax: Axes, df: pd.DataFrame, job: SimJob) -> None:
    n_env = job.config["model"]["n_env"]
    n_phe = job.config["model"]["n_phe"]
    if n_env != 2 or n_phe != 2:
        return

    strat_phe_0_i_values = df["strat_phe_0_i"].dropna().unique().tolist()

    for env in range(n_env):
        rates_birth = np.array(job.config["model"]["rates_birth"][env])
        rates_death = np.array(job.config["model"]["rates_death"][env])
        dist_phe_0_lim_values = []
        for strat_phe_0_i in strat_phe_0_i_values:
            strat_phe_1_i = 1.0 - strat_phe_0_i
            matrix = np.array(
                [strat_phe_0_i * rates_birth, strat_phe_1_i * rates_birth]
            )
            matrix[0][0] -= rates_death[0]
            matrix[1][1] -= rates_death[1]
            eigenvalues, eigenvectors = np.linalg.eig(matrix)
            max_index = np.argmax(eigenvalues)
            max_eigenvector = eigenvectors[:, max_index]
            dist_phe_0_lim_values.append(
                float(max_eigenvector[0] / np.sum(max_eigenvector))
            )

        ax.plot(strat_phe_0_i_values, dist_phe_0_lim_values, ls="--", **LINE_STYLE)


def plot_expected_values(
    ax: Axes, df: pd.DataFrame, job: SimJob, param: str, y_col: str
) -> None:
    param_df = FILTERS[param](df, job).sort_values(param)
    fixed_i_df = FILTERS["fixed_i"](df, job).sort_values("strat_phe_0_i")

    spline = make_splrep(fixed_i_df["strat_phe_0_i"], fixed_i_df[(y_col, "mean")])
    strat_phe_0, dist_avg_strat_phe_0 = get_dist_avg_strat_phe_0(param_df)

    exp_values = np.zeros(len(param_df))
    hist_bins = len(strat_phe_0)
    for bin in range(hist_bins):
        exp_values += dist_avg_strat_phe_0[bin] * spline(strat_phe_0[bin]) / hist_bins

    ax.plot(param_df[param], exp_values, ls="--", **LINE_STYLE)


def plot_extinct_times(ax: Axes, df: pd.DataFrame) -> None:
    extinct_times = df["time"][df["n_extinct"].diff() > 0]
    for extinct_time in extinct_times:
        ax.axvline(extinct_time, ls=":", c="k", lw=0.25, alpha=0.5)


def plot_time_series(
    ax: Axes, df: pd.DataFrame, y_col: str, y_span_col: str | None
) -> None:
    color, label = get_sim_color_and_label(df)
    x = df["time"]
    y = df[y_col]
    ax.scatter(x, y, c=color, label=label, lw=0.0, s=0.25)
    if y_span_col is not None:
        y_span = df[y_span_col]
        ax.fill_between(x, y - y_span, y + y_span, color=color, **FILL_STYLE)


def get_dist_avg_strat_phe_0(df: pd.DataFrame) -> tuple[list[Any], list[Any]]:
    hist_bins = count_hist_bins(df, "dist_avg_strat_phe_0")
    x, y = [], []
    for bin in range(hist_bins):
        x.append((bin + 1 / 2) / hist_bins)
        y.append(hist_bins * df[(f"dist_avg_strat_phe_0_{bin}", "mean")])
    return x, y


def plot_avg_strat_phe_0(
    fig: Figure, ax_main: Axes, ax_bar: Axes, df: pd.DataFrame, data: list[Any]
) -> None:
    n_agents_i_values = sorted(df["n_agents_i"].unique())
    prob_mut_values = sorted(df["prob_mut"].unique())
    im = ax_main.pcolormesh(
        n_agents_i_values,
        prob_mut_values,
        np.array(data).transpose(),
        vmin=0.2,
        vmax=0.8,
        cmap=CMAP,
        shading="nearest",
    )
    ax_main.set_xlim(n_agents_i_values[0], n_agents_i_values[-1])
    ax_main.set_ylim(prob_mut_values[0], prob_mut_values[-1])
    set_heatmap_colorbar(fig, ax_bar, "avg_strat_phe_0", im)


def plot_colored_errorbar(
    ax: Axes, df: pd.DataFrame, x_col: str, y_col: str, norm: Normalize, value: float
) -> None:
    color = CMAP(norm(value))
    x = df[x_col]
    y = df[(y_col, "mean")]
    yerr = df[(y_col, "sem")]
    ax.errorbar(x, y, yerr, None, c=color, **PLOT_STYLE)
