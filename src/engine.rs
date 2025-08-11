use crate::data::{AgtData, SimData};
use crate::params::Params;
use anyhow::{Context, Result};
use ndarray::Array1;
use rand::prelude::*;
use rand_chacha::ChaCha12Rng;
use rand_distr::{Bernoulli, LogNormal, Uniform, weighted::WeightedIndex};
use serde::{Deserialize, Serialize};
use std::{
    fs::OpenOptions,
    io::{BufWriter, Write},
    path::Path,
};

#[derive(Debug, Serialize, Deserialize)]
pub struct SimEng {
    data: SimData,
    par: Params,
    rng: ChaCha12Rng,
}

impl SimEng {
    pub fn new(env: usize, par: Params) -> Result<Self> {
        Ok(Self {
            data: SimData::new(env, par.n_agt_init),
            par,
            rng: ChaCha12Rng::try_from_os_rng()?,
        })
    }

    pub fn generate_initial_condition(&mut self) -> Result<()> {
        let env_dist = Uniform::new(0, self.par.n_env)?;
        self.data.env = env_dist.sample(&mut self.rng);

        self.data.agt_vec.clear();
        self.data.agt_vec.reserve(self.par.n_agt_init);

        let phe_dist = Uniform::new(0, self.par.n_phe)?;
        for _ in 0..self.par.n_agt_init {
            let phe = phe_dist.sample(&mut self.rng);
            let prob_phe = Array1::from_elem(self.par.n_phe, 1.0 / self.par.n_phe as f64);
            self.data.agt_vec.push(
                AgtData::new(phe, prob_phe, self.par.n_phe)
                    .context("failed to create new agent")?,
            );
        }

        Ok(())
    }

    pub fn run_simulation<P: AsRef<Path>>(&mut self, file: P) -> Result<()> {
        let file = file.as_ref();
        let file = OpenOptions::new()
            .write(true)
            .create(true)
            .truncate(true)
            .open(file)
            .with_context(|| format!("failed to open {:?}", file))?;

        let mut writer = BufWriter::new(file);

        let mut i_agt_rep = Vec::with_capacity(self.par.n_agt_init);
        let mut i_agt_dec = Vec::with_capacity(self.par.n_agt_init);

        const MAX_N_AGT_FACTOR: usize = 2;

        let i_agt_all = (0..MAX_N_AGT_FACTOR * self.par.n_agt_init).collect();

        for i_save in 0..self.par.saves_per_file {
            for _ in 0..self.par.steps_per_save {
                self.perform_step(&mut i_agt_rep, &mut i_agt_dec, &i_agt_all)
                    .context("failed to perform step")?;
            }

            self.data
                .write_frame(&mut writer)
                .context("failed to write frame")?;

            let progress = 100.0 * (i_save + 1) as f64 / self.par.saves_per_file as f64;
            log::info!("completed {:06.2}%", progress);
        }

        writer.flush().context("failed to flush writer stream")?;

        log::info!("finished simulation");

        Ok(())
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

        self.data.n_agt_diff = 0;

        self.replicate_agents(i_agt_rep)
            .context("failed to replicate agents")?;

        self.remove_deceased(i_agt_dec);

        self.remove_excess(i_agt_all);

        Ok(())
    }

    fn update_environment(&mut self) -> Result<()> {
        let env_dist = WeightedIndex::new(self.par.prob_env.row(self.data.env))?;
        self.data.env = env_dist.sample(&mut self.rng);
        Ok(())
    }

    fn select_rep_and_dec(
        &mut self,
        i_agt_rep: &mut Vec<usize>,
        i_agt_dec: &mut Vec<usize>,
    ) -> Result<()> {
        let mut rep_dist_vec = Vec::with_capacity(self.par.n_phe);
        for &prob in self.par.prob_rep.row(self.data.env) {
            rep_dist_vec.push(Bernoulli::new(prob)?);
        }
        let mut dec_dist_vec = Vec::with_capacity(self.par.n_phe);
        for &prob in self.par.prob_dec.row(self.data.env) {
            dec_dist_vec.push(Bernoulli::new(prob)?);
        }
        i_agt_rep.clear();
        i_agt_dec.clear();
        for (i_agt, agt) in self.data.agt_vec.iter().enumerate() {
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
        let mut_dist = LogNormal::new(0.0, self.par.std_dev_mut)?;

        for &i_agt in i_agt_rep {
            let prob_phe = self.data.agt_vec[i_agt].prob_phe();

            let phe_dist = WeightedIndex::new(prob_phe)?;
            let phe_new = phe_dist.sample(&mut self.rng);

            let rand_arr =
                Array1::from_shape_fn(self.par.n_phe, |_| mut_dist.sample(&mut self.rng));
            let mut prob_phe_new = prob_phe * rand_arr;
            prob_phe_new /= prob_phe_new.sum();

            self.data.agt_vec.push(
                AgtData::new(phe_new, prob_phe_new, self.par.n_phe)
                    .context("failed to create new agent")?,
            );

            self.data.n_agt_diff += 1;
        }
        Ok(())
    }

    fn remove_deceased(&mut self, i_agt_dec: &mut Vec<usize>) {
        i_agt_dec.sort_by(|a, b| b.cmp(a));
        for &i_agt in i_agt_dec.iter() {
            self.data.agt_vec.swap_remove(i_agt);
            self.data.n_agt_diff -= 1;
        }
    }

    fn remove_excess(&mut self, i_agt_all: &Vec<usize>) {
        let n_agt = self.data.agt_vec.len();
        if n_agt > self.par.n_agt_init {
            let excess = n_agt - self.par.n_agt_init;
            let mut i_agt_rm: Vec<_> = i_agt_all[..n_agt]
                .choose_multiple(&mut self.rng, excess)
                .collect();
            i_agt_rm.sort_by(|a, b| b.cmp(a));
            for &i_agt in i_agt_rm {
                self.data.agt_vec.swap_remove(i_agt);
            }
        }
    }
}
