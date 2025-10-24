//! Simulation engine.

use crate::analysis::calc_observables;
use crate::config::Config;
use crate::types::{Agent, Event, Observables, State};
use anyhow::{Context, Result};
use rand::prelude::*;
use rand_chacha::ChaCha12Rng;
use rand_distr::{Exp, weighted::WeightedIndex};
use rmp_serde::{decode, encode};
use serde::{Deserialize, Serialize};
use std::{
    fs::File,
    io::{BufReader, BufWriter, Write},
    path::Path,
};

/// Collection of all possible events and their associated rates at a certain step.
#[derive(Default)]
pub struct EventPool {
    /// Vector of possible events.
    events: Vec<Event>,
    /// Vector of associated rates.
    rates: Vec<f64>,
}

impl EventPool {
    /// Clear the event pool.
    pub fn clear(&mut self) {
        self.events.clear();
        self.rates.clear();
    }

    /// Add to the pool a new event with its associated rate.
    pub fn push(&mut self, event: Event, rate: f64) {
        self.events.push(event);
        self.rates.push(rate);
    }

    /// Get all events in the pool.
    pub fn events(&self) -> &[Event] {
        &self.events
    }

    /// Get all rates in the pool.
    pub fn rates(&self) -> &[f64] {
        &self.rates
    }
}

/// Simulation engine.
///
/// Holds the configuration, a random number generator and the current step and state.
/// Provides methods to initialize, run, save, and load simulations.
#[derive(Serialize, Deserialize)]
pub struct Engine {
    /// Simulation configuration parameters.
    cfg: Config,
    /// Random number generator.
    rng: ChaCha12Rng,
    /// Current simulation step.
    step: usize,
    /// Current simulation state.
    state: State,
    /// Number of extinctions so far.
    n_extinct: usize,
}

impl Engine {
    /// Create a new `Engine` with the given configuration and a random initial state.
    pub fn new(cfg: Config) -> Result<Self> {
        let mut rng = ChaCha12Rng::try_from_os_rng()?;

        let env = rng.random_range(0..cfg.model.n_env);

        let agents = Engine::generate_random_agents(&cfg, &mut rng)
            .context("failed to generate random agents")?;

        Ok(Self {
            cfg,
            rng,
            step: 0,
            state: State {
                time: 0.0,
                env,
                agents,
            },
            n_extinct: 0,
        })
    }

    /// Perform the simulation and save the simulation observables to a binary file.
    pub fn perform_simulation<P: AsRef<Path>>(&mut self, file: P) -> Result<()> {
        let file = file.as_ref();
        let file = File::create(file).with_context(|| format!("failed to create {file:?}"))?;
        let mut writer = BufWriter::new(file);

        let mut event_pool = EventPool::default();

        for _ in 0..self.cfg.output.steps_per_file {
            let observables = self
                .perform_step(&mut event_pool)
                .context("failed to perform step")?;

            if let Some(observables) = observables {
                encode::write(&mut writer, &observables)
                    .context("failed to serialize observables")?;
            }
        }

        writer.flush().context("failed to flush writer stream")?;

        Ok(())
    }

    /// Save a checkpoint of the entire engine state.
    ///
    /// Can be used to resume the simulation later.
    pub fn save_checkpoint<P: AsRef<Path>>(&self, file: P) -> Result<()> {
        let file = file.as_ref();
        let file = File::create(file).with_context(|| format!("failed to create {file:?}"))?;
        let mut writer = BufWriter::new(file);
        encode::write(&mut writer, &self).context("failed to serialize engine")?;
        Ok(())
    }

    /// Load a previously saved engine checkpoint.
    pub fn load_checkpoint<P: AsRef<Path>>(file: P) -> Result<Self> {
        let file = file.as_ref();
        let file = File::open(file).with_context(|| format!("failed to open {file:?}"))?;
        let mut reader = BufReader::new(file);
        let engine = decode::from_read(&mut reader).context("failed to deserialize engine")?;
        Ok(engine)
    }

    /// Generate random vector of agents.
    fn generate_random_agents(cfg: &Config, rng: &mut ChaCha12Rng) -> Result<Vec<Agent>> {
        let mut agents = Vec::with_capacity(cfg.init.n_agt);
        let phe_dist = WeightedIndex::new(&cfg.init.strat_phe)?;
        for _ in 0..cfg.init.n_agt {
            let phe = phe_dist.sample(rng);
            let prob_phe = cfg.init.strat_phe.clone();
            agents.push(Agent::new(phe, prob_phe));
        }
        Ok(agents)
    }

    /// Perform a single simulation step and optionally return the simulation observables.
    fn perform_step(&mut self, event_pool: &mut EventPool) -> Result<Option<Observables>> {
        // Create event distribution.
        self.update_event_pool(event_pool);
        let event_dist = WeightedIndex::new(event_pool.rates())?;

        // Select next simulation event.
        let event = &event_pool.events()[event_dist.sample(&mut self.rng)];

        // Sample time to the next event.
        let total_rate = event_dist.total_weight();
        let time_step = Exp::new(total_rate)?.sample(&mut self.rng);

        // Calculate simulation observables.
        let observables = (self.step % self.cfg.output.steps_per_save == 0)
            .then(|| calc_observables(&self.state, event, time_step, self.n_extinct));

        // Update simulation state.
        self.state.time += time_step;
        match *event {
            Event::EnvTrans { next_env } => {
                self.state.env = next_env;
            }
            Event::Replication { agent_idx } => {
                self.replicate_agent(agent_idx)
                    .context("failed to replicate agent")?;
            }
            Event::Death { agent_idx } => {
                self.state.agents.swap_remove(agent_idx);
            }
        }

        // Update number of extinctions so far.
        if self.state.agents.len() == 0 {
            self.n_extinct += 1;
        }

        // Normalize population size.
        self.normalize_population()
            .context("failed to normalize population size")?;

        // Increment simulation step.
        self.step += 1;

        Ok(observables)
    }

    /// Update the event pool based on the configuration and current state.
    fn update_event_pool(&self, event_pool: &mut EventPool) {
        event_pool.clear();

        for (next_env, &rate) in self.cfg.model.rates_trans[self.state.env]
            .iter()
            .enumerate()
        {
            if next_env != self.state.env {
                event_pool.push(Event::EnvTrans { next_env }, rate);
            }
        }

        for (agent_idx, agent) in self.state.agents.iter().enumerate() {
            let phe = agent.phe();
            event_pool.push(
                Event::Replication { agent_idx },
                self.cfg.model.rates_birth[self.state.env][phe],
            );
            event_pool.push(
                Event::Death { agent_idx },
                self.cfg.model.rates_death[self.state.env][phe],
            );
        }
    }

    /// Replicate agent: create a new agent with a new phenotype and phenotypic strategy.
    fn replicate_agent(&mut self, agent_idx: usize) -> Result<()> {
        let parent = &self.state.agents[agent_idx];
        let strat_phe = parent.strat_phe().clone();
        let phe_dist = WeightedIndex::new(&strat_phe)?;
        let phe_new = phe_dist.sample(&mut self.rng);
        let mut strat_phe_new = strat_phe.clone();

        if self.rng.random_bool(self.cfg.model.prob_mut) {
            strat_phe_new = (0..self.cfg.model.n_phe)
                .map(|_| self.rng.random_range(0.0..1.0))
                .collect();
            let sum: f64 = strat_phe_new.iter().sum();
            strat_phe_new.iter_mut().for_each(|ele| *ele /= sum);
        }

        self.state.agents.push(Agent::new(phe_new, strat_phe_new));

        Ok(())
    }

    /// Normalize population size.
    fn normalize_population(&mut self) -> Result<()> {
        let n_agt = self.state.agents.len();
        if n_agt == 0 {
            // Extinction: generate a new random vector of agents.
            self.state.agents = Engine::generate_random_agents(&self.cfg, &mut self.rng)
                .context("failed to generate random agents")?;

            return Ok(());
        }

        let diff = n_agt as i32 - self.cfg.init.n_agt as i32;
        if diff > 0 {
            // Too many agents: delete excess agents.
            let excess = diff as usize;

            // Randomly pick excess agents to delete.
            let mut i_agt_del = (0..n_agt).choose_multiple(&mut self.rng, excess);

            // Sort in reverse to safely remove by index.
            i_agt_del.sort_by(|a, b| b.cmp(a));
            for i_agt in i_agt_del {
                self.state.agents.swap_remove(i_agt);
            }
        }

        Ok(())
    }
}
