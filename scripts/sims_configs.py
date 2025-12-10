from pathlib import Path
import numpy as np
from copy import deepcopy

from utils.exec import RunOptions, SimJob, SimsConfig

SIMS_DIR = Path("sims")

symmetric_sim_job = SimJob(
    base_dir=SIMS_DIR / "symmetric",
    config={
        "model": {
            "n_env": 2,
            "n_phe": 2,
            "rates_trans": [
                [-1.0, 1.0],
                [1.0, -1.0],
            ],
            "rates_birth": [
                [1.2, 0.0],
                [0.0, 0.8],
            ],
            "rates_death": [
                [0.0, 1.0],
                [1.0, 0.0],
            ],
            "prob_mut": 0.001,
        },
        "init": {"n_agents": 100},
        "output": {
            "steps_per_file": 1_048_576,
            "steps_per_save": 1_024,
            "hist_bins": 16,
        },
    },
    run_options=RunOptions(n_runs=16, n_files=64),
)
strat_phe_0_values = np.linspace(start=1 / 16, stop=15 / 16, num=15).tolist()
prob_mut_values = np.logspace(start=-8, stop=0, num=17).tolist()
n_agents_values = np.logspace(start=1.5, stop=3.5, num=9).round().astype(int).tolist()

symmetric_sims_config = SimsConfig(
    init_sim_job=symmetric_sim_job,
    strat_phe_0_values=strat_phe_0_values,
    prob_mut_values=prob_mut_values,
    n_agents_values=n_agents_values,
)

asymmetric_sim_job = deepcopy(symmetric_sim_job)
asymmetric_sim_job.base_dir = SIMS_DIR / "asymmetric"
asymmetric_sim_job.config["model"]["rates_birth"] = [
    [1.0, 0.2],
    [0.0, 0.0],
]
asymmetric_sim_job.config["model"]["rates_death"] = [
    [0.0, 0.0],
    [1.0, 0.1],
]

asymmetric_sims_config = SimsConfig(
    init_sim_job=asymmetric_sim_job,
    strat_phe_0_values=strat_phe_0_values,
    prob_mut_values=prob_mut_values,
    n_agents_values=n_agents_values,
)

extended_sim_job = deepcopy(asymmetric_sim_job)
extended_sim_job.base_dir = SIMS_DIR / "extended"
extended_sim_job.config["init"]["n_agents"] = 1000

extended_sims_config = SimsConfig(
    init_sim_job=extended_sim_job,
    strat_phe_0_values=strat_phe_0_values,
    prob_mut_values=[],
    n_agents_values=[],
)

ALL_CONFIGS = [
    symmetric_sims_config,
    asymmetric_sims_config,
    extended_sims_config,
]
