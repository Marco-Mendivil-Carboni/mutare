import pandas as pd
import matplotlib as mpl
from matplotlib.figure import Figure
from matplotlib.axes import Axes
import matplotlib.gridspec as gridspec
import matplotlib.colors as colors
from typing import Literal, Any, overload

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
COL_SCALES: dict[str, str] = {
    "strat_phe_0": "linear",
    "prob_mut": "log",
    "n_agents": "log",
    "extinct_rate": "log",
    "growth_rate": "linear",
    "avg_strat_phe_0": "linear",
}


def create_standard_figure(x_col: str, y_col: str) -> tuple[Figure, Axes]:
    fig = Figure(figsize=FIGSIZE)
    ax = fig.add_subplot()
    ax.set_xlabel(COL_TEX_LABELS[x_col])
    ax.set_ylabel(COL_TEX_LABELS[y_col])
    ax.set_xscale(COL_SCALES[x_col])
    ax.set_yscale(COL_SCALES[y_col])
    return fig, ax


@overload
def create_heatmap_figure(
    x_col: str, panels: Literal[2]
) -> tuple[Figure, Axes, Axes]: ...
@overload
def create_heatmap_figure(
    x_col: str, panels: Literal[3]
) -> tuple[Figure, Axes, Axes, Axes]: ...
def create_heatmap_figure(x_col: str, panels: int):
    fig = Figure(figsize=FIGSIZE)

    if panels == 2:
        gs = gridspec.GridSpec(1, 2, figure=fig, width_ratios=[64, 1], wspace=0)
        ax_main = fig.add_subplot(gs[0, 0])
        ax_cbar = fig.add_subplot(gs[0, 1])
        ax_main.set_xlabel(COL_TEX_LABELS[x_col])
        ax_main.set_ylabel("$s(0)$")
        ax_main.set_xscale(COL_SCALES[x_col])

        return fig, ax_main, ax_cbar

    elif panels == 3:
        gs = gridspec.GridSpec(1, 3, figure=fig, width_ratios=[64, 8, 1], wspace=0)
        ax_main = fig.add_subplot(gs[0, 0])
        ax_side = fig.add_subplot(gs[0, 1])
        ax_cbar = fig.add_subplot(gs[0, 2])
        ax_main.set_xlabel(COL_TEX_LABELS[x_col])
        ax_main.set_ylabel("$s(0)$")
        ax_main.set_xscale(COL_SCALES[x_col])
        ax_side.set_xticks([])
        ax_side.set_yticks([])

        return fig, ax_main, ax_side, ax_cbar


def get_sim_color_and_label(avg_analyses: pd.DataFrame) -> tuple[str, str]:
    sim_types = avg_analyses["sim_type"].unique()
    if len(sim_types) != 1:
        raise ValueError("sim_type not unique")
    sim_type = sim_types[0]
    return SIM_COLORS[sim_type], SIM_LABELS[sim_type]


def plot_horizontal_bands(
    ax: Axes,
    avg_analyses: pd.DataFrame,
    mean_col: tuple[str, str],
    span_col: tuple[str, str],
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


def count_hist_bins(avg_analyses: pd.DataFrame) -> int:
    hist_bins = 0
    while (f"dist_strat_phe_0_{hist_bins}", "mean") in avg_analyses.columns:
        hist_bins += 1
    return hist_bins


def generate_heatmap_matrix(
    avg_analyses: pd.DataFrame, hist_bins: int
) -> list[list[float]]:
    hm_z = []
    for bin in range(hist_bins):
        hm_z.append(
            (hist_bins * avg_analyses[(f"dist_strat_phe_0_{bin}", "mean")]).tolist()
        )
    return hm_z


def plot_main_heatmap(
    fig: Figure, ax_main: Axes, ax_cbar: Axes, avg_analyses: pd.DataFrame, x_col: str
) -> None:
    hist_bins = count_hist_bins(avg_analyses)
    hm_x = avg_analyses[x_col].tolist()
    hm_y = [(i + 0.5) / hist_bins for i in range(hist_bins)]
    hm_z = generate_heatmap_matrix(avg_analyses, hist_bins)
    im = ax_main.pcolormesh(
        hm_x, hm_y, hm_z, cmap=CMAP, vmin=0, vmax=hist_bins, shading="nearest"
    )
    ax_main.set_xlim(hm_x[0], hm_x[-1])
    cbar = fig.colorbar(im, cax=ax_cbar, aspect=64)
    cbar.ax.set_ylabel("$p(s(0))$")


def plot_side_heatmap(ax_side: Axes, avg_analyses: pd.DataFrame) -> None:
    hist_bins = count_hist_bins(avg_analyses)
    hm_x = [0.0, 1.0]
    hm_y = [i / hist_bins for i in range(hist_bins + 1)]
    hm_z = generate_heatmap_matrix(avg_analyses, hist_bins)
    ax_side.pcolormesh(hm_x, hm_y, hm_z, cmap=CMAP, vmin=0, vmax=hist_bins)


def generate_strat_phe_plots(init_sim_job: SimJob, avg_analyses: pd.DataFrame) -> None:
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

    fig_1, ax_1 = create_standard_figure("strat_phe_0", "extinct_rate")
    fig_2, ax_2 = create_standard_figure("strat_phe_0", "growth_rate")
    fig_3, ax_3 = create_standard_figure("strat_phe_0", "avg_strat_phe_0")
    fig_4, ax_4_main, ax_4_side, ax_4_cbar = create_heatmap_figure(
        "strat_phe_0", panels=3
    )
    ax_4_side.set_xlabel("random init")
    fig_5, ax_5 = create_standard_figure("growth_rate", "extinct_rate")

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
            plot_main_heatmap(fig_4, ax_4_main, ax_4_cbar, avg_analyses, "strat_phe_0")
        elif sim_type == SimType.RANDOM:
            plot_side_heatmap(ax_4_side, avg_analyses)

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


def generate_prob_mut_plots(init_sim_job: SimJob, avg_analyses: pd.DataFrame) -> None:
    avg_analyses = avg_analyses[
        (avg_analyses["sim_type"] == SimType.RANDOM)
        & (avg_analyses["n_agents"] == init_sim_job.config["init"]["n_agents"])
    ]
    if len(avg_analyses) < 2:
        return

    avg_analyses = avg_analyses.sort_values("prob_mut")

    fig_1, ax_1 = create_standard_figure("prob_mut", "extinct_rate")
    fig_2, ax_2 = create_standard_figure("prob_mut", "growth_rate")
    fig_3, ax_3 = create_standard_figure("prob_mut", "avg_strat_phe_0")
    fig_4, ax_4_main, ax_4_cbar = create_heatmap_figure("prob_mut", panels=2)
    fig_5, ax_5 = create_standard_figure("growth_rate", "extinct_rate")

    plot_errorbar_with_band(ax_1, avg_analyses, "prob_mut", "extinct_rate", False, None)
    plot_errorbar_with_band(ax_2, avg_analyses, "prob_mut", "growth_rate", False, None)
    plot_errorbar_with_band(
        ax_3, avg_analyses, "prob_mut", "avg_strat_phe_0", False, "std_dev_strat_phe"
    )
    plot_main_heatmap(fig_4, ax_4_main, ax_4_cbar, avg_analyses, "prob_mut")
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


def generate_n_agents_plots(init_sim_job: SimJob, avg_analyses: pd.DataFrame) -> None:
    avg_analyses = avg_analyses[
        (avg_analyses["sim_type"] == SimType.RANDOM)
        & (avg_analyses["prob_mut"] == init_sim_job.config["model"]["prob_mut"])
    ]
    if len(avg_analyses) < 2:
        return

    avg_analyses = avg_analyses.sort_values("n_agents")

    fig_1, ax_1 = create_standard_figure("n_agents", "extinct_rate")
    fig_2, ax_2 = create_standard_figure("n_agents", "growth_rate")
    fig_3, ax_3 = create_standard_figure("n_agents", "avg_strat_phe_0")
    fig_4, ax_4_main, ax_4_cbar = create_heatmap_figure("n_agents", panels=2)
    fig_5, ax_5 = create_standard_figure("growth_rate", "extinct_rate")

    plot_errorbar_with_band(ax_1, avg_analyses, "n_agents", "extinct_rate", False, None)
    plot_errorbar_with_band(ax_2, avg_analyses, "n_agents", "growth_rate", False, None)
    plot_errorbar_with_band(
        ax_3, avg_analyses, "n_agents", "avg_strat_phe_0", False, "std_dev_strat_phe"
    )
    plot_main_heatmap(fig_4, ax_4_main, ax_4_cbar, avg_analyses, "n_agents")
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


def plot_sim_jobs(sim_jobs: list[SimJob]) -> None:
    init_sim_job = sim_jobs[0]
    avg_analyses = collect_avg_analyses(sim_jobs)

    generate_strat_phe_plots(init_sim_job, avg_analyses)
    generate_prob_mut_plots(init_sim_job, avg_analyses)
    generate_n_agents_plots(init_sim_job, avg_analyses)

    # generate_param_plots("strat_phe_0", init_sim_job, avg_analyses)
    # generate_param_plots("prob_mut", init_sim_job, avg_analyses)
    # generate_param_plots("n_agents", init_sim_job, avg_analyses)

    print("plots made")


# def filter_strat_phe_0(df: pd.DataFrame, job: SimJob) -> pd.DataFrame:
#     return df[
#         ((df["prob_mut"] == job.config["model"]["prob_mut"]) | (df["prob_mut"] == 0))
#         & (df["n_agents"] == job.config["init"]["n_agents"])
#     ]


# def filter_prob_mut(df: pd.DataFrame, job: SimJob) -> pd.DataFrame:
#     return df[
#         (df["sim_type"] == SimType.RANDOM)
#         & (df["n_agents"] == job.config["init"]["n_agents"])
#     ]


# def filter_n_agents(df: pd.DataFrame, job: SimJob) -> pd.DataFrame:
#     return df[
#         (df["sim_type"] == SimType.RANDOM)
#         & (df["prob_mut"] == job.config["model"]["prob_mut"])
#     ]


# PLOT_SPECS = {
#     "strat_phe_0": {
#         "filter": filter_strat_phe_0,
#         "sim_types": [SimType.FIXED, SimType.EVOL, SimType.RANDOM],
#         "heatmap_side": True,
#         "compute_optima": True,
#     },
#     "prob_mut": {
#         "filter": filter_prob_mut,
#         "sim_types": [SimType.RANDOM],
#         "heatmap_side": False,
#         "compute_optima": False,
#     },
#     "n_agents": {
#         "filter": filter_n_agents,
#         "sim_types": [SimType.RANDOM],
#         "heatmap_side": False,
#         "compute_optima": False,
#     },
# }


# def plot_metric(ax, df, col_x, col_y, sim_type, err_col=None):
#     if sim_type == SimType.RANDOM and col_x != "growth_rate":
#         plot_horizontal_bands(ax, df, (col_y, "mean"), (col_y, "sem"))
#     else:
#         plot_errorbar_with_band(ax, df, col_x, col_y, col_x == "growth_rate", err_col)


# def generate_param_plots(param: str, init_sim_job: SimJob, avg_df: pd.DataFrame):
#     spec = PLOT_SPECS[param]

#     df = spec["filter"](avg_df, init_sim_job)
#     if len(df) < 2:
#         return
#     df = df.sort_values(param)
#     sim_types = df["sim_type"]

#     x = param
#     fig1, ax1 = create_std_fig_for(x, "extinct_rate")
#     fig2, ax2 = create_std_fig_for(x, "growth_rate")
#     fig3, ax3 = create_std_fig_for(x, "avg_strat_phe_0")

#     fig4 = None

#     if spec["heatmap_side"]:
#         fig4, ax4_main, ax4_side, ax4_cbar = create_heatmap_figure(
#             xlabel=COL_TEX_LABELS[x], ylabel="$s(0)$", panels=3
#         )
#     else:
#         fig4, ax4_main, ax4_cbar = create_heatmap_figure(
#             xlabel=COL_TEX_LABELS[x], ylabel="$s(0)$", panels=2
#         )
#         ax4_side = None

#     fig5, ax5 = create_std_fig_for("growth_rate", "extinct_rate")

#     max_growth = None
#     min_extinct = None

#     if spec["compute_optima"]:
#         fixed_df = df[sim_types == SimType.FIXED]
#         if len(fixed_df):
#             max_growth = fixed_df[param][fixed_df[("growth_rate", "mean")].idxmax()]
#             min_extinct = fixed_df[param][fixed_df[("extinct_rate", "mean")].idxmin()]

#     for st in spec["sim_types"]:
#         sub = df[sim_types == st]
#         if len(sub) == 0:
#             continue

#         plot_metric(ax1, sub, x, "extinct_rate", st)
#         plot_metric(ax2, sub, x, "growth_rate", st)
#         plot_metric(ax3, sub, x, "avg_strat_phe_0", st, err_col="std_dev_strat_phe")

#         if st == SimType.EVOL:
#             plot_main_heatmap(fig4, ax4_main, ax4_cbar, sub, x)
#         elif st == SimType.RANDOM and spec["heatmap_side"]:
#             if ax4_side is not None:
#                 plot_side_heatmap(ax4_side, sub)

#         plot_errorbar_with_band(ax5, sub, "growth_rate", "extinct_rate", True, None)

#     if max_growth is not None:
#         ax1.axvline(max_growth, color="gray", ls="-.")
#         ax2.axvline(max_growth, color="gray", ls="-.")
#         ax3.axhline(max_growth, color="gray", ls="-.")
#         ax4_main.axhline(max_growth, color="gray", ls="-.")
#         if ax4_side is not None:
#             ax4_side.axhline(max_growth, color="gray", ls="-.")

#     if min_extinct is not None:
#         ax1.axvline(min_extinct, color="gray", ls=":")
#         ax2.axvline(min_extinct, color="gray", ls=":")
#         ax3.axhline(min_extinct, color="gray", ls=":")
#         ax4_main.axhline(min_extinct, color="gray", ls=":")
#         if ax4_side is not None:
#             ax4_side.axhline(min_extinct, color="gray", ls=":")

#     fig_dir = init_sim_job.base_dir / "plots" / param
#     fig_dir.mkdir(parents=True, exist_ok=True)

#     fig1.savefig(fig_dir / "extinct_rate.pdf")
#     fig2.savefig(fig_dir / "growth_rate.pdf")
#     fig3.savefig(fig_dir / "avg_strat_phe.pdf")
#     fig4.savefig(fig_dir / "dist_strat_phe.pdf")
#     fig5.savefig(fig_dir / "rates.pdf")
