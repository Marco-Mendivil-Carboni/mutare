import pandas as pd
import numpy as np
from scipy.optimize import curve_fit
from scipy.interpolate import make_splrep
from shutil import rmtree
from matplotlib.axes import Axes
from matplotlib.colors import LogNorm
from matplotlib.cm import ScalarMappable
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import cast

from ..exec import N_CORES, SimJob, print_process_msg
from ..analysis import SimType, collect_avg_analyses, collect_run_time_series

from .utils import (
    CMAP,
    SIM_COLORS,
    COL_TEX_LABELS,
    PLOT_STYLE,
    LINE_STYLE,
    create_standard_figure,
    create_colorbar_figure,
    plot_horizontal_bands,
    plot_errorbar,
    plot_errorband,
    count_hist_bins,
    plot_main_heatmap,
    plot_side_heatmap,
    plot_dist_phe_0_lims,
    plot_extinct_times,
    plot_time_series,
)


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


def make_param_plots(param: str, df: pd.DataFrame, job: SimJob) -> None:
    param_df = PARAM_FILTERS[param](df, job).sort_values(param)
    if len(param_df) < 2:
        return

    two_panels = param == "strat_phe_0_i"
    fig_1, ax_1 = create_standard_figure(param, "avg_growth_rate")
    fig_2, ax_2 = create_standard_figure(param, "extinct_rate")
    fig_3, ax_3 = create_standard_figure("avg_growth_rate", "extinct_rate")
    fig_4, axs_4 = create_colorbar_figure(param, "norm_n_agents", two_panels)
    fig_5, axs_5 = create_colorbar_figure(param, "avg_strat_phe_0", two_panels)
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
                    fig_5,
                    axs_5[0],
                    axs_5[2],
                    subgroup_df,
                    param,
                    "dist_avg_strat_phe_0",
                )
            elif sim_type == SimType.RANDOM:
                plot_side_heatmap(axs_4[1], subgroup_df, "dist_n_agents")
                plot_side_heatmap(axs_5[1], subgroup_df, "dist_avg_strat_phe_0")
        else:
            plot_main_heatmap(
                fig_4, axs_4[0], axs_4[1], subgroup_df, param, "dist_n_agents"
            )
            plot_main_heatmap(
                fig_5, axs_5[0], axs_5[1], subgroup_df, param, "dist_avg_strat_phe_0"
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
        hist_bins = count_hist_bins(df, "dist_avg_strat_phe_0")
        extinct_rate_spline = make_splrep(
            subgroup_df["strat_phe_0_i"], subgroup_df[("extinct_rate", "mean")]
        )
        for bin in range(hist_bins):
            exp_extinct_rates += param_df[
                (f"dist_avg_strat_phe_0_{bin}", "mean")
            ] * extinct_rate_spline((1 / 2 + bin) / hist_bins)

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
    fig_5.savefig(fig_dir / "dist_avg_strat_phe_0.pdf")
    fig_6.savefig(fig_dir / "avg_strat_phe_0.pdf")
    fig_7.savefig(fig_dir / "dist_phe_0.pdf")
    fig_8.savefig(fig_dir / "std_dev_growth_rate.pdf")

    print_process_msg(f"made '{param}' plots")


def make_time_series_plots(df: pd.DataFrame, job: SimJob) -> None:
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

    print_process_msg("made 'time_series' plots")


def make_scaling_plots(df: pd.DataFrame, job: SimJob) -> None:
    scaling_df = df[df["prob_mut"] == 0].sort_values("strat_phe_0_i")
    if scaling_df["n_agents_i"].nunique() < 2:
        return

    fig_1, axs_1 = create_colorbar_figure("strat_phe_0_i", "avg_growth_rate", False)
    fig_2, axs_2 = create_colorbar_figure("strat_phe_0_i", "extinct_rate", False)
    fig_3, axs_3 = create_colorbar_figure("strat_phe_0_i", "dist_phe_0", False)
    fig_4, axs_4 = create_colorbar_figure("strat_phe_0_i", "std_dev_growth_rate", False)

    fig_5, axs_5 = create_colorbar_figure("n_agents_i", "extinct_rate", False)
    fig_6, ax_6 = create_standard_figure("strat_phe_0_i", "ext_fit_alpha")
    fig_7, ax_7 = create_standard_figure("strat_phe_0_i", "ext_fit_A")
    fig_8, axs_8 = create_colorbar_figure(
        "avg_strat_phe_0", "dist_avg_strat_phe_0", False
    )

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
            {
                "strat_phe_0_i": strat_phe_0_i,
                "avg_growth_rate": subgroup_df[("avg_growth_rate", "mean")].max(),
                "alpha": popt[0],
                "alpha_err": perr[0],
                "A": popt[1],
                "A_err": perr[1],
            }
        )

    fit_df = pd.DataFrame(fit_results)
    smoothness = len(fit_df) - np.sqrt(4 * len(fit_df))
    strat_phe_0_i_values = fit_df["strat_phe_0_i"].to_numpy()
    avg_growth_rate_values = fit_df["avg_growth_rate"].to_numpy()
    alpha_values = fit_df["alpha"].to_numpy()
    alpha_err_values = fit_df["alpha_err"].to_numpy()
    A_values = fit_df["A"].to_numpy()
    A_err_values = fit_df["A_err"].to_numpy()

    color = SIM_COLORS[SimType.FIXED]
    ax_6.errorbar(
        strat_phe_0_i_values, alpha_values, alpha_err_values, c=color, **PLOT_STYLE
    )
    ax_7.errorbar(strat_phe_0_i_values, A_values, A_err_values, c=color, **PLOT_STYLE)

    avg_growth_rate_spline = make_splrep(strat_phe_0_i_values, avg_growth_rate_values)
    alpha_spline = make_splrep(
        strat_phe_0_i_values, alpha_values, w=1.0 / alpha_err_values, s=smoothness
    )
    A_spline = make_splrep(
        strat_phe_0_i_values, A_values, w=1.0 / A_err_values, s=smoothness
    )
    avg_strat_phe_0 = np.linspace(0.0, 1.0, 64)

    axs_1[0].errorbar(
        avg_strat_phe_0, avg_growth_rate_spline(avg_strat_phe_0), ls=":", **LINE_STYLE
    )
    ax_6.errorbar(avg_strat_phe_0, alpha_spline(avg_strat_phe_0), ls=":", **LINE_STYLE)
    ax_7.errorbar(avg_strat_phe_0, A_spline(avg_strat_phe_0), ls=":", **LINE_STYLE)

    for ax in [axs_5[0]]:
        ax.set_xscale("log")
    for ax in [axs_2[0], axs_5[0]]:
        ax.set_yscale("log")

    axs_2[0].set_ylim(bottom=10**-8.5)
    axs_5[0].set_ylim(bottom=10**-8.5)

    sm = ScalarMappable(cmap=CMAP)
    cbar = fig_5.colorbar(sm, cax=axs_5[1], aspect=64)
    cbar.ax.set_ylabel(COL_TEX_LABELS["strat_phe_0_i"])

    norm = LogNorm(vmin=1e2 / 2.0, vmax=1e3 * 2.0)
    for n_agents_i in np.logspace(start=2, stop=3, num=4):
        color = CMAP(norm(n_agents_i))
        log_dist_avg_strat_phe_0 = (
            n_agents_i * avg_growth_rate_spline(avg_strat_phe_0)
        ) - np.log(
            (A_spline(avg_strat_phe_0) * n_agents_i) ** -alpha_spline(avg_strat_phe_0)
            + 1e-3 * avg_growth_rate_spline(avg_strat_phe_0).mean()
        )
        log_dist_avg_strat_phe_0 -= np.max(log_dist_avg_strat_phe_0)
        dist_avg_strat_phe_0 = np.exp(log_dist_avg_strat_phe_0)
        dist_avg_strat_phe_0 /= np.sum(dist_avg_strat_phe_0) / len(avg_strat_phe_0)
        axs_8[0].plot(avg_strat_phe_0, dist_avg_strat_phe_0, c=color, ls="--")

    sm = ScalarMappable(norm=norm, cmap=CMAP)
    cbar = fig_5.colorbar(sm, cax=axs_8[1], aspect=64)
    cbar.ax.set_ylabel(COL_TEX_LABELS["n_agents_i"])

    fig_dir = job.base_dir / "plots" / "scaling"
    fig_dir.mkdir(parents=True, exist_ok=True)

    fig_1.savefig(fig_dir / "avg_growth_rate.pdf")
    fig_2.savefig(fig_dir / "extinct_rate.pdf")
    fig_3.savefig(fig_dir / "dist_phe_0.pdf")
    fig_4.savefig(fig_dir / "std_dev_growth_rate.pdf")
    fig_5.savefig(fig_dir / "extinct_rate_scaling.pdf")
    fig_6.savefig(fig_dir / "ext_fit_alpha.pdf")
    fig_7.savefig(fig_dir / "ext_fit_A.pdf")
    fig_8.savefig(fig_dir / "dist_avg_strat_phe_0.pdf")

    print_process_msg("made 'scaling' plots")


def plot_sim_jobs(sim_jobs: list[SimJob]) -> None:
    avg_analyses = collect_avg_analyses(sim_jobs)
    init_sim_job = sim_jobs[0]
    run_time_series = collect_run_time_series(init_sim_job, 0)

    rmtree(init_sim_job.base_dir / "plots", ignore_errors=True)

    with ProcessPoolExecutor(max_workers=N_CORES) as pool:
        futures = [
            pool.submit(make_param_plots, "strat_phe_0_i", avg_analyses, init_sim_job),
            pool.submit(make_param_plots, "prob_mut", avg_analyses, init_sim_job),
            pool.submit(make_param_plots, "n_agents_i", avg_analyses, init_sim_job),
            pool.submit(make_time_series_plots, run_time_series, init_sim_job),
            pool.submit(make_scaling_plots, avg_analyses, init_sim_job),
        ]

        for future in as_completed(futures):
            future.result()
