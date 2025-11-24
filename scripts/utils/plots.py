import pandas as pd
import matplotlib as mpl
from matplotlib.figure import Figure
import matplotlib.gridspec as gridspec
import matplotlib.colors as colors
from typing import Dict, List, Any

from .exec import SimJob
from .analysis import collect_avg_analyses, SimType

mpl.use("pdf")

mpl.rcParams["text.usetex"] = True
mpl.rcParams["text.latex.preamble"] = "\\usepackage{lmodern}\\usepackage{mathtools}"
mpl.rcParams["font.family"] = "lmodern"
mpl.rcParams["font.size"] = 10

CM = 1 / 2.54

FIGSIZE = (8.0 * CM, 5.0 * CM)

mpl.rcParams["figure.constrained_layout.use"] = True

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

PLOT_STYLE: Dict[str, Any] = dict(ls=":", marker="o", markersize=2)
FILL_STYLE: Dict[str, Any] = dict(lw=0.0, alpha=0.5)
LINE_STYLE: Dict[str, Any] = dict(ls=":", lw=1.0, alpha=0.5)

CMAP = colors.LinearSegmentedColormap.from_list("custom", ["white", COLORS[1]])


def generate_strat_phe_plots(
    init_sim_job: SimJob, avg_analyses: pd.DataFrame, hist_bins: int
) -> None:
    avg_analyses = avg_analyses[
        (
            (avg_analyses["prob_mut"] == init_sim_job.config["model"]["prob_mut"])
            | (avg_analyses["prob_mut"] == 0)
        )
        & (avg_analyses["n_agents"] == init_sim_job.config["init"]["n_agents"])
    ]
    if len(avg_analyses) < 2:
        return

    avg_analyses = avg_analyses.sort_values("strat_phe_0")

    fig_1 = Figure(figsize=FIGSIZE)
    ax_1 = fig_1.add_subplot()
    ax_1.set_xlabel("$s(0)_i$")
    ax_1.set_ylabel("$r_e$")
    ax_1.set_yscale("log")

    fig_2 = Figure(figsize=FIGSIZE)
    ax_2 = fig_2.add_subplot()
    ax_2.set_xlabel("$s(0)_i$")
    ax_2.set_ylabel("$\\langle\\mu\\rangle$")

    fig_3 = Figure(figsize=FIGSIZE)
    ax_3 = fig_3.add_subplot()
    ax_3.set_xlabel("$s(0)_i$")
    ax_3.set_ylabel("$\\langle s(0)\\rangle$")

    fig_4 = Figure(figsize=FIGSIZE)
    gs = gridspec.GridSpec(1, 3, figure=fig_4, width_ratios=[64, 8, 1], wspace=0)
    ax_4_l = fig_4.add_subplot(gs[0, 0])
    ax_4_r = fig_4.add_subplot(gs[0, 1])
    ax_4_c = fig_4.add_subplot(gs[0, 2])
    ax_4_l.set_ylabel("$s(0)$")
    ax_4_l.set_xlabel("$s(0)_i$")
    ax_4_r.set_xlabel("random init")
    ax_4_r.set_xticks([])
    ax_4_r.set_yticks([])

    fig_5 = Figure(figsize=FIGSIZE)
    ax_5 = fig_5.add_subplot()
    ax_5.set_xlabel("$\\langle\\mu\\rangle$")
    ax_5.set_ylabel("$r_e$")
    ax_5.set_yscale("log")

    sim_type = avg_analyses["sim_type"]

    min_extinct_strat: Any = None
    max_growth_strat: Any = None

    for avg_analyses, color, label in [
        (avg_analyses[sim_type == SimType.FIXED], COLORS[1], "fixed strat"),
        (avg_analyses[sim_type == SimType.EVOL], COLORS[7], "evolutive"),
        (avg_analyses[sim_type == SimType.RANDOM], COLORS[11], "random init"),
    ]:
        if label == "fixed strat":
            max_growth_strat = avg_analyses["strat_phe_0"][
                avg_analyses[("growth_rate", "mean")].idxmax()
            ]
            min_extinct_strat = avg_analyses["strat_phe_0"][
                avg_analyses[("extinct_rate", "mean")].idxmin()
            ]

        if label == "random init":
            for extinct_rate_mean, extinct_rate_sem in avg_analyses[
                [("extinct_rate", "mean"), ("extinct_rate", "sem")]
            ].itertuples(index=False):
                ax_1.axhline(extinct_rate_mean, c=color, label=label, ls=":")
                ax_1.axhspan(
                    extinct_rate_mean + extinct_rate_sem,
                    extinct_rate_mean - extinct_rate_sem,
                    color=color,
                    **FILL_STYLE,
                )
        else:
            ax_1.errorbar(
                avg_analyses["strat_phe_0"],
                avg_analyses[("extinct_rate", "mean")],
                yerr=avg_analyses[("extinct_rate", "sem")],
                c=color,
                label=label,
                **PLOT_STYLE,
            )

        if label == "random init":
            for growth_rate_mean, growth_rate_sem in avg_analyses[
                [("growth_rate", "mean"), ("growth_rate", "sem")]
            ].itertuples(index=False):
                ax_2.axhline(growth_rate_mean, c=color, label=label, ls=":")
                ax_2.axhspan(
                    growth_rate_mean + growth_rate_sem,
                    growth_rate_mean - growth_rate_sem,
                    color=color,
                    **FILL_STYLE,
                )
        else:
            ax_2.errorbar(
                avg_analyses["strat_phe_0"],
                avg_analyses[("growth_rate", "mean")],
                yerr=avg_analyses[("growth_rate", "sem")],
                c=color,
                label=label,
                **PLOT_STYLE,
            )

        if label == "random init":
            for avg_strat_phe_0, std_dev_strat_phe in avg_analyses[
                [("avg_strat_phe_0", "mean"), ("std_dev_strat_phe", "mean")]
            ].itertuples(index=False):
                ax_3.axhline(avg_strat_phe_0, c=color, label=label, ls=":")
                ax_3.axhspan(
                    avg_strat_phe_0 + std_dev_strat_phe,
                    avg_strat_phe_0 - std_dev_strat_phe,
                    color=color,
                    **FILL_STYLE,
                )
        else:
            ax_3.errorbar(
                avg_analyses["strat_phe_0"],
                avg_analyses[("avg_strat_phe_0", "mean")],
                yerr=avg_analyses[("avg_strat_phe_0", "sem")],
                c=color,
                label=label,
                **PLOT_STYLE,
            )
            ax_3.fill_between(
                avg_analyses["strat_phe_0"],
                avg_analyses[("avg_strat_phe_0", "mean")]
                - avg_analyses[("std_dev_strat_phe", "mean")],
                avg_analyses[("avg_strat_phe_0", "mean")]
                + avg_analyses[("std_dev_strat_phe", "mean")],
                color=color,
                **FILL_STYLE,
            )

        if label == "evolutive":
            hm_x = avg_analyses["strat_phe_0"].tolist()
            hm_z1 = list()
            for bin in range(hist_bins):
                hm_z1.append(
                    (
                        hist_bins * avg_analyses[(f"dist_strat_phe_0_{bin}", "mean")]
                    ).tolist()
                )
            im = ax_4_l.pcolormesh(
                hm_x,
                [(i + 0.5) / hist_bins for i in range(hist_bins)],
                hm_z1,
                cmap=CMAP,
                vmin=0,
                vmax=hist_bins,
                shading="nearest",
            )
            cbar = fig_4.colorbar(im, cax=ax_4_c, aspect=64)
            cbar.ax.set_ylabel("$p(s(0))$")
        elif label == "random init":
            hm_z2 = list()
            for bin in range(hist_bins):
                hm_z2.append(
                    (
                        hist_bins * avg_analyses[(f"dist_strat_phe_0_{bin}", "mean")]
                    ).tolist()
                )
            ax_4_r.pcolormesh(
                [0.0, 1.0],
                [i / hist_bins for i in range(hist_bins + 1)],
                hm_z2,
                cmap=CMAP,
                vmin=0,
                vmax=hist_bins,
            )

        ax_5.errorbar(
            avg_analyses[("growth_rate", "mean")],
            avg_analyses[("extinct_rate", "mean")],
            xerr=avg_analyses[("growth_rate", "sem")],
            yerr=avg_analyses[("extinct_rate", "sem")],
            c=color,
            label=label,
            **PLOT_STYLE,
        )
        ax_5.axvline(
            avg_analyses[("growth_rate", "mean")].mean(), c=color, **LINE_STYLE
        )
        ax_5.axhline(
            avg_analyses[("extinct_rate", "mean")].mean(), c=color, **LINE_STYLE
        )

    fig_dir = init_sim_job.base_dir / "plots" / "strat_phe"
    fig_dir.mkdir(parents=True, exist_ok=True)

    ax_1.legend()
    ax_1.axvline(max_growth_strat, color="gray", ls="-.")
    ax_1.axvline(min_extinct_strat, color="gray", ls=":")
    fig_1.savefig(fig_dir / "extinct_rate.pdf")

    ax_2.axvline(max_growth_strat, color="gray", ls="-.")
    ax_2.axvline(min_extinct_strat, color="gray", ls=":")
    ax_2.legend()
    fig_2.savefig(fig_dir / "growth_rate.pdf")

    ax_3.axhline(max_growth_strat, color="gray", ls="-.")
    ax_3.axhline(min_extinct_strat, color="gray", ls=":")
    ax_3.legend()
    fig_3.savefig(fig_dir / "avg_strat_phe.pdf")

    ax_4_l.axhline(max_growth_strat, color="gray", ls="-.")
    ax_4_r.axhline(max_growth_strat, color="gray", ls="-.")
    ax_4_l.axhline(min_extinct_strat, color="gray", ls=":")
    ax_4_r.axhline(min_extinct_strat, color="gray", ls=":")
    fig_4.savefig(fig_dir / "dist_strat_phe.pdf")

    ax_5.legend()
    fig_5.savefig(fig_dir / "rates.pdf")


def generate_prob_mut_plots(
    init_sim_job: SimJob, avg_analyses: pd.DataFrame, hist_bins: int
) -> None:
    avg_analyses = avg_analyses[
        (avg_analyses["sim_type"] == SimType.RANDOM)
        & (avg_analyses["n_agents"] == init_sim_job.config["init"]["n_agents"])
    ]
    if len(avg_analyses) < 2:
        return

    avg_analyses = avg_analyses.sort_values("prob_mut")

    fig_1 = Figure(figsize=FIGSIZE)
    ax_1 = fig_1.add_subplot()
    ax_1.set_xlabel("$p_{\\text{mut}}$")
    ax_1.set_ylabel("$r_e$")
    ax_1.set_xscale("log")
    ax_1.set_yscale("log")

    fig_2 = Figure(figsize=FIGSIZE)
    ax_2 = fig_2.add_subplot()
    ax_2.set_xlabel("$p_{\\text{mut}}$")
    ax_2.set_ylabel("$\\langle\\mu\\rangle$")
    ax_2.set_xscale("log")

    fig_3 = Figure(figsize=FIGSIZE)
    ax_3 = fig_3.add_subplot()
    ax_3.set_xlabel("$p_{\\text{mut}}$")
    ax_3.set_ylabel("$\\langle s(0)\\rangle$")
    ax_3.set_xscale("log")

    fig_4 = Figure(figsize=FIGSIZE)
    gs = gridspec.GridSpec(1, 2, figure=fig_4, width_ratios=[64, 1], wspace=0)
    ax_4 = fig_4.add_subplot(gs[0, 0])
    ax_4_c = fig_4.add_subplot(gs[0, 1])
    ax_4.set_xlabel("$p_{\\text{mut}}$")
    ax_4.set_ylabel("$s(0)$")
    ax_4.set_xscale("log")

    fig_5 = Figure(figsize=FIGSIZE)
    ax_5 = fig_5.add_subplot()
    ax_5.set_xlabel("$\\langle\\mu\\rangle$")
    ax_5.set_ylabel("$r_e$")
    ax_5.set_yscale("log")

    ax_1.errorbar(
        avg_analyses["prob_mut"],
        avg_analyses[("extinct_rate", "mean")],
        yerr=avg_analyses[("extinct_rate", "sem")],
        c=COLORS[11],
        **PLOT_STYLE,
    )

    ax_2.errorbar(
        avg_analyses["prob_mut"],
        avg_analyses[("growth_rate", "mean")],
        yerr=avg_analyses[("growth_rate", "sem")],
        c=COLORS[11],
        **PLOT_STYLE,
    )

    ax_3.plot(
        avg_analyses["prob_mut"],
        avg_analyses[("avg_strat_phe_0", "mean")],
        c=COLORS[11],
        **PLOT_STYLE,
    )
    ax_3.fill_between(
        avg_analyses["prob_mut"],
        avg_analyses[("avg_strat_phe_0", "mean")]
        - avg_analyses[("std_dev_strat_phe", "mean")],
        avg_analyses[("avg_strat_phe_0", "mean")]
        + avg_analyses[("std_dev_strat_phe", "mean")],
        color=COLORS[11],
        **FILL_STYLE,
    )

    hm_x = avg_analyses["prob_mut"].tolist()
    hm_z = list()
    for bin in range(hist_bins):
        hm_z.append(
            (hist_bins * avg_analyses[(f"dist_strat_phe_0_{bin}", "mean")]).tolist()
        )
    im = ax_4.pcolormesh(
        hm_x,
        [(i + 0.5) / hist_bins for i in range(hist_bins)],
        hm_z,
        cmap=CMAP,
        vmin=0,
        vmax=hist_bins,
        shading="nearest",
    )
    ax_4.set_xlim(hm_x[0], hm_x[-1])

    cbar = fig_4.colorbar(im, cax=ax_4_c, aspect=64)
    cbar.ax.set_ylabel("$p(s(0))$")

    ax_5.errorbar(
        avg_analyses[("growth_rate", "mean")],
        avg_analyses[("extinct_rate", "mean")],
        xerr=avg_analyses[("growth_rate", "sem")],
        yerr=avg_analyses[("extinct_rate", "sem")],
        c=COLORS[11],
        **PLOT_STYLE,
    )

    fig_dir = init_sim_job.base_dir / "plots" / "prob_mut"
    fig_dir.mkdir(parents=True, exist_ok=True)

    fig_1.savefig(fig_dir / "extinct_rate.pdf")

    fig_2.savefig(fig_dir / "growth_rate.pdf")

    fig_3.savefig(fig_dir / "avg_strat_phe.pdf")

    fig_4.savefig(fig_dir / "dist_strat_phe.pdf")

    fig_5.savefig(fig_dir / "rates.pdf")


def plot_sim_jobs(sim_jobs: List[SimJob]) -> None:
    init_sim_job = sim_jobs[0]
    avg_analyses = collect_avg_analyses(sim_jobs)
    hist_bins = len(
        [
            col
            for col in avg_analyses.columns
            if "dist_strat_phe_0_" in col[0] and "mean" in col[1]
        ]
    )

    generate_strat_phe_plots(init_sim_job, avg_analyses, hist_bins)

    generate_prob_mut_plots(init_sim_job, avg_analyses, hist_bins)

    print("plots made")
