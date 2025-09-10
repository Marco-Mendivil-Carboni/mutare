//! Simulation model data types.

use serde::{Deserialize, Serialize};

/// Represents an agent in the simulation.
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

    /// Get the probability distribution associated with the agent.
    pub fn prob_phe(&self) -> &Vec<f64> {
        &self.prob_phe
    }
}

/// Represents the state of the simulation at a given step.
///
/// Contains the current environment and all agents in the simulation,
/// as well as the relative change in the number of agents per step.
#[derive(Serialize, Deserialize)]
pub struct State {
    /// Current environment index.
    pub env: usize,

    /// Vector of agents currently in the simulation.
    pub agt_vec: Vec<Agent>,

    /// Relative change in the number of agents per step.
    pub discrete_growth_rate: f64,
}
