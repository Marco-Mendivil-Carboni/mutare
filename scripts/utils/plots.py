import pandas as pd
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

CMAP = colors.LinearSegmentedColormap.from_list("custom", ["white", COLORS[1]])

SIM_COLORS: dict[SimType, str] = {
    SimType.FIXED: COLORS[1],
    SimType.EVOL: COLORS[7],
    SimType.RANDOM: COLORS[11],
}
SIM_LABELS: dict[SimType, str] = {
    SimType.FIXED: "fixed strat",
    SimType.EVOL: "evolutive",
    SimType.RANDOM: "random init",
}

COL_TEX_LABELS: dict[str, str] = {
    "strat_phe_0": "$s(0)_i$",
    "prob_mut": "$p_{\\text{mut}}$",
    "n_agents": "$N_0$",
    "extinct_rate": "$r_e$",
    "growth_rate": "$\\langle\\mu\\rangle$",
    "avg_strat_phe_0": "$\\langle s(0)\\rangle$",
}


def create_standard_figure(x_col: str, y_col: str) -> tuple[Figure, Axes]:
    fig = Figure(figsize=FIGSIZE)
    ax = fig.add_subplot()
    ax.set_xlabel(COL_TEX_LABELS[x_col])
    ax.set_ylabel(COL_TEX_LABELS[y_col])
    return fig, ax


def create_heatmap_figure(x_col: str, two_panels: bool) -> tuple[Figure, list[Axes]]:
    fig = Figure(figsize=FIGSIZE)

    if two_panels:
        gs = gridspec.GridSpec(1, 3, figure=fig, width_ratios=[64, 8, 1], wspace=0)
        ax_main = fig.add_subplot(gs[0, 0])
        ax_side = fig.add_subplot(gs[0, 1])
        ax_cbar = fig.add_subplot(gs[0, 2])
        ax_main.set_xlabel(COL_TEX_LABELS[x_col])
        ax_main.set_ylabel("$s(0)$")
        ax_side.set_xticks([])
        ax_side.set_yticks([])

        return fig, [ax_main, ax_side, ax_cbar]

    else:
        gs = gridspec.GridSpec(1, 2, figure=fig, width_ratios=[64, 1], wspace=0)
        ax_main = fig.add_subplot(gs[0, 0])
        ax_cbar = fig.add_subplot(gs[0, 1])
        ax_main.set_xlabel(COL_TEX_LABELS[x_col])
        ax_main.set_ylabel("$s(0)$")

        return fig, [ax_main, ax_cbar]


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


def count_hist_bins(df: pd.DataFrame) -> int:
    hist_bins = 0
    while (f"dist_strat_phe_0_{hist_bins}", "mean") in df.columns:
        hist_bins += 1
    return hist_bins


def generate_heatmap_matrix(df: pd.DataFrame, hist_bins: int) -> list[list[float]]:
    hm_z = []
    for bin in range(hist_bins):
        hm_z.append((hist_bins * df[(f"dist_strat_phe_0_{bin}", "mean")]).tolist())
    return hm_z


def plot_main_heatmap(
    fig: Figure, ax_main: Axes, ax_cbar: Axes, df: pd.DataFrame, x_col: str
) -> None:
    hist_bins = count_hist_bins(df)
    hm_x = df[x_col].tolist()
    hm_y = [(i + 0.5) / hist_bins for i in range(hist_bins)]
    hm_z = generate_heatmap_matrix(df, hist_bins)
    im = ax_main.pcolormesh(
        hm_x, hm_y, hm_z, cmap=CMAP, vmin=0, vmax=hist_bins, shading="nearest"
    )
    ax_main.set_xlim(hm_x[0], hm_x[-1])
    cbar = fig.colorbar(im, cax=ax_cbar, aspect=64)
    cbar.ax.set_ylabel("$p(s(0))$")


def plot_side_heatmap(ax_side: Axes, df: pd.DataFrame) -> None:
    hist_bins = count_hist_bins(df)
    hm_x = [0.0, 1.0]
    hm_y = [i / hist_bins for i in range(hist_bins + 1)]
    hm_z = generate_heatmap_matrix(df, hist_bins)
    ax_side.pcolormesh(hm_x, hm_y, hm_z, cmap=CMAP, vmin=0, vmax=hist_bins)


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
    df_p = PARAM_FILTERS[param](df, job)
    if len(df_p) < 2:
        return
    df_p = df_p.sort_values(param)

    fig_1, ax_1 = create_standard_figure(param, "extinct_rate")
    fig_2, ax_2 = create_standard_figure(param, "growth_rate")
    fig_3, ax_3 = create_standard_figure(param, "avg_strat_phe_0")

    if param == "strat_phe_0":
        fig_4, axs_4 = create_heatmap_figure(param, True)
        axs_4[1].set_xlabel("random init")
    else:
        fig_4, axs_4 = create_heatmap_figure(param, False)

    fig_5, ax_5 = create_standard_figure("growth_rate", "extinct_rate")

    if param == "strat_phe_0":
        min_extinct = df_p[param][df_p[("extinct_rate", "mean")].idxmin()]
        max_growth = df_p[param][df_p[("growth_rate", "mean")].idxmax()]
        for ax in [ax_1, ax_2]:
            ax.axvline(min_extinct, color="gray", ls=":")
            ax.axvline(max_growth, color="gray", ls="-.")
        for ax in [ax_3] + axs_4[:-1]:
            ax.axhline(min_extinct, color="gray", ls=":")
            ax.axhline(max_growth, color="gray", ls="-.")

    sim_types = df_p["sim_type"]
    for sim_type in sim_types.unique():
        df_s = df_p[sim_types == sim_type]

        def plot_with_uncertainty(ax: Axes, y_col: str, y_span_col: str | None):
            if param == "strat_phe_0" and sim_type == SimType.RANDOM:
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

        plot_with_uncertainty(ax_1, "extinct_rate", None)
        plot_with_uncertainty(ax_2, "growth_rate", None)
        plot_with_uncertainty(ax_3, "avg_strat_phe_0", "std_dev_strat_phe")

        if param == "strat_phe_0":
            if sim_type == SimType.EVOL:
                plot_main_heatmap(fig_4, axs_4[0], axs_4[2], df_s, param)
            elif sim_type == SimType.RANDOM:
                plot_side_heatmap(axs_4[1], df_s)
        else:
            plot_main_heatmap(fig_4, axs_4[0], axs_4[1], df_s, param)

        plot_errorbar(ax_5, df_s, "growth_rate", "extinct_rate", True)

    if param == "prob_mut":
        df_s = df[df["sim_type"] == SimType.FIXED]
        df_s.sort_values("strat_phe_0")
        plot_errorbar(ax_5, df_s, "growth_rate", "extinct_rate", True)

    fig_dir = job.base_dir / "plots" / param
    fig_dir.mkdir(parents=True, exist_ok=True)

    if param in ["prob_mut", "n_agents"]:
        for ax in [ax_1, ax_2, ax_3, axs_4[0]]:
            ax.set_xscale("log")
    for ax in [ax_1, ax_5]:
        ax.set_yscale("log")
    for ax in [ax_1, ax_2, ax_3, ax_5]:
        ax.legend()

    fig_1.savefig(fig_dir / "extinct_rate.pdf")
    fig_2.savefig(fig_dir / "growth_rate.pdf")
    fig_3.savefig(fig_dir / "avg_strat_phe_0.pdf")
    fig_4.savefig(fig_dir / "dist_strat_phe_0.pdf")
    fig_5.savefig(fig_dir / "rates.pdf")


def plot_sim_jobs(sim_jobs: list[SimJob]) -> None:
    avg_analyses = collect_avg_analyses(sim_jobs)
    init_sim_job = sim_jobs[0]

    generate_param_plots("strat_phe_0", avg_analyses, init_sim_job)
    generate_param_plots("prob_mut", avg_analyses, init_sim_job)
    generate_param_plots("n_agents", avg_analyses, init_sim_job)

    print("plots made")
