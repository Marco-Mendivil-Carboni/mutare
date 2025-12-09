import pandas as pd
import numpy as np
import matplotlib as mpl
from matplotlib.figure import Figure
from matplotlib.axes import Axes
import matplotlib.gridspec as gridspec
import matplotlib.colors as colors
from typing import Any

from .exec import SimJob
from .analysis import collect_avg_analyses, SimType

mpl.use("pdf")

mpl.rcParams["text.usetex"] = True
mpl.rcParams["text.latex.preamble"] = "\\usepackage{lmodern}\\usepackage{mathtools}"
mpl.rcParams["font.family"] = "lmodern"
mpl.rcParams["font.size"] = 10
mpl.rcParams["figure.dpi"] = 1200
mpl.rcParams["figure.constrained_layout.use"] = True

CM = 1 / 2.54
FIGSIZE = (8.0 * CM, 5.0 * CM)

COLORS = [
    "#df591f",
    "#d81e2c",
    "#d21e6f",
    "#cc1dad",
    "#a31cc5",
    "#611bbf",
    "#221ab9",
    "#194bb2",
    "#1880ac",
    "#17a69b",
    "#169f62",
    "#15992c",
]

PLOT_STYLE: dict[str, Any] = dict(ls=":", marker="o", markersize=2)
FILL_STYLE: dict[str, Any] = dict(lw=0.0, alpha=0.5)
LINE_STYLE: dict[str, Any] = dict(ls=":", lw=1.0, alpha=0.5)

CMAP = colors.LinearSegmentedColormap.from_list("custom", list(reversed(COLORS)))

SIM_COLORS: dict[SimType, str] = {
    SimType.FIXED: COLORS[1],
    SimType.EVOL: COLORS[5],
    SimType.RANDOM: COLORS[9],
}
SIM_LABELS: dict[SimType, str] = {
    SimType.FIXED: "\\texttt{fixed}",
    SimType.EVOL: "\\texttt{evol}",
    SimType.RANDOM: "\\texttt{random}",
}

EXTRA_COLORS = [COLORS[3], COLORS[7], COLORS[11]]

COL_TEX_LABELS: dict[str, str] = {
    "strat_phe_0": "$s(0)_i$",
    "prob_mut": "$p_{\\text{mut}}$",
    "n_agents": "$N_i$",
    "dist_n_agents": "$N/N_i$",
    "growth_rate": "$\\langle\\mu\\rangle$",
    "extinct_rate": "$r_e$",
    "avg_strat_phe_0": "$\\langle s(0)\\rangle$",
    "dist_strat_phe_0": "$s(0)$",
    "dist_phe_0": "$p_{\\phi}(0)$",
}


def create_standard_figure(x_col: str, y_col: str) -> tuple[Figure, Axes]:
    fig = Figure(figsize=FIGSIZE)
    ax = fig.add_subplot()
    ax.set_xlabel(COL_TEX_LABELS[x_col])
    ax.set_ylabel(COL_TEX_LABELS[y_col])
    return fig, ax


def create_heatmap_figure(
    x_col: str, y_col: str, two_panels: bool
) -> tuple[Figure, list[Axes]]:
    fig = Figure(figsize=FIGSIZE)

    if two_panels:
        gs = gridspec.GridSpec(1, 3, figure=fig, width_ratios=[64, 4, 1], wspace=0)
        ax_main = fig.add_subplot(gs[0, 0])
        ax_side = fig.add_subplot(gs[0, 1])
        ax_cbar = fig.add_subplot(gs[0, 2])
        ax_main.set_xlabel(COL_TEX_LABELS[x_col])
        ax_main.set_ylabel(COL_TEX_LABELS[y_col])
        ax_side.set_xticks([])
        ax_side.set_yticks([])

        return fig, [ax_main, ax_side, ax_cbar]

    else:
        gs = gridspec.GridSpec(1, 2, figure=fig, width_ratios=[64, 1], wspace=0)
        ax_main = fig.add_subplot(gs[0, 0])
        ax_cbar = fig.add_subplot(gs[0, 1])
        ax_main.set_xlabel(COL_TEX_LABELS[x_col])
        ax_main.set_ylabel(COL_TEX_LABELS[y_col])

        return fig, [ax_main, ax_cbar]


def add_top_label(ax: Axes, label: str) -> None:
    sec_ax = ax.secondary_xaxis("top")
    sec_ax.set_xticks([])
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
        ax.axhline(mean, c=color, label=label, ls=":")
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
    df: pd.DataFrame, y_col: str, hist_bins: int
) -> list[list[float]]:
    hm_z = []
    for bin in range(hist_bins):
        hm_z.append((hist_bins * df[(f"{y_col}_{bin}", "mean")]).tolist())
    return hm_z


def plot_main_heatmap(
    fig: Figure, ax_main: Axes, ax_cbar: Axes, df: pd.DataFrame, x_col: str, y_col: str
) -> None:
    _, label = get_sim_color_and_label(df)
    add_top_label(ax_main, label)
    hist_bins = count_hist_bins(df, y_col)
    hm_x = df[x_col].tolist()
    hm_y = [(i + 0.5) / hist_bins for i in range(hist_bins)]
    hm_z = generate_heatmap_matrix(df, y_col, hist_bins)
    norm = colors.PowerNorm(gamma=0.5, vmin=0, vmax=hist_bins)
    im = ax_main.pcolormesh(
        hm_x, hm_y, hm_z, alpha=0.5, norm=norm, cmap=CMAP, shading="nearest"
    )
    ax_main.set_xlim(hm_x[0], hm_x[-1])
    cbar = fig.colorbar(im, cax=ax_cbar, aspect=64)
    raw_y_label = COL_TEX_LABELS[y_col][1:-1]
    cbar.ax.set_ylabel(f"$p({raw_y_label})$")


def plot_side_heatmap(ax_side: Axes, df: pd.DataFrame, y_col: str) -> None:
    _, label = get_sim_color_and_label(df)
    add_top_label(ax_side, label)
    hist_bins = count_hist_bins(df, y_col)
    hm_x = [0.0, 1.0]
    hm_y = [i / hist_bins for i in range(hist_bins + 1)]
    hm_z = generate_heatmap_matrix(df, y_col, hist_bins)
    norm = colors.PowerNorm(gamma=0.5, vmin=0, vmax=hist_bins)
    ax_side.pcolormesh(hm_x, hm_y, hm_z, alpha=0.5, norm=norm, cmap=CMAP)


def plot_dist_phe_0_lims(ax: Axes, df: pd.DataFrame, job: SimJob) -> None:
    n_env = job.config["model"]["n_env"]
    n_phe = job.config["model"]["n_phe"]
    if n_env != 2 or n_phe != 2:
        return

    strat_phe_0_values = df["strat_phe_0"].tolist()

    for env in range(n_env):
        rates_birth = np.array(job.config["model"]["rates_birth"][env])
        rates_death = np.array(job.config["model"]["rates_death"][env])
        dist_phe_0_lim_values = []
        for strat_phe_0 in strat_phe_0_values:
            strat_phe_1 = 1.0 - strat_phe_0
            matrix = np.array([strat_phe_0 * rates_birth, strat_phe_1 * rates_birth])
            matrix[0][0] -= rates_death[0]
            matrix[1][1] -= rates_death[1]
            eigenvalues, eigenvectors = np.linalg.eig(matrix)
            max_index = np.argmax(eigenvalues)
            max_eigenvector = eigenvectors[:, max_index]
            dist_phe_0_lim_values.append(
                float(max_eigenvector[0] / np.sum(max_eigenvector))
            )

        ax.plot(
            strat_phe_0_values,
            dist_phe_0_lim_values,
            c=EXTRA_COLORS[env],
            label=f"sol. for $e={env}$",
            **LINE_STYLE,
        )


def strat_phe_0_filter(df: pd.DataFrame, job: SimJob) -> pd.DataFrame:
    return df[
        ((df["prob_mut"] == job.config["model"]["prob_mut"]) | (df["prob_mut"] == 0))
        & (df["n_agents"] == job.config["init"]["n_agents"])
    ]


def prob_mut_filter(df: pd.DataFrame, job: SimJob) -> pd.DataFrame:
    return df[
        (df["sim_type"] == SimType.RANDOM)
        & (df["n_agents"] == job.config["init"]["n_agents"])
    ]


def n_agents_filter(df: pd.DataFrame, job: SimJob) -> pd.DataFrame:
    return df[
        (df["sim_type"] == SimType.RANDOM)
        & (df["prob_mut"] == job.config["model"]["prob_mut"])
    ]


PARAM_FILTERS = {
    "strat_phe_0": strat_phe_0_filter,
    "prob_mut": prob_mut_filter,
    "n_agents": n_agents_filter,
}


def generate_param_plots(param: str, df: pd.DataFrame, job: SimJob) -> None:
    df_p = PARAM_FILTERS[param](df, job).sort_values(param)
    if len(df_p) < 2:
        return

    strat_phe_0 = param == "strat_phe_0"

    fig_1, ax_1 = create_standard_figure(param, "growth_rate")
    fig_2, ax_2 = create_standard_figure(param, "extinct_rate")
    fig_3, ax_3 = create_standard_figure("growth_rate", "extinct_rate")
    fig_4, axs_4 = create_heatmap_figure(param, "dist_n_agents", strat_phe_0)
    fig_5, axs_5 = create_heatmap_figure(param, "dist_strat_phe_0", strat_phe_0)
    fig_6, ax_6 = create_standard_figure(param, "avg_strat_phe_0")
    fig_7, ax_7 = create_standard_figure(param, "dist_phe_0")

    sim_types = df_p["sim_type"]
    for sim_type in sim_types.unique():
        df_s = df_p[sim_types == sim_type]

        def plot_with_uncertainty(ax: Axes, y_col: str, y_span_col: str | None):
            if strat_phe_0 and sim_type == SimType.RANDOM:
                if y_span_col is None:
                    plot_horizontal_bands(ax, df_s, (y_col, "mean"), (y_col, "sem"))
                else:
                    plot_horizontal_bands(
                        ax, df_s, (y_col, "mean"), (y_span_col, "mean")
                    )
            else:
                plot_errorbar(ax, df_s, param, y_col, False)
                if y_span_col is not None:
                    plot_errorband(ax, df_s, param, y_col, y_span_col)

        plot_with_uncertainty(ax_1, "growth_rate", None)
        plot_with_uncertainty(ax_2, "extinct_rate", None)

        plot_errorbar(ax_3, df_s, "growth_rate", "extinct_rate", True)

        if strat_phe_0:
            if sim_type == SimType.FIXED:
                plot_main_heatmap(
                    fig_4, axs_4[0], axs_4[2], df_s, param, "dist_n_agents"
                )
            elif sim_type == SimType.EVOL:
                plot_main_heatmap(
                    fig_5, axs_5[0], axs_5[2], df_s, param, "dist_strat_phe_0"
                )
            elif sim_type == SimType.RANDOM:
                plot_side_heatmap(axs_4[1], df_s, "dist_n_agents")
                plot_side_heatmap(axs_5[1], df_s, "dist_strat_phe_0")
        else:
            plot_main_heatmap(fig_4, axs_4[0], axs_4[1], df_s, param, "dist_n_agents")
            plot_main_heatmap(
                fig_5, axs_5[0], axs_5[1], df_s, param, "dist_strat_phe_0"
            )

        plot_with_uncertainty(ax_6, "avg_strat_phe_0", "std_dev_strat_phe")
        plot_with_uncertainty(ax_7, "dist_phe_0", None)

        if strat_phe_0 and sim_type == SimType.FIXED:
            min_extinct = df_s[param][df_s[("extinct_rate", "mean")].idxmin()]
            max_growth = df_s[param][df_s[("growth_rate", "mean")].idxmax()]
            for ax in [ax_1, ax_2]:
                ax.axvline(min_extinct, c=EXTRA_COLORS[0], **LINE_STYLE)
                ax.axvline(max_growth, c=EXTRA_COLORS[1], **LINE_STYLE)
            for ax in axs_5[:-1] + [ax_6]:
                ax.axhline(min_extinct, c=EXTRA_COLORS[0], **LINE_STYLE)
                ax.axhline(max_growth, c=EXTRA_COLORS[1], **LINE_STYLE)

            plot_dist_phe_0_lims(ax_7, df_s, job)

    if param == "prob_mut":
        df_s = df[df["sim_type"] == SimType.FIXED].sort_values("strat_phe_0")
        plot_errorbar(ax_3, df_s, "growth_rate", "extinct_rate", True)

    fig_dir = job.base_dir / "plots" / param
    fig_dir.mkdir(parents=True, exist_ok=True)

    if param in ["prob_mut", "n_agents"]:
        for ax in [ax_1, ax_2, axs_4[0], axs_5[0], ax_6, ax_7]:
            ax.set_xscale("log")
    for ax in [ax_2, ax_3]:
        ax.set_yscale("log")
    for ax in [ax_1, ax_2, ax_3, ax_6, ax_7]:
        ax.legend()

    fig_1.savefig(fig_dir / "growth_rate.pdf")
    fig_2.savefig(fig_dir / "extinct_rate.pdf")
    fig_3.savefig(fig_dir / "rates.pdf")
    fig_4.savefig(fig_dir / "dist_n_agents.pdf")
    fig_5.savefig(fig_dir / "dist_strat_phe_0.pdf")
    fig_6.savefig(fig_dir / "avg_strat_phe_0.pdf")
    fig_7.savefig(fig_dir / "dist_phe_0.pdf")


def plot_sim_jobs(sim_jobs: list[SimJob]) -> None:
    avg_analyses = collect_avg_analyses(sim_jobs)
    init_sim_job = sim_jobs[0]

    generate_param_plots("strat_phe_0", avg_analyses, init_sim_job)
    generate_param_plots("prob_mut", avg_analyses, init_sim_job)
    generate_param_plots("n_agents", avg_analyses, init_sim_job)

    print("plots made")
