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
mpl.rcParams["font.size"] = 11

CM = 1 / 2.54

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


def plot_sim_jobs(sim_jobs: List[SimJob]) -> None:
    init_sim_job = sim_jobs[0]

    avg_analyses = collect_avg_analyses(sim_jobs)

    n_hist_bins = len(
        [
            col
            for col in avg_analyses.columns
            if "dist_strat_phe_0_" in col[0] and "mean" in col[1]
        ]
    )

    fig_1 = Figure(figsize=(9.0 * CM, 6.0 * CM))
    ax_1 = fig_1.add_subplot()
    ax_1.set_xlabel("$\\langle\\mu\\rangle$")
    ax_1.set_ylabel("$r_e$")
    ax_1.set_yscale("log")

    fig_2 = Figure(figsize=(9.0 * CM, 6.0 * CM))
    ax_2 = fig_2.add_subplot()
    ax_2.set_xlabel("$s(0)_i$")
    ax_2.set_ylabel("$\\langle\\mu\\rangle$")

    fig_3 = Figure(figsize=(9.0 * CM, 6.0 * CM))
    ax_3 = fig_3.add_subplot()
    ax_3.set_xlabel("$s(0)_i$")
    ax_3.set_ylabel("$\\langle s(0)\\rangle$")

    fig_4 = Figure(figsize=(9.0 * CM, 6.0 * CM))
    gs = gridspec.GridSpec(1, 3, figure=fig_4, width_ratios=[64, 8, 1], wspace=0)
    ax_4_l = fig_4.add_subplot(gs[0, 0])
    ax_4_r = fig_4.add_subplot(gs[0, 1])
    ax_4_c = fig_4.add_subplot(gs[0, 2])
    ax_4_l.set_ylabel("$s(0)$")
    ax_4_l.set_xlabel("$s(0)_i$")
    ax_4_r.set_xlabel("random init")
    ax_4_r.set_xticks([])
    ax_4_r.set_yticks([])

    strat_phe_avg_analyses = avg_analyses[
        (
            (avg_analyses["prob_mut"] == init_sim_job.config["model"]["prob_mut"])
            | (avg_analyses["prob_mut"] == 0)
        )
        & (avg_analyses["n_agents"] == init_sim_job.config["init"]["n_agents"])
    ]

    sim_type = strat_phe_avg_analyses["sim_type"]

    max_mu_strat: Any = None

    for strat_phe_avg_analyses, color, label in [
        (strat_phe_avg_analyses[sim_type == SimType.FIXED], COLORS[1], "fixed strat"),
        (strat_phe_avg_analyses[sim_type == SimType.EVOL], COLORS[7], "evolutive"),
        (strat_phe_avg_analyses[sim_type == SimType.RANDOM], COLORS[11], "random init"),
    ]:
        ax_1.errorbar(
            strat_phe_avg_analyses[("growth_rate", "mean")],
            strat_phe_avg_analyses[("extinct_rate", "mean")],
            xerr=strat_phe_avg_analyses[("growth_rate", "sem")],
            yerr=strat_phe_avg_analyses[("extinct_rate", "sem")],
            c=color,
            label=label,
            **PLOT_STYLE,
        )
        ax_1.axvline(
            strat_phe_avg_analyses[("growth_rate", "mean")].mean(),
            c=color,
            **LINE_STYLE,
        )
        ax_1.axhline(
            strat_phe_avg_analyses[("extinct_rate", "mean")].mean(),
            c=color,
            **LINE_STYLE,
        )

        if label == "fixed strat":
            max_mu_strat = strat_phe_avg_analyses["strat_phe_0"][
                strat_phe_avg_analyses[("growth_rate", "mean")].idxmax()
            ]

        if label == "random init":
            for growth_rate_mean, growth_rate_sem in strat_phe_avg_analyses[
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
                strat_phe_avg_analyses["strat_phe_0"],
                strat_phe_avg_analyses[("growth_rate", "mean")],
                yerr=strat_phe_avg_analyses[("growth_rate", "sem")],
                c=color,
                label=label,
                **PLOT_STYLE,
            )

        if label == "random init":
            for avg_strat_phe_0, std_dev_strat_phe in strat_phe_avg_analyses[
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
                strat_phe_avg_analyses["strat_phe_0"],
                strat_phe_avg_analyses[("avg_strat_phe_0", "mean")],
                yerr=strat_phe_avg_analyses[("avg_strat_phe_0", "sem")],
                c=color,
                label=label,
                **PLOT_STYLE,
            )
            ax_3.fill_between(
                strat_phe_avg_analyses["strat_phe_0"],
                strat_phe_avg_analyses[("avg_strat_phe_0", "mean")]
                - strat_phe_avg_analyses[("std_dev_strat_phe", "mean")],
                strat_phe_avg_analyses[("avg_strat_phe_0", "mean")]
                + strat_phe_avg_analyses[("std_dev_strat_phe", "mean")],
                color=color,
                **FILL_STYLE,
            )

        if label == "evolutive":
            hm_x = strat_phe_avg_analyses["strat_phe_0"].tolist()
            hm_z1 = list()
            for bin in range(n_hist_bins):
                hm_z1.append(
                    strat_phe_avg_analyses[
                        (f"dist_strat_phe_0_{bin}", "mean")
                    ].tolist(),
                )
            im = ax_4_l.pcolormesh(
                hm_x,
                [(i + 0.5) / n_hist_bins for i in range(n_hist_bins)],
                hm_z1,
                cmap=CMAP,
                vmin=0.0,
                vmax=1.0,
                shading="nearest",
            )
            cbar = fig_4.colorbar(im, cax=ax_4_c, aspect=64)
            cbar.ax.set_ylabel("$p(s(0))$")
        elif label == "random init":
            hm_z2 = list()
            for bin in range(n_hist_bins):
                hm_z2.append(
                    strat_phe_avg_analyses[
                        (f"dist_strat_phe_0_{bin}", "mean")
                    ].tolist(),
                )
            ax_4_r.pcolormesh(
                [0.0, 1.0],
                [i / n_hist_bins for i in range(n_hist_bins + 1)],
                hm_z2,
                cmap=CMAP,
                vmin=0.0,
                vmax=1.0,
            )

    fig_dir = init_sim_job.base_dir / "plots" / "strat_phe"
    fig_dir.mkdir(parents=True, exist_ok=True)

    ax_1.legend()
    fig_1.savefig(fig_dir / "extinct_rate.pdf")

    ax_2.axvline(max_mu_strat, color="gray", ls="-.")
    ax_2.legend()
    fig_2.savefig(fig_dir / "growth_rate.pdf")

    ax_3.axhline(max_mu_strat, color="gray", ls="-.")
    ax_3.legend()
    fig_3.savefig(fig_dir / "avg_strat_phe.pdf")

    ax_4_l.axhline(max_mu_strat, color="gray", ls="-.")
    ax_4_r.axhline(max_mu_strat, color="gray", ls="-.")
    fig_4.savefig(fig_dir / "dist_strat_phe.pdf")

    # ...

    fig_1 = Figure(figsize=(9.0 * CM, 6.0 * CM))
    ax_1 = fig_1.add_subplot()
    ax_1.set_xlabel("$p_{\\text{mut}}$")
    ax_1.set_ylabel("$r_e$")
    ax_1.set_xscale("log")
    ax_1.set_yscale("log")

    fig_2 = Figure(figsize=(9.0 * CM, 6.0 * CM))
    ax_2 = fig_2.add_subplot()
    ax_2.set_xlabel("$p_{\\text{mut}}$")
    ax_2.set_ylabel("$\\langle\\mu\\rangle$")
    ax_2.set_xscale("log")

    fig_3 = Figure(figsize=(9.0 * CM, 6.0 * CM))
    ax_3 = fig_3.add_subplot()
    ax_3.set_xlabel("$p_{\\text{mut}}$")
    ax_3.set_ylabel("$\\langle s(0)\\rangle$")
    ax_3.set_xscale("log")

    fig_4 = Figure(figsize=(9.0 * CM, 6.0 * CM))
    gs = gridspec.GridSpec(1, 2, figure=fig_4, width_ratios=[64, 1], wspace=0)
    ax_4 = fig_4.add_subplot(gs[0, 0])
    ax_4_c = fig_4.add_subplot(gs[0, 1])
    ax_4.set_xlabel("$p_{\\text{mut}}$")
    ax_4.set_ylabel("$s(0)$")
    ax_4.set_xscale("log")

    prob_mut_avg_analyses = avg_analyses[
        (avg_analyses["sim_type"] == SimType.RANDOM)
        & (avg_analyses["n_agents"] == init_sim_job.config["init"]["n_agents"])
    ]

    ax_1.errorbar(
        prob_mut_avg_analyses["prob_mut"],
        prob_mut_avg_analyses[("extinct_rate", "mean")],
        yerr=prob_mut_avg_analyses[("extinct_rate", "sem")],
        c=COLORS[11],
        **PLOT_STYLE,
    )

    ax_2.errorbar(
        prob_mut_avg_analyses["prob_mut"],
        prob_mut_avg_analyses[("growth_rate", "mean")],
        yerr=prob_mut_avg_analyses[("growth_rate", "sem")],
        c=COLORS[11],
        **PLOT_STYLE,
    )

    ax_3.plot(
        prob_mut_avg_analyses["prob_mut"],
        prob_mut_avg_analyses[("avg_strat_phe_0", "mean")],
        c=COLORS[11],
        **PLOT_STYLE,
    )
    ax_3.fill_between(
        prob_mut_avg_analyses["prob_mut"],
        prob_mut_avg_analyses[("avg_strat_phe_0", "mean")]
        - prob_mut_avg_analyses[("std_dev_strat_phe", "mean")],
        prob_mut_avg_analyses[("avg_strat_phe_0", "mean")]
        + prob_mut_avg_analyses[("std_dev_strat_phe", "mean")],
        color=COLORS[11],
        **FILL_STYLE,
    )

    hm_x = prob_mut_avg_analyses["prob_mut"].tolist()
    hm_z = list()
    for bin in range(n_hist_bins):
        hm_z.append(
            prob_mut_avg_analyses[(f"dist_strat_phe_0_{bin}", "mean")].tolist(),
        )
    im = ax_4.pcolormesh(
        hm_x,
        [(i + 0.5) / n_hist_bins for i in range(n_hist_bins)],
        hm_z,
        cmap=CMAP,
        vmin=0.0,
        vmax=1.0,
        shading="nearest",
    )
    ax_4.set_xlim(hm_x[0], hm_x[-1])

    cbar = fig_4.colorbar(im, cax=ax_4_c, aspect=64)
    cbar.ax.set_ylabel("$p(s(0))$")

    fig_dir = init_sim_job.base_dir / "plots" / "prob_mut"
    fig_dir.mkdir(parents=True, exist_ok=True)

    fig_1.savefig(fig_dir / "extinct_rate.pdf")

    fig_2.savefig(fig_dir / "growth_rate.pdf")

    fig_3.savefig(fig_dir / "avg_strat_phe.pdf")

    fig_4.savefig(fig_dir / "dist_strat_phe.pdf")

    print("plots made")
