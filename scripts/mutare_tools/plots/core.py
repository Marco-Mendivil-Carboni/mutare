import pandas as pd
import numpy as np
from scipy.interpolate import make_splrep, LSQBivariateSpline
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
    PLOT_STYLE,
    LINE_STYLE,
    FILTERS,
    create_standard_figure,
    create_colorbar_figure,
    plot_horizontal_bands,
    plot_errorbar,
    plot_errorband,
    set_heatmap_colorbar,
    plot_main_heatmap,
    plot_side_heatmap,
    get_optimal_strat_phe_0,
    plot_dist_phe_0_lims,
    plot_expected_values,
    plot_extinct_times,
    plot_time_series,
    get_dist_avg_strat_phe_0,
    plot_avg_strat_phe_0,
)


def make_param_plots(param: str, df: pd.DataFrame, job: SimJob) -> None:
    param_df = FILTERS[param](df, job).sort_values(param)
    if len(param_df) < 2:
        return

    two_panels = param == "strat_phe_0_i"
    fig_0, ax_0 = create_standard_figure(param, "avg_growth_rate")
    fig_1, ax_1 = create_standard_figure(param, "extinct_rate")
    fig_2, ax_2 = create_standard_figure("avg_growth_rate", "extinct_rate")
    fig_3, axs_3 = create_colorbar_figure(param, "norm_n_agents", two_panels)
    fig_4, axs_4 = create_colorbar_figure(param, "avg_strat_phe_0", two_panels)
    fig_5, ax_5 = create_standard_figure(param, "avg_strat_phe_0")
    fig_6, ax_6 = create_standard_figure(param, "dist_phe_0")
    fig_7, ax_7 = create_standard_figure(param, "std_dev_growth_rate")
    fig_8, ax_8 = create_standard_figure(param, "avg_birth_rate")
    fig_9, ax_9 = create_standard_figure("avg_growth_rate", "std_dev_growth_rate")

    if param in ["prob_mut", "n_agents_i"]:
        for ax in [axs_3[0], axs_4[0]]:
            ax.set_xscale("log")

    for sim_type, group_df in param_df.groupby("sim_type"):

        def plot_mean_and_uncertainty(
            ax: Axes, y_col: str, y_span_col: str | None
        ) -> None:
            if param == "strat_phe_0_i" and sim_type == SimType.RANDOM:
                if y_span_col is None:
                    plot_horizontal_bands(ax, group_df, (y_col, "mean"), (y_col, "sem"))
                else:
                    plot_horizontal_bands(
                        ax, group_df, (y_col, "mean"), (y_span_col, "mean")
                    )
            else:
                plot_errorbar(ax, group_df, param, y_col, False)
                if y_span_col is not None:
                    plot_errorband(ax, group_df, param, y_col, y_span_col)

        plot_mean_and_uncertainty(ax_0, "avg_growth_rate", None)
        plot_mean_and_uncertainty(ax_1, "extinct_rate", None)

        plot_errorbar(ax_2, group_df, "avg_growth_rate", "extinct_rate", True)

        if param == "strat_phe_0_i":
            if sim_type == SimType.FIXED:
                plot_main_heatmap(
                    fig_3, axs_3[0], axs_3[2], group_df, param, "dist_n_agents"
                )
            elif sim_type == SimType.EVOL:
                plot_main_heatmap(
                    fig_4, axs_4[0], axs_4[2], group_df, param, "dist_avg_strat_phe_0"
                )
            elif sim_type == SimType.RANDOM:
                plot_side_heatmap(axs_3[1], group_df, "dist_n_agents")
                plot_side_heatmap(axs_4[1], group_df, "dist_avg_strat_phe_0")
        else:
            plot_main_heatmap(
                fig_3, axs_3[0], axs_3[1], group_df, param, "dist_n_agents"
            )
            plot_main_heatmap(
                fig_4, axs_4[0], axs_4[1], group_df, param, "dist_avg_strat_phe_0"
            )

        plot_mean_and_uncertainty(ax_5, "avg_strat_phe_0", "std_dev_strat_phe")
        plot_mean_and_uncertainty(ax_6, "dist_phe_0", None)
        plot_mean_and_uncertainty(ax_7, "std_dev_growth_rate", None)
        plot_mean_and_uncertainty(ax_8, "avg_birth_rate", None)

        plot_errorbar(ax_9, group_df, "avg_growth_rate", "std_dev_growth_rate", True)

    if param == "strat_phe_0_i":
        plot_dist_phe_0_lims(ax_6, param_df, job)

    if param == "prob_mut":
        fixed_i_df = FILTERS["fixed_i"](df, job).sort_values("strat_phe_0_i")
        plot_errorbar(ax_2, fixed_i_df, "avg_growth_rate", "extinct_rate", True)
        plot_errorbar(ax_9, fixed_i_df, "avg_growth_rate", "std_dev_growth_rate", True)
        plot_expected_values(ax_0, df, job, param, "avg_growth_rate")
        plot_expected_values(ax_1, df, job, param, "extinct_rate")

    max_avg_growth = get_optimal_strat_phe_0(df, job, "avg_growth_rate", "max")
    min_extinct = get_optimal_strat_phe_0(df, job, "extinct_rate", "min")
    if param == "strat_phe_0_i":
        for ax in [ax_0, ax_1, ax_7]:
            ax.axvline(max_avg_growth, ls="--", **LINE_STYLE)
            ax.axvline(min_extinct, ls=":", **LINE_STYLE)
    for ax in axs_4[:-1] + [ax_5]:
        ax.axhline(max_avg_growth, ls="--", **LINE_STYLE)
        ax.axhline(min_extinct, ls=":", **LINE_STYLE)

    if param in ["prob_mut", "n_agents_i"]:
        for ax in [ax_0, ax_1, ax_5, ax_6, ax_7, ax_8]:
            ax.set_xscale("log")
    for ax in [ax_1, ax_2]:
        ax.set_yscale("log")

    for ax in [ax_0, ax_1, ax_2, ax_5, ax_6, ax_7, ax_8, ax_9]:
        ax.legend()

    fig_dir = job.base_dir / "plots" / param
    fig_dir.mkdir(parents=True, exist_ok=True)

    fig_0.savefig(fig_dir / "avg_growth_rate.pdf")
    fig_1.savefig(fig_dir / "extinct_rate.pdf")
    fig_2.savefig(fig_dir / "rates.pdf")
    fig_3.savefig(fig_dir / "dist_n_agents.pdf")
    fig_4.savefig(fig_dir / "dist_avg_strat_phe_0.pdf")
    fig_5.savefig(fig_dir / "avg_strat_phe_0.pdf")
    fig_6.savefig(fig_dir / "dist_phe_0.pdf")
    fig_7.savefig(fig_dir / "std_dev_growth_rate.pdf")
    fig_8.savefig(fig_dir / "avg_birth_rate.pdf")
    fig_9.savefig(fig_dir / "growth_rates.pdf")

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


def make_fixed_plots(df: pd.DataFrame, job: SimJob) -> None:
    fixed_df = FILTERS["fixed"](df, job).sort_values("strat_phe_0_i")
    if fixed_df["n_agents_i"].nunique() < 2:
        return

    fig_0, axs_0 = create_colorbar_figure("strat_phe_0_i", "avg_growth_rate", False)
    fig_1, axs_1 = create_colorbar_figure("strat_phe_0_i", "extinct_rate", False)
    fig_2, axs_2 = create_colorbar_figure("strat_phe_0_i", "dist_phe_0", False)
    fig_3, axs_3 = create_colorbar_figure("strat_phe_0_i", "std_dev_growth_rate", False)
    fig_4, axs_4 = create_colorbar_figure("strat_phe_0_i", "avg_birth_rate", False)

    fig_5, axs_5 = create_colorbar_figure("n_agents_i", "extinct_rate", False)

    fig_6, axs_6 = create_colorbar_figure(
        "avg_strat_phe_0", "dist_avg_strat_phe_0", False
    )
    fig_7, axs_7 = create_colorbar_figure(
        "avg_strat_phe_0", "dist_avg_strat_phe_0", False
    )

    fig_8, axs_8 = create_colorbar_figure("n_agents_i", "prob_mut", False)
    fig_9, axs_9 = create_colorbar_figure("n_agents_i", "prob_mut", False)

    norm = LogNorm(
        vmin=fixed_df["n_agents_i"].min() / 2, vmax=fixed_df["n_agents_i"].max() * 2
    )

    for n_agents_i, group_df in fixed_df.groupby("n_agents_i"):

        def plot_mean_and_uncertainty(ax: Axes, y_col: str) -> None:
            color = CMAP(norm(cast(float, n_agents_i)))
            x = group_df["strat_phe_0_i"]
            y = group_df[(y_col, "mean")]
            yerr = group_df[(y_col, "sem")]
            ax.errorbar(x, y, yerr, None, c=color, **PLOT_STYLE)

        plot_mean_and_uncertainty(axs_0[0], "avg_growth_rate")
        plot_mean_and_uncertainty(axs_1[0], "extinct_rate")
        plot_mean_and_uncertainty(axs_2[0], "dist_phe_0")
        plot_mean_and_uncertainty(axs_3[0], "std_dev_growth_rate")
        plot_mean_and_uncertainty(axs_4[0], "avg_birth_rate")

    sm = ScalarMappable(norm=norm, cmap=CMAP)
    for fig, axs in zip(
        [fig_0, fig_1, fig_2, fig_3, fig_4], [axs_0, axs_1, axs_2, axs_3, axs_4]
    ):
        set_heatmap_colorbar(fig, axs[1], "n_agents_i", sm)

    fixed_df = fixed_df.sort_values("n_agents_i")

    fit_results = []
    for strat_phe_0_i, group_df in fixed_df.groupby("strat_phe_0_i"):
        color = CMAP(cast(float, strat_phe_0_i))
        x = group_df["n_agents_i"]
        y = group_df[("extinct_rate", "mean")]
        yerr = group_df[("extinct_rate", "sem")]
        axs_5[0].errorbar(x, y, yerr, None, c=color, **PLOT_STYLE)

        x, y, yerr = x[y != 0], y[y != 0], yerr[y != 0]
        fit_results.append(
            {
                "strat_phe_0_i": strat_phe_0_i,
                "avg_growth_rate": group_df[
                    ("avg_growth_rate", "mean")
                ].max(),  # maybe I should use the last N instead of taking the max value -----------
            }
        )

    fit_df = pd.DataFrame(fit_results)
    strat_phe_0_i_values = fit_df["strat_phe_0_i"].to_numpy()
    avg_growth_rate_values = fit_df["avg_growth_rate"].to_numpy()
    avg_growth_rate_spline = make_splrep(strat_phe_0_i_values, avg_growth_rate_values)
    avg_strat_phe_0 = np.linspace(0.0, 1.0, 64)
    avg_growth_rate = avg_growth_rate_spline(avg_strat_phe_0)

    axs_0[0].errorbar(avg_strat_phe_0, avg_growth_rate, ls="--", **LINE_STYLE)

    for ax in [axs_5[0], axs_8[0], axs_9[0]]:
        ax.set_xscale("log")
    for ax in [axs_1[0], axs_5[0], axs_8[0], axs_9[0]]:
        ax.set_yscale("log")

    extinct_rates = fixed_df[("extinct_rate", "mean")]
    min_extinct_rate = np.min(extinct_rates[extinct_rates > 0.0])
    axs_1[0].set_ylim(bottom=min_extinct_rate)
    axs_5[0].set_ylim(bottom=min_extinct_rate)

    sm = ScalarMappable(cmap=CMAP)
    set_heatmap_colorbar(fig_5, axs_5[1], "strat_phe_0_i", sm)

    norm = LogNorm(vmin=1e2 / 2.0, vmax=1e3 * 2.0)
    random_df = FILTERS["random"](df, job)

    mask = fixed_df[("extinct_rate", "mean")] > 0
    work_df = fixed_df[mask].copy()
    x = np.log(work_df["n_agents_i"])
    y = work_df["strat_phe_0_i"]
    z = np.log(work_df[("extinct_rate", "mean")])
    sem = work_df[("extinct_rate", "sem")]
    mean = work_df[("extinct_rate", "mean")]
    weights = mean / sem

    x_min = np.log(random_df["n_agents_i"].min())
    x_max = np.log(random_df["n_agents_i"].max())
    y_min, y_max = 0.0, 1.0
    tx = []
    ty = np.linspace(0.2, 0.8, 8).tolist()

    kx, ky = 2, 3

    spl = LSQBivariateSpline(
        x, y, z, tx, ty, w=weights, bbox=[x_min, x_max, y_min, y_max], kx=kx, ky=ky
    )

    target_strat = np.linspace(0.0, 1.0, 64)
    n_agents_i_values = sorted(random_df["n_agents_i"].unique())
    log_n_vals = np.log(n_agents_i_values)
    log_n_mesh, strat_mesh = np.meshgrid(log_n_vals, target_strat, indexing="ij")
    log_extinct_flat = spl.ev(log_n_mesh.ravel(), strat_mesh.ravel())
    extinct_rate_grid = np.exp(log_extinct_flat.reshape(log_n_mesh.shape))
    for strat_phe_0_i, group_df in fixed_df.groupby("strat_phe_0_i"):
        color = CMAP(cast(float, strat_phe_0_i))
        x = n_agents_i_values
        y = np.exp(spl.ev(np.log(x), strat_phe_0_i))
        axs_5[0].errorbar(x, y, ls="--", **LINE_STYLE)

    avg_strat_phe_0_mean = []
    exp_avg_strat_phe_0_mean = []
    for n_agents_i, group_df in random_df.groupby("n_agents_i"):
        n_idx = n_agents_i_values.index(n_agents_i)
        extinct_rate = extinct_rate_grid[n_idx, :]
        avg_strat_phe_0_mean_row = []
        exp_avg_strat_phe_0_mean_row = []
        for prob_mut, subgroup_df in group_df.groupby("prob_mut"):
            log_dist_avg_strat_phe_0 = (n_agents_i * avg_growth_rate) - np.log(
                extinct_rate + prob_mut * avg_growth_rate.mean()
            )
            log_dist_avg_strat_phe_0 -= np.max(log_dist_avg_strat_phe_0)
            dist_avg_strat_phe_0 = np.exp(log_dist_avg_strat_phe_0)
            dist_avg_strat_phe_0 /= np.sum(dist_avg_strat_phe_0) / len(avg_strat_phe_0)
            exp_avg_strat_phe_0_mean_row.append(
                (avg_strat_phe_0 * dist_avg_strat_phe_0 / len(avg_strat_phe_0)).sum()
            )
            strat_phe_0, dist_avg_strat_phe_0 = get_dist_avg_strat_phe_0(subgroup_df)
            avg_strat_phe_0_mean_row.append(
                (
                    np.array(strat_phe_0)
                    * np.array(dist_avg_strat_phe_0).ravel()
                    / len(strat_phe_0)
                ).sum()
            )
        avg_strat_phe_0_mean.append(avg_strat_phe_0_mean_row)
        exp_avg_strat_phe_0_mean.append(exp_avg_strat_phe_0_mean_row)

    plot_avg_strat_phe_0(fig_8, axs_8[0], axs_8[1], random_df, exp_avg_strat_phe_0_mean)
    plot_avg_strat_phe_0(fig_9, axs_9[0], axs_9[1], random_df, avg_strat_phe_0_mean)

    fig_dir = job.base_dir / "plots" / "fixed"
    fig_dir.mkdir(parents=True, exist_ok=True)

    fig_0.savefig(fig_dir / "avg_growth_rate.pdf")
    fig_1.savefig(fig_dir / "extinct_rate.pdf")
    fig_2.savefig(fig_dir / "dist_phe_0.pdf")
    fig_3.savefig(fig_dir / "std_dev_growth_rate.pdf")
    fig_4.savefig(fig_dir / "avg_birth_rate.pdf")
    fig_5.savefig(fig_dir / "extinct_rate_scaling.pdf")
    fig_6.savefig(fig_dir / "exp_dist_avg_strat_phe_0.pdf")
    fig_7.savefig(fig_dir / "dist_avg_strat_phe_0.pdf")
    fig_8.savefig(fig_dir / "exp_avg_strat_phe_0.pdf")
    fig_9.savefig(fig_dir / "avg_strat_phe_0.pdf")

    print_process_msg("made 'fixed' plots")


def plot_sim_jobs(sim_jobs: list[SimJob]) -> None:
    avg_analyses = collect_avg_analyses(sim_jobs)
    job = sim_jobs[0]
    run_time_series = collect_run_time_series(job, 0)

    rmtree(job.base_dir / "plots", ignore_errors=True)

    with ProcessPoolExecutor(max_workers=N_CORES) as pool:
        futures = [
            pool.submit(make_param_plots, "strat_phe_0_i", avg_analyses, job),
            pool.submit(make_param_plots, "prob_mut", avg_analyses, job),
            pool.submit(make_param_plots, "n_agents_i", avg_analyses, job),
            pool.submit(make_time_series_plots, run_time_series, job),
            pool.submit(make_fixed_plots, avg_analyses, job),
        ]

        for future in as_completed(futures):
            future.result()
