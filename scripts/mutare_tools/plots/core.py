import pandas as pd
import numpy as np
from scipy.interpolate import make_splrep, LSQBivariateSpline
from shutil import rmtree
from matplotlib.axes import Axes
from matplotlib.colors import LogNorm
from matplotlib.cm import ScalarMappable
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import cast, Any

from ..exec import N_CORES, SimJob, print_process_msg
from ..analysis import SimType, collect_avg_analyses, collect_run_time_series

from .utils import (
    CMAP,
    PLOT_STYLE,
    LINE_STYLE,
    COL_TEX_LABELS,
    FILTERS,
    create_standard_figure,
    create_colorbar_figure,
    plot_horizontal_bands,
    plot_errorbar,
    plot_errorband,
    plot_main_heatmap,
    plot_side_heatmap,
    get_optimal_strat_phe_0,
    plot_dist_phe_0_lims,
    plot_extinct_times,
    plot_time_series,
    get_dist_avg_strat_phe_0,
)


def make_param_plots(param: str, df: pd.DataFrame, job: SimJob) -> None:
    param_df = FILTERS[param](df, job).sort_values(param)
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

        plot_mean_and_uncertainty(ax_1, "avg_growth_rate", None)
        plot_mean_and_uncertainty(ax_2, "extinct_rate", None)

        plot_errorbar(ax_3, group_df, "avg_growth_rate", "extinct_rate", True)

        if param == "strat_phe_0_i":
            if sim_type == SimType.FIXED:
                plot_main_heatmap(
                    fig_4, axs_4[0], axs_4[2], group_df, param, "dist_n_agents"
                )
            elif sim_type == SimType.EVOL:
                plot_main_heatmap(
                    fig_5, axs_5[0], axs_5[2], group_df, param, "dist_avg_strat_phe_0"
                )
            elif sim_type == SimType.RANDOM:
                plot_side_heatmap(axs_4[1], group_df, "dist_n_agents")
                plot_side_heatmap(axs_5[1], group_df, "dist_avg_strat_phe_0")
        else:
            plot_main_heatmap(
                fig_4, axs_4[0], axs_4[1], group_df, param, "dist_n_agents"
            )
            plot_main_heatmap(
                fig_5, axs_5[0], axs_5[1], group_df, param, "dist_avg_strat_phe_0"
            )

        plot_mean_and_uncertainty(ax_6, "avg_strat_phe_0", "std_dev_strat_phe")
        plot_mean_and_uncertainty(ax_7, "dist_phe_0", None)
        plot_mean_and_uncertainty(ax_8, "std_dev_growth_rate", None)

    if param == "strat_phe_0_i":
        plot_dist_phe_0_lims(ax_7, param_df, job)

    if param == "prob_mut":
        group_df = FILTERS["fixed_i"](df, job).sort_values("strat_phe_0_i")

        exp_extinct_rates = np.zeros(len(param_df))
        extinct_rate_spline = make_splrep(
            group_df["strat_phe_0_i"], group_df[("extinct_rate", "mean")]
        )
        # refactor this and do the same for the average growth rate ------------------
        strat_phe_0, dist_avg_strat_phe_0 = get_dist_avg_strat_phe_0(param_df)
        hist_bins = len(strat_phe_0)
        for idx in range(hist_bins):
            exp_extinct_rates += (
                dist_avg_strat_phe_0[idx]
                * extinct_rate_spline(strat_phe_0[idx])
                / hist_bins
            )

        ax_2.plot(param_df["prob_mut"], exp_extinct_rates, ls="-.", **LINE_STYLE)

        plot_errorbar(ax_3, group_df, "avg_growth_rate", "extinct_rate", True)

    max_avg_growth = get_optimal_strat_phe_0(df, job, "avg_growth_rate", "max")
    min_extinct = get_optimal_strat_phe_0(df, job, "extinct_rate", "min")
    if param == "strat_phe_0_i":
        for ax in [ax_1, ax_2, ax_8]:
            ax.axvline(max_avg_growth, ls="--", **LINE_STYLE)
            ax.axvline(min_extinct, ls=":", **LINE_STYLE)
    for ax in axs_5[:-1] + [ax_6]:
        ax.axhline(max_avg_growth, ls="--", **LINE_STYLE)
        ax.axhline(min_extinct, ls=":", **LINE_STYLE)

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
    scaling_df = FILTERS["fixed"](df, job).sort_values("strat_phe_0_i")
    if scaling_df["n_agents_i"].nunique() < 2:
        return

    fig_1, axs_1 = create_colorbar_figure("strat_phe_0_i", "avg_growth_rate", False)
    fig_2, axs_2 = create_colorbar_figure("strat_phe_0_i", "extinct_rate", False)
    fig_3, axs_3 = create_colorbar_figure("strat_phe_0_i", "dist_phe_0", False)
    fig_4, axs_4 = create_colorbar_figure("strat_phe_0_i", "std_dev_growth_rate", False)

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
        vmin=scaling_df["n_agents_i"].min() / 2.0,
        vmax=scaling_df["n_agents_i"].max() * 2.0,
    )

    for n_agents_i, group_df in scaling_df.groupby("n_agents_i"):

        def plot_mean_and_uncertainty(ax: Axes, y_col: str) -> None:
            color = CMAP(norm(cast(float, n_agents_i)))
            x = group_df["strat_phe_0_i"]
            y = group_df[(y_col, "mean")]
            yerr = group_df[(y_col, "sem")]
            ax.errorbar(x, y, yerr, None, c=color, **PLOT_STYLE)

        plot_mean_and_uncertainty(axs_1[0], "avg_growth_rate")
        plot_mean_and_uncertainty(axs_2[0], "extinct_rate")
        plot_mean_and_uncertainty(axs_3[0], "dist_phe_0")
        plot_mean_and_uncertainty(axs_4[0], "std_dev_growth_rate")

    # use function for this -------------------------------------------------
    sm = ScalarMappable(norm=norm, cmap=CMAP)
    for fig, axs in [(fig_1, axs_1), (fig_2, axs_2), (fig_3, axs_3), (fig_4, axs_4)]:
        cbar = fig.colorbar(sm, cax=axs[1], aspect=64)
        cbar.ax.set_ylabel(COL_TEX_LABELS["n_agents_i"])

    scaling_df = scaling_df.sort_values("n_agents_i")

    fit_results = []
    for strat_phe_0_i, group_df in scaling_df.groupby("strat_phe_0_i"):
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

    axs_1[0].errorbar(avg_strat_phe_0, avg_growth_rate, ls=":", **LINE_STYLE)

    for ax in [axs_5[0], axs_8[0], axs_9[0]]:
        ax.set_xscale("log")
    for ax in [axs_2[0], axs_5[0], axs_8[0], axs_9[0]]:
        ax.set_yscale("log")

    extinct_rates = scaling_df[("extinct_rate", "mean")]
    min_extinct_rate = np.min(extinct_rates[extinct_rates > 0.0])
    axs_2[0].set_ylim(bottom=min_extinct_rate)

    # use function for this -------------------------------------------------
    sm = ScalarMappable(cmap=CMAP)
    cbar = fig_5.colorbar(sm, cax=axs_5[1], aspect=64)
    cbar.ax.set_ylabel(COL_TEX_LABELS["strat_phe_0_i"])

    norm = LogNorm(vmin=1e2 / 2.0, vmax=1e3 * 2.0)
    heatmap_df = FILTERS["random"](df, job)

    mask = scaling_df[("extinct_rate", "mean")] > 0
    work_df = scaling_df[mask].copy()
    x = np.log(work_df["n_agents_i"].values)
    y = cast(Any, work_df["strat_phe_0_i"].values)
    z = np.log(work_df[("extinct_rate", "mean")].values)
    sem = work_df[("extinct_rate", "sem")]
    mean = work_df[("extinct_rate", "mean")]
    weights = ((mean / sem) ** 2).values

    x_min = np.log(heatmap_df["n_agents_i"].min())
    x_max = np.log(heatmap_df["n_agents_i"].max())
    y_min, y_max = 0.0, 1.0
    tx = []
    ty = np.linspace(0.2, 0.8, 8).tolist()

    kx, ky = 2, 3

    spl = LSQBivariateSpline(
        x, y, z, tx, ty, w=weights, bbox=[x_min, x_max, y_min, y_max], kx=kx, ky=ky
    )

    target_strat = np.linspace(0.0, 1.0, 64)
    n_agents_i_values = sorted(heatmap_df["n_agents_i"].unique())
    prob_mut_values = sorted(heatmap_df["prob_mut"].unique())
    log_n_vals = np.log(n_agents_i_values)
    log_n_mesh, strat_mesh = np.meshgrid(log_n_vals, target_strat, indexing="ij")
    log_extinct_flat = spl.ev(log_n_mesh.ravel(), strat_mesh.ravel())
    extinct_rate_grid = np.exp(log_extinct_flat.reshape(log_n_mesh.shape))
    for strat_phe_0_i, group_df in scaling_df.groupby("strat_phe_0_i"):
        color = CMAP(cast(float, strat_phe_0_i))
        x = n_agents_i_values
        y = np.exp(spl.ev(np.log(x), strat_phe_0_i))
        axs_5[0].errorbar(x, y, ls="--", **LINE_STYLE)

    avg_strat_phe_0_mean = []
    exp_avg_strat_phe_0_mean = []
    for n_agents_i, group_df in heatmap_df.groupby("n_agents_i"):
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

    axs_5[0].set_ylim(bottom=1e-10)

    vmin = 0.2
    vmax = 0.8

    im = axs_8[0].pcolormesh(
        n_agents_i_values,
        prob_mut_values,
        np.array(avg_strat_phe_0_mean).transpose(),
        vmin=vmin,
        vmax=vmax,
        cmap=CMAP,
        shading="nearest",
    )
    axs_8[0].set_xlim(n_agents_i_values[0], n_agents_i_values[-1])
    axs_8[0].set_ylim(prob_mut_values[0], prob_mut_values[-1])
    cbar = fig_8.colorbar(im, cax=axs_8[1], aspect=64)
    cbar.ax.set_ylabel(COL_TEX_LABELS["avg_strat_phe_0"])

    im = axs_9[0].pcolormesh(
        n_agents_i_values,
        prob_mut_values,
        np.array(exp_avg_strat_phe_0_mean).transpose(),
        vmin=vmin,
        vmax=vmax,
        cmap=CMAP,
        shading="nearest",
    )
    axs_9[0].set_xlim(n_agents_i_values[0], n_agents_i_values[-1])
    axs_9[0].set_ylim(prob_mut_values[0], prob_mut_values[-1])
    cbar = fig_9.colorbar(im, cax=axs_9[1], aspect=64)
    cbar.ax.set_ylabel(COL_TEX_LABELS["avg_strat_phe_0"])

    fig_dir = job.base_dir / "plots" / "scaling"
    fig_dir.mkdir(parents=True, exist_ok=True)

    fig_1.savefig(fig_dir / "avg_growth_rate.pdf")
    fig_2.savefig(fig_dir / "extinct_rate.pdf")
    fig_3.savefig(fig_dir / "dist_phe_0.pdf")
    fig_4.savefig(fig_dir / "std_dev_growth_rate.pdf")
    fig_5.savefig(fig_dir / "extinct_rate_scaling.pdf")
    fig_8.savefig(fig_dir / "avg_strat_phe_0.pdf")
    fig_9.savefig(fig_dir / "exp_avg_strat_phe_0.pdf")

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
