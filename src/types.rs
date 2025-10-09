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

/// State of the simulation at a certain instant.
#[derive(Clone, Serialize, Deserialize)]
pub struct State {
    /// Current environment index.
    pub env: usize,

    /// Vector of agents currently in the simulation.
    pub agents: Vec<Agent>,
}

/// Record of the simulation at a certain instant.
#[derive(Serialize, Deserialize)]
pub struct Record {
    /// Current simulation time.
    pub time_step: f64,

    /// Instantaneous growth rate.
    pub growth_rate: f64,

    /// Extinction rate.
    pub extinction_rate: f64,

    /// Current simulation state.
    pub state: Option<State>,
}

/// Basic simulation event type.
pub enum Event {
    /// Agent replication event.
    Replication { agent_idx: usize },

    /// Agent death event.
    Death { agent_idx: usize },

    /// Environment transition event.
    EnvTrans { next_env: usize },
}

#[derive(Default)]
pub struct Channels {
    events: Vec<Event>,
    rates: Vec<f64>,
}

impl Channels {
    pub fn clear(&mut self) {
        self.events.clear();
        self.rates.clear();
    }

    pub fn push(&mut self, event: Event, rate: f64) {
        self.events.push(event);
        self.rates.push(rate);
    }

    pub fn events(&self) -> &[Event] {
        &self.events
    }

    pub fn rates(&self) -> &[f64] {
        &self.rates
    }
}
