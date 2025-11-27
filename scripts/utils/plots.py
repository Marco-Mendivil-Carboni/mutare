import pandas as pd
import matplotlib as mpl
from matplotlib.figure import Figure
from matplotlib.axes import Axes
import matplotlib.gridspec as gridspec
import matplotlib.colors as colors
from typing import Dict, List, Tuple, Literal, Any, overload

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


def create_standard_figure(
    xlabel: str, ylabel: str, xscale: str = "linear", yscale: str = "linear"
) -> Tuple[Figure, Axes]:
    fig = Figure(figsize=FIGSIZE)
    ax = fig.add_subplot()
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_xscale(xscale)
    ax.set_yscale(yscale)
    return fig, ax


@overload
def create_heatmap_figure(
    xlabel: str, ylabel: str, panels: Literal[2], xscale: str = "linear"
) -> Tuple[Figure, Axes, Axes]: ...
@overload
def create_heatmap_figure(
    xlabel: str, ylabel: str, panels: Literal[3], xscale: str = "linear"
) -> Tuple[Figure, Axes, Axes, Axes]: ...
def create_heatmap_figure(
    xlabel: str, ylabel: str, panels: int, xscale: str = "linear"
):
    fig = Figure(figsize=FIGSIZE)

    if panels == 2:
        gs = gridspec.GridSpec(1, 2, figure=fig, width_ratios=[64, 1], wspace=0)
        ax_main = fig.add_subplot(gs[0, 0])
        ax_cbar = fig.add_subplot(gs[0, 1])
        ax_main.set_xlabel(xlabel)
        ax_main.set_ylabel(ylabel)
        ax_main.set_xscale(xscale)

        return fig, ax_main, ax_cbar

    elif panels == 3:
        gs = gridspec.GridSpec(1, 3, figure=fig, width_ratios=[64, 8, 1], wspace=0)
        ax_main = fig.add_subplot(gs[0, 0])
        ax_side = fig.add_subplot(gs[0, 1])
        ax_cbar = fig.add_subplot(gs[0, 2])
        ax_main.set_xlabel(xlabel)
        ax_main.set_ylabel(ylabel)
        ax_main.set_xscale(xscale)
        ax_side.set_xticks([])
        ax_side.set_yticks([])

        return fig, ax_main, ax_side, ax_cbar


def get_sim_color_and_label(avg_analyses: pd.DataFrame) -> Tuple[str, str]:
    sim_types = avg_analyses["sim_type"].unique()
    if len(sim_types) != 1:
        raise ValueError("sim_type not unique")
    sim_type = sim_types[0]
    return SIM_COLORS[sim_type], SIM_LABELS[sim_type]


def plot_horizontal_bands(
    ax: Axes,
    avg_analyses: pd.DataFrame,
    mean_col: Tuple[str, str],
    span_col: Tuple[str, str],
) -> None:
    color, label = get_sim_color_and_label(avg_analyses)
    for mean, span in avg_analyses[[mean_col, span_col]].itertuples(index=False):
        ax.axhline(mean, c=color, label=label, ls=":")
        ax.axhspan(mean + span, mean - span, color=color, **FILL_STYLE)
        label = None


def plot_errorbar_with_band(
    ax: Axes,
    avg_analyses: pd.DataFrame,
    x_col: str,
    y_col: str,
    use_xerr: bool,
    y_span_col: str | None,
) -> None:
    color, label = get_sim_color_and_label(avg_analyses)
    x = avg_analyses[(x_col, "mean")] if use_xerr else avg_analyses[x_col]
    y = avg_analyses[(y_col, "mean")]
    xerr = avg_analyses[(x_col, "sem")] if use_xerr else None
    yerr = avg_analyses[(y_col, "sem")]
    ax.errorbar(x, y, yerr, xerr, c=color, label=label, **PLOT_STYLE)
    if y_span_col is not None:
        y_span = avg_analyses[(y_span_col, "mean")]
        ax.fill_between(x, y - y_span, y + y_span, color=color, **FILL_STYLE)


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

    fig_1, ax_1 = create_standard_figure(
        xlabel="$s(0)_i$", ylabel="$r_e$", yscale="log"
    )

    fig_2, ax_2 = create_standard_figure(
        xlabel="$s(0)_i$", ylabel="$\\langle\\mu\\rangle$"
    )

    fig_3, ax_3 = create_standard_figure(
        xlabel="$s(0)_i$", ylabel="$\\langle s(0)\\rangle$"
    )

    fig_4, ax_4_main, ax_4_side, ax_4_cbar = create_heatmap_figure(
        xlabel="$s(0)_i$", ylabel="$s(0)$", panels=3
    )
    ax_4_side.set_xlabel("random init")

    fig_5, ax_5 = create_standard_figure(
        xlabel="$\\langle\\mu\\rangle$", ylabel="$r_e$", yscale="log"
    )

    sim_types = avg_analyses["sim_type"]

    min_extinct_strat: Any = None
    max_growth_strat: Any = None

    for avg_analyses, sim_type in [
        (avg_analyses[sim_types == SimType.FIXED], SimType.FIXED),
        (avg_analyses[sim_types == SimType.EVOL], SimType.EVOL),
        (avg_analyses[sim_types == SimType.RANDOM], SimType.RANDOM),
    ]:
        if sim_type == SimType.FIXED:
            max_growth_strat = avg_analyses["strat_phe_0"][
                avg_analyses[("growth_rate", "mean")].idxmax()
            ]
            min_extinct_strat = avg_analyses["strat_phe_0"][
                avg_analyses[("extinct_rate", "mean")].idxmin()
            ]

        if sim_type == SimType.RANDOM:
            plot_horizontal_bands(
                ax_1, avg_analyses, ("extinct_rate", "mean"), ("extinct_rate", "sem")
            )
        else:
            plot_errorbar_with_band(
                ax_1, avg_analyses, "strat_phe_0", "extinct_rate", False, None
            )

        if sim_type == SimType.RANDOM:
            plot_horizontal_bands(
                ax_2, avg_analyses, ("growth_rate", "mean"), ("growth_rate", "sem")
            )
        else:
            plot_errorbar_with_band(
                ax_2, avg_analyses, "strat_phe_0", "growth_rate", False, None
            )

        if sim_type == SimType.RANDOM:
            plot_horizontal_bands(
                ax_3,
                avg_analyses,
                ("avg_strat_phe_0", "mean"),
                ("std_dev_strat_phe", "mean"),
            )
        else:
            plot_errorbar_with_band(
                ax_3,
                avg_analyses,
                "strat_phe_0",
                "avg_strat_phe_0",
                False,
                "std_dev_strat_phe",
            )

        if sim_type == SimType.EVOL:
            hm_x = avg_analyses["strat_phe_0"].tolist()
            hm_z1 = list()
            for bin in range(hist_bins):
                hm_z1.append(
                    (
                        hist_bins * avg_analyses[(f"dist_strat_phe_0_{bin}", "mean")]
                    ).tolist()
                )
            im = ax_4_main.pcolormesh(
                hm_x,
                [(i + 0.5) / hist_bins for i in range(hist_bins)],
                hm_z1,
                cmap=CMAP,
                vmin=0,
                vmax=hist_bins,
                shading="nearest",
            )
            cbar = fig_4.colorbar(im, cax=ax_4_cbar, aspect=64)
            cbar.ax.set_ylabel("$p(s(0))$")
        elif sim_type == SimType.RANDOM:
            hm_z2 = list()
            for bin in range(hist_bins):
                hm_z2.append(
                    (
                        hist_bins * avg_analyses[(f"dist_strat_phe_0_{bin}", "mean")]
                    ).tolist()
                )
            ax_4_side.pcolormesh(
                [0.0, 1.0],
                [i / hist_bins for i in range(hist_bins + 1)],
                hm_z2,
                cmap=CMAP,
                vmin=0,
                vmax=hist_bins,
            )

        plot_errorbar_with_band(
            ax_5, avg_analyses, "growth_rate", "extinct_rate", True, None
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

    ax_4_main.axhline(max_growth_strat, color="gray", ls="-.")
    ax_4_side.axhline(max_growth_strat, color="gray", ls="-.")
    ax_4_main.axhline(min_extinct_strat, color="gray", ls=":")
    ax_4_side.axhline(min_extinct_strat, color="gray", ls=":")
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

    fig_1, ax_1 = create_standard_figure(
        xlabel="$p_{\\text{mut}}$", ylabel="$r_e$", xscale="log", yscale="log"
    )

    fig_2, ax_2 = create_standard_figure(
        xlabel="$p_{\\text{mut}}$", ylabel="$\\langle\\mu\\rangle$", xscale="log"
    )

    fig_3, ax_3 = create_standard_figure(
        xlabel="$p_{\\text{mut}}$", ylabel="$\\langle s(0)\\rangle$", xscale="log"
    )

    fig_4, ax_4_main, ax_4_cbar = create_heatmap_figure(
        xlabel="$p_{\\text{mut}}$", ylabel="$s(0)$", panels=2, xscale="log"
    )

    fig_5, ax_5 = create_standard_figure(
        xlabel="$\\langle\\mu\\rangle$", ylabel="$r_e$", yscale="log"
    )

    plot_errorbar_with_band(ax_1, avg_analyses, "prob_mut", "extinct_rate", False, None)

    plot_errorbar_with_band(ax_2, avg_analyses, "prob_mut", "growth_rate", False, None)

    plot_errorbar_with_band(
        ax_3, avg_analyses, "prob_mut", "avg_strat_phe_0", False, "std_dev_strat_phe"
    )

    hm_x = avg_analyses["prob_mut"].tolist()
    hm_z = list()
    for bin in range(hist_bins):
        hm_z.append(
            (hist_bins * avg_analyses[(f"dist_strat_phe_0_{bin}", "mean")]).tolist()
        )
    im = ax_4_main.pcolormesh(
        hm_x,
        [(i + 0.5) / hist_bins for i in range(hist_bins)],
        hm_z,
        cmap=CMAP,
        vmin=0,
        vmax=hist_bins,
        shading="nearest",
    )
    ax_4_main.set_xlim(hm_x[0], hm_x[-1])

    cbar = fig_4.colorbar(im, cax=ax_4_cbar, aspect=64)
    cbar.ax.set_ylabel("$p(s(0))$")

    plot_errorbar_with_band(
        ax_5, avg_analyses, "growth_rate", "extinct_rate", True, None
    )

    fig_dir = init_sim_job.base_dir / "plots" / "prob_mut"
    fig_dir.mkdir(parents=True, exist_ok=True)

    fig_1.savefig(fig_dir / "extinct_rate.pdf")

    fig_2.savefig(fig_dir / "growth_rate.pdf")

    fig_3.savefig(fig_dir / "avg_strat_phe.pdf")

    fig_4.savefig(fig_dir / "dist_strat_phe.pdf")

    fig_5.savefig(fig_dir / "rates.pdf")


def generate_n_agents_plots(
    init_sim_job: SimJob, avg_analyses: pd.DataFrame, hist_bins: int
) -> None:
    avg_analyses = avg_analyses[
        (avg_analyses["sim_type"] == SimType.RANDOM)
        & (avg_analyses["prob_mut"] == init_sim_job.config["model"]["prob_mut"])
    ]
    if len(avg_analyses) < 2:
        return

    avg_analyses = avg_analyses.sort_values("n_agents")

    fig_1, ax_1 = create_standard_figure(
        xlabel="$N_0$", ylabel="$r_e$", xscale="log", yscale="log"
    )

    fig_2, ax_2 = create_standard_figure(
        xlabel="$N_0$", ylabel="$\\langle\\mu\\rangle$", xscale="log"
    )

    fig_3, ax_3 = create_standard_figure(
        xlabel="$N_0$", ylabel="$\\langle s(0)\\rangle$", xscale="log"
    )

    fig_4, ax_4_main, ax_4_cbar = create_heatmap_figure(
        xlabel="$N_0$", ylabel="$s(0)$", panels=2, xscale="log"
    )

    fig_5, ax_5 = create_standard_figure(
        xlabel="$\\langle\\mu\\rangle$", ylabel="$r_e$", yscale="log"
    )

    plot_errorbar_with_band(ax_1, avg_analyses, "n_agents", "extinct_rate", False, None)

    plot_errorbar_with_band(ax_2, avg_analyses, "n_agents", "growth_rate", False, None)

    plot_errorbar_with_band(
        ax_3, avg_analyses, "n_agents", "avg_strat_phe_0", False, "std_dev_strat_phe"
    )

    hm_x = avg_analyses["n_agents"].tolist()
    hm_z = list()
    for bin in range(hist_bins):
        hm_z.append(
            (hist_bins * avg_analyses[(f"dist_strat_phe_0_{bin}", "mean")]).tolist()
        )
    im = ax_4_main.pcolormesh(
        hm_x,
        [(i + 0.5) / hist_bins for i in range(hist_bins)],
        hm_z,
        cmap=CMAP,
        vmin=0,
        vmax=hist_bins,
        shading="nearest",
    )
    ax_4_main.set_xlim(hm_x[0], hm_x[-1])

    cbar = fig_4.colorbar(im, cax=ax_4_cbar, aspect=64)
    cbar.ax.set_ylabel("$p(s(0))$")

    plot_errorbar_with_band(
        ax_5, avg_analyses, "growth_rate", "extinct_rate", True, None
    )

    fig_dir = init_sim_job.base_dir / "plots" / "n_agents"
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

    generate_n_agents_plots(init_sim_job, avg_analyses, hist_bins)

    print("plots made")
