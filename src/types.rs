//! Simulation data types.

use serde::{Deserialize, Serialize};

/// Agent of the simulation.
#[derive(Serialize, Deserialize)]
pub struct Agent {
    /// Phenotype.
    phe: usize,

    /// Phenotypic strategy.
    strat_phe: Vec<f64>,
}

impl Agent {
    /// Create a new agent with a given phenotype and phenotypic strategy.
    pub fn new(phe: usize, strat_phe: Vec<f64>) -> Self {
        Self { phe, strat_phe }
    }

    /// Get the phenotype of the agent.
    pub fn phe(&self) -> usize {
        self.phe
    }

    /// Get the phenotypic strategy of the agent.
    pub fn strat_phe(&self) -> &Vec<f64> {
        &self.strat_phe
    }
}

/// State of the simulation at a certain step.
#[derive(Serialize, Deserialize)]
pub struct State {
    /// Simulation time.
    pub time: f64,

    /// Environment index.
    pub env: usize,

    /// Vector of agents in the simulation.
    pub agents: Vec<Agent>,
}

/// Single simulation event.
pub enum Event {
    /// Agent replication event.
    Replication { agent_idx: usize },

    /// Agent death event.
    Death { agent_idx: usize },

    /// Environment transition event.
    EnvTrans { next_env: usize },
}

/// Collection of simulation observables.
#[derive(Serialize, Deserialize)]
pub struct Observables {
    /// Current simulation time.
    pub time: f64,

    /// Time until the next event.
    pub time_step: f64,

    /// Number of agents in the simulation.
    pub n_agents: f64,

    /// Instantaneous population growth rate.
    pub growth_rate: f64,

    /// Number of extinctions so far.
    pub n_extinct: usize,

    /// Average phenotypic strategy.
    pub avg_strat_phe: Vec<f64>,

    /// Standard deviation of the phenotypic strategy.
    pub std_dev_strat_phe: f64,

    /// Distribution of phenotypes.
    pub dist_phe: Vec<f64>,
}
