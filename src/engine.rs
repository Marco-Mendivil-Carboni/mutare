use crate::config::Config;
use crate::model::{Agent, State};
use anyhow::{Context, Result};
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

#[derive(Serialize, Deserialize)]
pub struct Engine {
    cfg: Config,
    state: State,
    rng: ChaCha12Rng,
}

impl Engine {
    pub fn generate_initial_condition(cfg: Config) -> Result<Self> {
        let mut rng = ChaCha12Rng::try_from_os_rng()?;

        let env_dist = Uniform::new(0, cfg.n_env)?;
        let env = env_dist.sample(&mut rng);

        let mut agt_vec = Vec::with_capacity(cfg.n_agt_init);
        let phe_dist = Uniform::new(0, cfg.n_phe)?;
        for _ in 0..cfg.n_agt_init {
            let phe = phe_dist.sample(&mut rng);
            let prob_phe = vec![1.0 / cfg.n_phe as f64; cfg.n_phe];
            agt_vec.push(Agent::new(phe, prob_phe));
        }

        let state = State {
            env,
            agt_vec,
            n_agt_diff: 0,
        };

        Ok(Self { cfg, state, rng })
    }

    pub fn run_simulation<P: AsRef<Path>>(&mut self, file: P) -> Result<()> {
        let file = file.as_ref();
        let file = File::create(file).with_context(|| format!("failed to create {file:?}"))?;
        let mut writer = BufWriter::new(file);

        let mut i_agt_rep = Vec::with_capacity(self.cfg.n_agt_init);
        let mut i_agt_dec = Vec::with_capacity(self.cfg.n_agt_init);

        const MAX_N_AGT_FACTOR: usize = 2;
        let i_agt_all = (0..MAX_N_AGT_FACTOR * self.cfg.n_agt_init).collect();

        for i_save in 0..self.cfg.saves_per_file {
            for _ in 0..self.cfg.steps_per_save {
                self.perform_step(&mut i_agt_rep, &mut i_agt_dec, &i_agt_all)
                    .context("failed to perform step")?;
            }

            encode::write(&mut writer, &self.state).context("failed to serialize state")?;

            let progress = 100.0 * (i_save + 1) as f64 / self.cfg.saves_per_file as f64;
            log::info!("completed {progress:06.2}%");
        }

        writer.flush().context("failed to flush writer stream")?;

        log::info!("finished simulation");

        Ok(())
    }

    pub fn save_checkpoint<P: AsRef<Path>>(&self, file: P) -> Result<()> {
        let file = file.as_ref();
        let file = File::create(file).with_context(|| format!("failed to create {file:?}"))?;
        let mut writer = BufWriter::new(file);
        encode::write(&mut writer, &self).context("failed to serialize engine")?;
        Ok(())
    }

    pub fn load_checkpoint<P: AsRef<Path>>(file: P) -> Result<Self> {
        let file = file.as_ref();
        let file = File::open(file).with_context(|| format!("failed to open {file:?}"))?;
        let mut reader = BufReader::new(file);
        let engine = decode::from_read(&mut reader).context("failed to deserialize engine")?;
        Ok(engine)
    }

    pub fn cfg(&self) -> &Config {
        &self.cfg
    }

    fn perform_step(
        &mut self,
        i_agt_rep: &mut Vec<usize>,
        i_agt_dec: &mut Vec<usize>,
        i_agt_all: &Vec<usize>,
    ) -> Result<()> {
        self.update_environment()
            .context("failed to update environment")?;

        self.select_rep_and_dec(i_agt_rep, i_agt_dec)
            .context("failed to select replicating and deceased agents")?;

        self.state.n_agt_diff = 0;

        self.replicate_agents(i_agt_rep)
            .context("failed to replicate agents")?;

        self.remove_deceased(i_agt_dec);

        self.remove_excess(i_agt_all);

        Ok(())
    }

    fn update_environment(&mut self) -> Result<()> {
        let env_dist = WeightedIndex::new(&self.cfg.prob_env[self.state.env])?;
        self.state.env = env_dist.sample(&mut self.rng);
        Ok(())
    }

    fn select_rep_and_dec(
        &mut self,
        i_agt_rep: &mut Vec<usize>,
        i_agt_dec: &mut Vec<usize>,
    ) -> Result<()> {
        let mut rep_dist_vec = Vec::with_capacity(self.cfg.n_phe);
        for &prob in &self.cfg.prob_rep[self.state.env] {
            rep_dist_vec.push(Bernoulli::new(prob)?);
        }
        let mut dec_dist_vec = Vec::with_capacity(self.cfg.n_phe);
        for &prob in &self.cfg.prob_dec[self.state.env] {
            dec_dist_vec.push(Bernoulli::new(prob)?);
        }

        i_agt_rep.clear();
        i_agt_dec.clear();

        for (i_agt, agt) in self.state.agt_vec.iter().enumerate() {
            let phe = agt.phe();
            if rep_dist_vec[phe].sample(&mut self.rng) {
                i_agt_rep.push(i_agt);
            }
            if dec_dist_vec[phe].sample(&mut self.rng) {
                i_agt_dec.push(i_agt);
            }
        }
        Ok(())
    }

    fn replicate_agents(&mut self, i_agt_rep: &Vec<usize>) -> Result<()> {
        let mut_dist = LogNormal::new(0.0, self.cfg.std_dev_mut)?;

        for &i_agt in i_agt_rep {
            let prob_phe = self.state.agt_vec[i_agt].prob_phe();

            let phe_dist = WeightedIndex::new(prob_phe)?;
            let phe_new = phe_dist.sample(&mut self.rng);

            let mut prob_phe_new: Vec<_> = prob_phe
                .iter()
                .map(|ele| ele * mut_dist.sample(&mut self.rng))
                .collect();
            let sum: f64 = prob_phe_new.iter().sum();
            prob_phe_new.iter_mut().for_each(|ele| *ele /= sum);

            self.state.agt_vec.push(Agent::new(phe_new, prob_phe_new));

            self.state.n_agt_diff += 1;
        }
        Ok(())
    }

    fn remove_deceased(&mut self, i_agt_dec: &mut Vec<usize>) {
        i_agt_dec.sort_by(|a, b| b.cmp(a));
        for &i_agt in i_agt_dec.iter() {
            self.state.agt_vec.swap_remove(i_agt);
            self.state.n_agt_diff -= 1;
        }
    }

    fn remove_excess(&mut self, i_agt_all: &Vec<usize>) {
        let n_agt = self.state.agt_vec.len();
        if n_agt > self.cfg.n_agt_init {
            let excess = n_agt - self.cfg.n_agt_init;
            let mut i_agt_rm: Vec<_> = i_agt_all[..n_agt]
                .choose_multiple(&mut self.rng, excess)
                .collect();
            i_agt_rm.sort_by(|a, b| b.cmp(a));
            for &i_agt in i_agt_rm {
                self.state.agt_vec.swap_remove(i_agt);
            }
        }
    }
}
