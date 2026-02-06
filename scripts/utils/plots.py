import pandas as pd
import numpy as np
from scipy.optimize import curve_fit
from shutil import rmtree
import matplotlib as mpl
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.gridspec import GridSpec
from matplotlib.colors import PowerNorm, LogNorm
from matplotlib.cm import ScalarMappable
from typing import Any, cast

from .exec import SimJob, print_process_msg
from .analysis import SimType, collect_avg_analyses, collect_run_time_series

mpl.use("pdf")

mpl.rcParams["text.usetex"] = True
mpl.rcParams["text.latex.preamble"] = "\\usepackage{lmodern}\\usepackage{mathtools}"
mpl.rcParams["font.family"] = "lmodern"
mpl.rcParams["font.size"] = 10
mpl.rcParams["figure.dpi"] = 1200
mpl.rcParams["figure.constrained_layout.use"] = True

CM = 1 / 2.54
FIGSIZE = (8.0 * CM, 5.0 * CM)

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
    "dist_n_agents": "$N/N_{\\text{ini}}$",
    "avg_growth_rate": "$\\langle\\mu\\rangle$",
    "extinct_rate": "$r_{\\text{ext}}$",
    "avg_strat_phe_0": "$\\langle s(A)\\rangle$",
    "dist_strat_phe_0": "$s(A)$",
    "dist_phe_0": "$p(A)$",
    "std_dev_growth_rate": "$\\sigma_{\\mu}$",
    "alpha": "$\\alpha$",
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
    df: pd.DataFrame, y_col: str, hist_bins: int
) -> list[list[float]]:
    hm_z = []
    for bin in range(hist_bins):
        hm_z.append((hist_bins * df[(f"{y_col}_{bin}", "mean")]).tolist())
    return hm_z


def plot_main_heatmap(
    fig: Figure, ax_main: Axes, ax_bar: Axes, df: pd.DataFrame, x_col: str, y_col: str
) -> None:
    _, label = get_sim_color_and_label(df)
    add_top_label(ax_main, label)
    hist_bins = count_hist_bins(df, y_col)
    hm_x = df[x_col].tolist()
    hm_y = [(i + 0.5) / hist_bins for i in range(hist_bins)]
    hm_z = generate_heatmap_matrix(df, y_col, hist_bins)
    norm = PowerNorm(gamma=0.5, vmin=0, vmax=hist_bins)
    im = ax_main.pcolormesh(hm_x, hm_y, hm_z, norm=norm, cmap=CMAP, shading="nearest")
    ax_main.set_xlim(hm_x[0], hm_x[-1])
    cbar = fig.colorbar(im, cax=ax_bar, aspect=64)
    raw_y_label = COL_TEX_LABELS[y_col][1:-1]
    cbar.ax.set_ylabel(f"$p({raw_y_label})$")


def plot_side_heatmap(ax_side: Axes, df: pd.DataFrame, y_col: str) -> None:
    _, label = get_sim_color_and_label(df)
    add_top_label(ax_side, label)
    hist_bins = count_hist_bins(df, y_col)
    hm_x = [0.0, 1.0]
    hm_y = [i / hist_bins for i in range(hist_bins + 1)]
    hm_z = generate_heatmap_matrix(df, y_col, hist_bins)
    norm = PowerNorm(gamma=0.5, vmin=0, vmax=hist_bins)
    ax_side.pcolormesh(hm_x, hm_y, hm_z, norm=norm, cmap=CMAP)


def plot_dist_phe_0_lims(ax: Axes, df: pd.DataFrame, job: SimJob) -> None:
    n_env = job.config["model"]["n_env"]
    n_phe = job.config["model"]["n_phe"]
    if n_env != 2 or n_phe != 2:
        return

    strat_phe_0_i_values = df["strat_phe_0_i"].tolist()

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

        ax.plot(strat_phe_0_i_values, dist_phe_0_lim_values, ls="-.", **LINE_STYLE)


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


PARAM_FILTERS = {
    "strat_phe_0_i": strat_phe_0_i_filter,
    "prob_mut": prob_mut_filter,
    "n_agents_i": n_agents_i_filter,
}


def generate_param_plots(param: str, df: pd.DataFrame, job: SimJob) -> None:
    param_df = PARAM_FILTERS[param](df, job).sort_values(param)
    if len(param_df) < 2:
        return

    two_panels = param == "strat_phe_0_i"
    fig_1, ax_1 = create_standard_figure(param, "avg_growth_rate")
    fig_2, ax_2 = create_standard_figure(param, "extinct_rate")
    fig_3, ax_3 = create_standard_figure("avg_growth_rate", "extinct_rate")
    fig_4, axs_4 = create_colorbar_figure(param, "dist_n_agents", two_panels)
    fig_5, axs_5 = create_colorbar_figure(param, "dist_strat_phe_0", two_panels)
    fig_6, ax_6 = create_standard_figure(param, "avg_strat_phe_0")
    fig_7, ax_7 = create_standard_figure(param, "dist_phe_0")
    fig_8, ax_8 = create_standard_figure(param, "std_dev_growth_rate")

    if param in ["prob_mut", "n_agents_i"]:
        for ax in [axs_4[0], axs_5[0]]:
            ax.set_xscale("log")

    for sim_type, subgroup_df in param_df.groupby("sim_type"):

        def plot_mean_and_uncertainty(
            ax: Axes, y_col: str, y_span_col: str | None
        ) -> None:
            if param == "strat_phe_0_i" and sim_type == SimType.RANDOM:
                if y_span_col is None:
                    plot_horizontal_bands(
                        ax, subgroup_df, (y_col, "mean"), (y_col, "sem")
                    )
                else:
                    plot_horizontal_bands(
                        ax, subgroup_df, (y_col, "mean"), (y_span_col, "mean")
                    )
            else:
                plot_errorbar(ax, subgroup_df, param, y_col, False)
                if y_span_col is not None:
                    plot_errorband(ax, subgroup_df, param, y_col, y_span_col)

        plot_mean_and_uncertainty(ax_1, "avg_growth_rate", None)
        plot_mean_and_uncertainty(ax_2, "extinct_rate", None)

        plot_errorbar(ax_3, subgroup_df, "avg_growth_rate", "extinct_rate", True)

        if param == "strat_phe_0_i":
            if sim_type == SimType.FIXED:
                plot_main_heatmap(
                    fig_4, axs_4[0], axs_4[2], subgroup_df, param, "dist_n_agents"
                )
            elif sim_type == SimType.EVOL:
                plot_main_heatmap(
                    fig_5, axs_5[0], axs_5[2], subgroup_df, param, "dist_strat_phe_0"
                )
            elif sim_type == SimType.RANDOM:
                plot_side_heatmap(axs_4[1], subgroup_df, "dist_n_agents")
                plot_side_heatmap(axs_5[1], subgroup_df, "dist_strat_phe_0")
        else:
            plot_main_heatmap(
                fig_4, axs_4[0], axs_4[1], subgroup_df, param, "dist_n_agents"
            )
            plot_main_heatmap(
                fig_5, axs_5[0], axs_5[1], subgroup_df, param, "dist_strat_phe_0"
            )

        plot_mean_and_uncertainty(ax_6, "avg_strat_phe_0", "std_dev_strat_phe")
        plot_mean_and_uncertainty(ax_7, "dist_phe_0", None)
        plot_mean_and_uncertainty(ax_8, "std_dev_growth_rate", None)

        if param == "strat_phe_0_i" and sim_type == SimType.FIXED:
            min_extinct = subgroup_df[param][
                subgroup_df[("extinct_rate", "mean")].idxmin()
            ]
            max_avg_growth = subgroup_df[param][
                subgroup_df[("avg_growth_rate", "mean")].idxmax()
            ]
            for ax in [ax_1, ax_2, ax_8]:
                ax.axvline(min_extinct, ls=":", **LINE_STYLE)
                ax.axvline(max_avg_growth, ls="--", **LINE_STYLE)
            for ax in axs_5[:-1] + [ax_6]:
                ax.axhline(min_extinct, ls=":", **LINE_STYLE)
                ax.axhline(max_avg_growth, ls="--", **LINE_STYLE)

            plot_dist_phe_0_lims(ax_7, subgroup_df, job)

    if param == "prob_mut":
        subgroup_df = df[
            (df["sim_type"] == SimType.FIXED)
            & (df["n_agents_i"] == job.config["init"]["n_agents"])
        ].sort_values("strat_phe_0_i")

        exp_extinct_rates = np.zeros(len(param_df))
        hist_bins = count_hist_bins(df, "dist_strat_phe_0")
        for bin in range(hist_bins - 1):
            exp_extinct_rates += (
                0.5
                * (
                    param_df[(f"dist_strat_phe_0_{bin + 1}", "mean")]
                    + param_df[(f"dist_strat_phe_0_{bin}", "mean")]
                )
                * subgroup_df.iloc[bin][("extinct_rate", "mean")]
            )
        ax_2.plot(param_df["prob_mut"], exp_extinct_rates, ls="-.", **LINE_STYLE)

        plot_errorbar(ax_3, subgroup_df, "avg_growth_rate", "extinct_rate", True)

    if param in ["prob_mut", "n_agents_i"]:
        for ax in [ax_1, ax_2, ax_6, ax_7, ax_8]:
            ax.set_xscale("log")
    for ax in [ax_2, ax_3]:
        ax.set_yscale("log")

    for ax in [ax_1, ax_2, ax_3, ax_6, ax_7, ax_8]:
        ax.legend()

    fig_dir = job.base_dir / "plots" / param
    fig_dir.mkdir(parents=True, exist_ok=True)

    fig_1.savefig(fig_dir / "avg_growth_rate.pdf")
    fig_2.savefig(fig_dir / "extinct_rate.pdf")
    fig_3.savefig(fig_dir / "rates.pdf")
    fig_4.savefig(fig_dir / "dist_n_agents.pdf")
    fig_5.savefig(fig_dir / "dist_strat_phe_0.pdf")
    fig_6.savefig(fig_dir / "avg_strat_phe_0.pdf")
    fig_7.savefig(fig_dir / "dist_phe_0.pdf")
    fig_8.savefig(fig_dir / "std_dev_growth_rate.pdf")


def generate_time_series_plots(df: pd.DataFrame, job: SimJob) -> None:
    fig_dir = job.base_dir / "plots" / "time_series"
    fig_dir.mkdir(parents=True, exist_ok=True)

    for y_col in ["n_agents", "n_extinct", "avg_strat_phe_0", "dist_phe_0"]:
        fig, ax = create_standard_figure("time", y_col)
        y_span_col = "std_dev_strat_phe" if y_col == "avg_strat_phe_0" else None
        plot_extinct_times(ax, df)
        plot_time_series(ax, df, y_col, y_span_col)
        ax.margins(0.0)
        ax.legend()
        fig.savefig(fig_dir / f"{y_col}.pdf")


def generate_scaling_plots(df: pd.DataFrame, job: SimJob) -> None:
    scaling_df = df[df["prob_mut"] == 0].sort_values("strat_phe_0_i")
    if scaling_df["n_agents_i"].nunique() < 2:
        return

    fig_1, axs_1 = create_colorbar_figure("strat_phe_0_i", "avg_growth_rate", False)
    fig_2, axs_2 = create_colorbar_figure("strat_phe_0_i", "extinct_rate", False)
    fig_3, axs_3 = create_colorbar_figure("strat_phe_0_i", "dist_phe_0", False)
    fig_4, axs_4 = create_colorbar_figure("strat_phe_0_i", "std_dev_growth_rate", False)

    fig_5, axs_5 = create_colorbar_figure("n_agents_i", "extinct_rate", False)
    fig_6, ax_6 = create_standard_figure("strat_phe_0_i", "alpha")

    norm = LogNorm(
        vmin=scaling_df["n_agents_i"].min() / 2.0,
        vmax=scaling_df["n_agents_i"].max() * 2.0,
    )

    for n_agents_i, subgroup_df in scaling_df.groupby("n_agents_i"):

        def plot_mean_and_uncertainty(ax: Axes, y_col: str) -> None:
            color = CMAP(norm(cast(float, n_agents_i)))
            x = subgroup_df["strat_phe_0_i"]
            y = subgroup_df[(y_col, "mean")]
            yerr = subgroup_df[(y_col, "sem")]
            ax.errorbar(x, y, yerr, None, c=color, **PLOT_STYLE)

        plot_mean_and_uncertainty(axs_1[0], "avg_growth_rate")
        plot_mean_and_uncertainty(axs_2[0], "extinct_rate")
        plot_mean_and_uncertainty(axs_3[0], "dist_phe_0")
        plot_mean_and_uncertainty(axs_4[0], "std_dev_growth_rate")

    for ax in [axs_2[0]]:
        ax.set_yscale("log")

    sm = ScalarMappable(norm=norm, cmap=CMAP)
    for fig, axs in [(fig_1, axs_1), (fig_2, axs_2), (fig_3, axs_3), (fig_4, axs_4)]:
        cbar = fig.colorbar(sm, cax=axs[1], aspect=64)
        cbar.ax.set_ylabel(COL_TEX_LABELS["n_agents_i"])

    scaling_df = scaling_df.sort_values("n_agents_i")

    def power_law(x: float | pd.Series, alpha: float, A: float) -> float | pd.Series:
        return (A * x) ** (-alpha)

    fit_results = []
    for strat_phe_0_i, subgroup_df in scaling_df.groupby("strat_phe_0_i"):
        color = CMAP(cast(float, strat_phe_0_i))
        x = subgroup_df["n_agents_i"]
        y = subgroup_df[("extinct_rate", "mean")]
        yerr = subgroup_df[("extinct_rate", "sem")]
        axs_5[0].errorbar(x, y, yerr, None, c=color, **PLOT_STYLE)

        x, y, yerr = x[y != 0], y[y != 0], yerr[y != 0]
        popt, pcov = curve_fit(power_law, x, y, p0=(2.0, 0.5), sigma=yerr)
        perr = np.sqrt(np.diag(pcov))
        axs_5[0].errorbar(x, power_law(x, *popt), ls=":", **LINE_STYLE)
        fit_results.append(
            {"strat_phe_0_i": strat_phe_0_i, "alpha": popt[0], "alpha_err": perr[0]}
        )

    fit_df = pd.DataFrame(fit_results)
    ax_6.errorbar(
        fit_df["strat_phe_0_i"],
        fit_df["alpha"],
        fit_df["alpha_err"],
        c=COLORS["red"],
        **PLOT_STYLE,
    )

    axs_5[0].set_xscale("log")
    axs_5[0].set_yscale("log")
    axs_5[0].set_ylim(bottom=1e-8)

    sm = ScalarMappable(cmap=CMAP)
    cbar = fig_5.colorbar(sm, cax=axs_5[1], aspect=64)
    cbar.ax.set_ylabel(COL_TEX_LABELS["strat_phe_0_i"])

    fig_dir = job.base_dir / "plots" / "scaling"
    fig_dir.mkdir(parents=True, exist_ok=True)

    fig_1.savefig(fig_dir / "avg_growth_rate.pdf")
    fig_2.savefig(fig_dir / "extinct_rate.pdf")
    fig_3.savefig(fig_dir / "dist_phe_0.pdf")
    fig_4.savefig(fig_dir / "std_dev_growth_rate.pdf")
    fig_5.savefig(fig_dir / "extinct_rate_scaling.pdf")
    fig_6.savefig(fig_dir / "alpha.pdf")


def plot_sim_jobs(sim_jobs: list[SimJob]) -> None:
    avg_analyses = collect_avg_analyses(sim_jobs)
    init_sim_job = sim_jobs[0]
    run_time_series = collect_run_time_series(init_sim_job, 0)

    rmtree(init_sim_job.base_dir / "plots", ignore_errors=True)

    generate_param_plots("strat_phe_0_i", avg_analyses, init_sim_job)
    generate_param_plots("prob_mut", avg_analyses, init_sim_job)
    generate_param_plots("n_agents_i", avg_analyses, init_sim_job)

    generate_time_series_plots(run_time_series, init_sim_job)

    generate_scaling_plots(avg_analyses, init_sim_job)

    print_process_msg("finished plots")
