//! Simulation data types.

use serde::{Deserialize, Serialize};

/// Agent of the simulation.
#[derive(Clone, Serialize, Deserialize)]
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

    /// Get the current phenotype of the agent.
    pub fn phe(&self) -> usize {
        self.phe
    }

    /// Get the current phenotypic strategy of the agent.
    pub fn strat_phe(&self) -> &Vec<f64> {
        &self.strat_phe
    }
}

/// State of the simulation at a certain step.
#[derive(Clone, Serialize, Deserialize)]
pub struct State {
    /// Current environment index.
    pub env: usize,

    /// Vector of agents currently in the simulation.
    pub agents: Vec<Agent>,
}

/// Single simulation event.
#[derive(Clone, Serialize, Deserialize)]
pub enum Event {
    /// Agent replication event.
    Replication { agent_idx: usize },

    /// Agent death event.
    Death { agent_idx: usize },

    /// Environment transition event.
    EnvTrans { next_env: usize },
}

/// Record of a single simulation step.
#[derive(Serialize, Deserialize)]
pub struct Record {
    /// Previous number of agents.
    pub prev_n_agents: usize,

    /// Time to the next event.
    pub time_step: f64,

    /// Next simulation event.
    pub event: Event,

    /// Next simulation state.
    pub state: Option<State>,
}
