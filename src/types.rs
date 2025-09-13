//! Simulation data types.

use serde::{Deserialize, Serialize};

/// Agent of the simulation.
///
/// Each agent has a phenotype (`phe`) and a probability distribution over phenotypes (`prob_phe`).
#[derive(Clone, Serialize, Deserialize)]
pub struct Agent {
    phe: usize,
    prob_phe: Vec<f64>,
}

impl Agent {
    /// Create a new agent with a given phenotype and probability distribution.
    pub fn new(phe: usize, prob_phe: Vec<f64>) -> Self {
        Self { phe, prob_phe }
    }

    /// Get the current phenotype of the agent.
    pub fn phe(&self) -> usize {
        self.phe
    }

    /// Get the current probability distribution over phenotypes of the agent.
    pub fn prob_phe(&self) -> &Vec<f64> {
        &self.prob_phe
    }
}

/// State of the simulation at a given step.
///
/// Contains the current environment and all agents in the simulation.
#[derive(Clone, Serialize, Deserialize)]
pub struct State {
    /// Current environment index.
    pub env: usize,

    /// Vector of agents currently in the simulation.
    pub agt_vec: Vec<Agent>,
}

/// Record of the simulation at a single step.
///
/// Contains the current step, growth rate, extinction flag and state (optional).
#[derive(Serialize, Deserialize)]
pub struct Record {
    /// Current simulation step.
    pub step: usize,

    /// Relative change in the number of agents at this step.
    pub growth_rate: f64,

    /// Population reached extinction at this step.
    pub extinction: bool,

    /// Current simulation state.
    pub state: Option<State>,
}
