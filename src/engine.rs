use crate::config::Config;
use crate::model::{Agent, State};
use anyhow::{Context, Result, bail};
use rand::prelude::*;
use rand_chacha::ChaCha12Rng;
use rand_distr::{Bernoulli, LogNormal, Uniform, weighted::WeightedIndex};
use rmp_serde::{decode, encode};
use serde::{Deserialize, Serialize};
use std::{
    fs::File,
    io::{BufReader, BufWriter, Write},
    path::Path,
};

/// Simulation engine.
///
/// Holds the configuration, current state, and random number generator,
/// and provides methods to initialize, run, save, and load simulations.
#[derive(Serialize, Deserialize)]
pub struct Engine {
    cfg: Config,
    state: State,
    rng: ChaCha12Rng,
}

impl Engine {
    /// Create a new `Engine` with the given configuration and a random initial state.
    pub fn generate_initial_condition(cfg: Config) -> Result<Self> {
        let mut rng = ChaCha12Rng::try_from_os_rng()?;

        let env_dist = Uniform::new(0, cfg.model.n_env)?;
        let env = env_dist.sample(&mut rng);

        let mut agt_vec = Vec::with_capacity(cfg.init.n_agt);
        let phe_dist = WeightedIndex::new(&cfg.init.prob_phe)?;
        for _ in 0..cfg.init.n_agt {
            let phe = phe_dist.sample(&mut rng);
            let prob_phe = cfg.init.prob_phe.clone();
            agt_vec.push(Agent::new(phe, prob_phe));
        }

        let state = State {
            env,
            agt_vec,
            n_agt_diff: 0,
        };

        Ok(Self { cfg, state, rng })
    }

    /// Perform the simulation and save the resulting states to a binary file.
    pub fn perform_simulation<P: AsRef<Path>>(&mut self, file: P) -> Result<()> {
        let file = file.as_ref();
        let file = File::create(file).with_context(|| format!("failed to create {file:?}"))?;
        let mut writer = BufWriter::new(file);

        let mut i_agt_rep = Vec::with_capacity(self.cfg.init.n_agt);
        let mut i_agt_dec = Vec::with_capacity(self.cfg.init.n_agt);

        const MAX_N_AGT_FACTOR: usize = 2;
        let i_agt_all = (0..MAX_N_AGT_FACTOR * self.cfg.init.n_agt).collect();

        for i_save in 0..self.cfg.output.saves_per_file {
            for _ in 0..self.cfg.output.steps_per_save {
                self.perform_step(&mut i_agt_rep, &mut i_agt_dec, &i_agt_all)
                    .context("failed to perform step")?;
            }

            encode::write(&mut writer, &self.state).context("failed to serialize state")?;

            let progress = 100.0 * (i_save + 1) as f64 / self.cfg.output.saves_per_file as f64;
            log::info!("completed {progress:06.2}%");
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

    fn perform_step(
        &mut self,
        i_agt_rep: &mut Vec<usize>,
        i_agt_dec: &mut Vec<usize>,
        i_agt_all: &Vec<usize>,
    ) -> Result<()> {
        // Update environment according to transition probabilities.
        self.update_environment()
            .context("failed to update environment")?;

        // Select replicating and deceased agents.
        self.select_rep_and_dec(i_agt_rep, i_agt_dec)
            .context("failed to select replicating and deceased agents")?;

        // Compute the net change in the number of agents.
        self.state.n_agt_diff = i_agt_rep.len() as i32 - i_agt_dec.len() as i32;

        // Replicate selected agents.
        self.replicate_agents(i_agt_rep)
            .context("failed to replicate selected agents")?;

        // Remove deceased agents.
        self.remove_deceased(i_agt_dec);

        // Normalize population size.
        self.normalize_population(i_agt_all)?;

        Ok(())
    }

    fn update_environment(&mut self) -> Result<()> {
        let env_dist = WeightedIndex::new(&self.cfg.model.prob_trans_env[self.state.env])?;
        self.state.env = env_dist.sample(&mut self.rng);
        Ok(())
    }

    fn select_rep_and_dec(
        &mut self,
        i_agt_rep: &mut Vec<usize>,
        i_agt_dec: &mut Vec<usize>,
    ) -> Result<()> {
        let mut rep_dist_vec = Vec::with_capacity(self.cfg.model.n_phe);
        for &prob in &self.cfg.model.prob_rep[self.state.env] {
            rep_dist_vec.push(Bernoulli::new(prob)?);
        }
        let mut dec_dist_vec = Vec::with_capacity(self.cfg.model.n_phe);
        for &prob in &self.cfg.model.prob_dec[self.state.env] {
            dec_dist_vec.push(Bernoulli::new(prob)?);
        }

        i_agt_rep.clear();
        i_agt_dec.clear();

        for (i_agt, agt) in self.state.agt_vec.iter().enumerate() {
            if rep_dist_vec[agt.phe()].sample(&mut self.rng) {
                i_agt_rep.push(i_agt);
            }
            if dec_dist_vec[agt.phe()].sample(&mut self.rng) {
                i_agt_dec.push(i_agt);
            }
        }

        Ok(())
    }

    fn replicate_agents(&mut self, i_agt_rep: &Vec<usize>) -> Result<()> {
        let mut_dist = Bernoulli::new(self.cfg.model.prob_mut)?;
        let ele_mut_dist = LogNormal::new(0.0, self.cfg.model.std_dev_mut)?;

        for &i_agt in i_agt_rep {
            let prob_phe = self.state.agt_vec[i_agt].prob_phe();

            // Sample the offspring's phenotype from the parent's probability distribution.
            let phe_dist = WeightedIndex::new(prob_phe)?;
            let phe_new = phe_dist.sample(&mut self.rng);

            // The offspring inherits the parent's probability distribution by default.
            let mut prob_phe_new = prob_phe.clone();

            // With probability `prob_mut` the offspring's distribution mutates randomly.
            if mut_dist.sample(&mut self.rng) {
                prob_phe_new = prob_phe_new
                    .iter()
                    .map(|ele| ele * ele_mut_dist.sample(&mut self.rng))
                    .collect();
                let sum: f64 = prob_phe_new.iter().sum();
                prob_phe_new.iter_mut().for_each(|ele| *ele /= sum);
            }

            self.state.agt_vec.push(Agent::new(phe_new, prob_phe_new));
        }

        Ok(())
    }

    fn remove_deceased(&mut self, i_agt_dec: &mut Vec<usize>) {
        // Sort in reverse to safely remove by index.
        i_agt_dec.sort_by(|a, b| b.cmp(a));
        for &i_agt in i_agt_dec.iter() {
            self.state.agt_vec.swap_remove(i_agt);
        }
    }

    fn normalize_population(&mut self, i_agt_all: &Vec<usize>) -> Result<()> {
        let n_agt = self.state.agt_vec.len();
        let n_agt_min = 1;
        if n_agt < n_agt_min {
            bail!("number of agents must be at least {n_agt_min}");
        }

        let diff = n_agt as i32 - self.cfg.init.n_agt as i32;
        if diff < 0 {
            // Too few agents: duplicate missing agents.
            let missing = -diff as usize;

            // Randomly pick missing agents to duplicate.
            for _ in 0..missing {
                let &i_agt = i_agt_all[..n_agt]
                    .choose(&mut self.rng)
                    .context("failed to choose an agent to duplicate")?;
                self.state.agt_vec.push(self.state.agt_vec[i_agt].clone());
            }
        } else if diff > 0 {
            // Too many agents: delete excess agents.
            let excess = diff as usize;

            // Randomly pick excess agents to delete.
            let mut i_agt_del: Vec<_> = i_agt_all[..n_agt]
                .choose_multiple(&mut self.rng, excess)
                .collect();

            // Sort in reverse to safely remove by index.
            i_agt_del.sort_by(|a, b| b.cmp(a));
            for &i_agt in i_agt_del {
                self.state.agt_vec.swap_remove(i_agt);
            }
        }

        Ok(())
    }
}
