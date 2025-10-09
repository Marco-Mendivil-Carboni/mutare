//! Simulation engine.

use crate::config::Config;
use crate::types::{Agent, Channels, Event, Record, State};
use anyhow::{Context, Result};
use rand::prelude::*;
use rand_chacha::ChaCha12Rng;
use rand_distr::{Bernoulli, Exp, LogNormal, Uniform, weighted::WeightedIndex};
use rmp_serde::{decode, encode};
use serde::{Deserialize, Serialize};
use std::{
    fs::File,
    io::{BufReader, BufWriter, Write},
    path::Path,
};

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
}

impl Engine {
    /// Create a new `Engine` with the given configuration and a random initial state.
    pub fn new(cfg: Config) -> Result<Self> {
        let mut rng = ChaCha12Rng::try_from_os_rng()?;

        let env_dist = Uniform::new(0, cfg.model.n_env)?;
        let env = env_dist.sample(&mut rng);

        let agents = Engine::generate_random_agents(&cfg, &mut rng)
            .context("failed to generate random agents")?;

        Ok(Self {
            cfg,
            rng,
            step: 0,
            state: State { env, agents },
        })
    }

    /// Perform the simulation and save the output records to a binary file.
    pub fn perform_simulation<P: AsRef<Path>>(&mut self, file: P) -> Result<()> {
        let file = file.as_ref();
        let file = File::create(file).with_context(|| format!("failed to create {file:?}"))?;
        let mut writer = BufWriter::new(file);

        let mut channels = Channels::default();

        for i_step in 0..self.cfg.output.steps_per_file {
            if i_step % (self.cfg.output.steps_per_file / 100).max(1) == 0 {
                let progress = 100.0 * i_step as f64 / self.cfg.output.steps_per_file as f64;
                log::info!("completed {progress:06.2}%");
            }

            let record = self
                .perform_step(&mut channels)
                .context("failed to perform step")?;

            encode::write(&mut writer, &record).context("failed to serialize record")?;
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

    fn update_channels(&self, channels: &mut Channels) {
        channels.clear();

        for (next_env, &rate) in self.cfg.model.rates_trans_env[self.state.env]
            .iter()
            .enumerate()
        {
            if next_env != self.state.env {
                channels.push(Event::EnvTrans { next_env }, rate);
            }
        }

        for (i, agt) in self.state.agents.iter().enumerate() {
            let phe = agt.phe();
            channels.push(
                Event::Replication { agent_idx: i },
                self.cfg.model.rates_rep[self.state.env][phe],
            );
            channels.push(
                Event::Death { agent_idx: i },
                self.cfg.model.rates_dec[self.state.env][phe],
            );
        }
    }

    /// Perform a single simulation step and return a `Record`.
    fn perform_step(&mut self, channels: &mut Channels) -> Result<Record> {
        let prev_n_agents = self.state.agents.len();

        // Select event
        self.update_channels(channels);
        let event_dist = WeightedIndex::new(channels.rates())?;
        let total_rate = event_dist.total_weight();
        let event = &channels.events()[event_dist.sample(&mut self.rng)];

        match *event {
            Event::EnvTrans { next_env } => {
                self.state.env = next_env;
            }
            Event::Replication { agent_idx } => {
                self.replicate_agent(agent_idx).context("...")?;
            }
            Event::Death { agent_idx } => {
                self.state.agents.swap_remove(agent_idx);
            }
        }

        // Time increment
        let dt = Exp::new(total_rate)?.sample(&mut self.rng);

        // Compute the relative change in the number of agents at this step.
        let growth_rate = match event {
            Event::EnvTrans { next_env: _ } => 0.0,
            Event::Replication { agent_idx: _ } => 1.0,
            Event::Death { agent_idx: _ } => -1.0,
        } / (prev_n_agents as f64);

        // Determine if population reached extinction at this step.
        let extinction_rate = if self.state.agents.is_empty() {
            1.0
        } else {
            0.0
        };

        self.normalize_population()
            .context("failed to normalize population size")?;

        let record = Record {
            time_step: dt,
            growth_rate,
            extinction_rate,
            state: self.cfg.output.steps_per_save.and_then(|steps_per_save| {
                if self.step % steps_per_save == 0 {
                    Some(self.state.clone())
                } else {
                    None
                }
            }),
        };

        // Increment simulation step.
        self.step += 1;

        Ok(record)
    }

    fn replicate_agent(&mut self, agent_idx: usize) -> Result<()> {
        let parent = &self.state.agents[agent_idx];
        let strat_phe = parent.strat_phe().clone();
        let phe_dist = WeightedIndex::new(&strat_phe)?;
        let phe_new = phe_dist.sample(&mut self.rng);
        let mut strat_phe_new = strat_phe.clone();

        // Mutation
        let mut_dist = Bernoulli::new(self.cfg.model.prob_mut)?;
        let ele_mut_dist = LogNormal::new(0.0, self.cfg.model.std_dev_mut)?;
        if mut_dist.sample(&mut self.rng) {
            strat_phe_new = strat_phe_new
                .iter()
                .map(|ele| ele * ele_mut_dist.sample(&mut self.rng))
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
