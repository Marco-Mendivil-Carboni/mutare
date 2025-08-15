use crate::config::Config;
use crate::model::State;
use crate::stats::{Accumulator, TimeSeries};
use anyhow::{Context, Result};
use rmp_serde::decode;
use std::{
    fs::File,
    io::{BufReader, BufWriter},
    path::Path,
};

pub trait Obs {
    fn update(&mut self, state: &State) -> Result<()>;
    fn report(&self) -> serde_json::Value;
}

pub struct ProbEnv {
    acc_vec: Vec<Accumulator>,
}

impl ProbEnv {
    pub fn new(cfg: &Config) -> Self {
        let mut acc_vec = Vec::new();
        acc_vec.resize_with(cfg.n_env, Accumulator::new);
        Self { acc_vec }
    }
}

impl Obs for ProbEnv {
    fn update(&mut self, state: &State) -> Result<()> {
        let env = state.env;
        for (i_env, acc) in self.acc_vec.iter_mut().enumerate() {
            acc.add(if i_env == env { 1.0 } else { 0.0 });
        }
        Ok(())
    }

    fn report(&self) -> serde_json::Value {
        let reports: Vec<_> = self.acc_vec.iter().map(|acc| acc.report()).collect();
        serde_json::json!({ "prob_env": reports })
    }
}

pub struct AvgProbPhe {
    acc_vec: Vec<Accumulator>,
}

impl AvgProbPhe {
    pub fn new(cfg: &Config) -> Self {
        let mut acc_vec = Vec::new();
        acc_vec.resize_with(cfg.n_phe, Accumulator::new);
        Self { acc_vec }
    }
}

impl Obs for AvgProbPhe {
    fn update(&mut self, state: &State) -> Result<()> {
        let n_phe = self.acc_vec.len();
        let agt_vec = &state.agt_vec;
        if agt_vec.is_empty() {
            return Ok(());
        }

        let mut prob_phe_sum = vec![0.0; n_phe];
        for agt in agt_vec {
            let prob_phe = agt.prob_phe();
            for (i_phe, &val) in prob_phe.iter().enumerate() {
                prob_phe_sum[i_phe] += val;
            }
        }

        for i_phe in 0..n_phe {
            self.acc_vec[i_phe].add(prob_phe_sum[i_phe] / agt_vec.len() as f64);
        }
        Ok(())
    }

    fn report(&self) -> serde_json::Value {
        let reports: Vec<_> = self.acc_vec.iter().map(|acc| acc.report()).collect();
        serde_json::json!({ "avg_prob_phe": reports })
    }
}

pub struct NAgtDiff {
    time_series: TimeSeries,
}

impl NAgtDiff {
    pub fn new() -> Self {
        Self {
            time_series: TimeSeries::new(),
        }
    }
}

impl Obs for NAgtDiff {
    fn update(&mut self, state: &State) -> Result<()> {
        self.time_series.push(state.n_agt_diff as f64);
        Ok(())
    }

    fn report(&self) -> serde_json::Value {
        let report = self.time_series.report();
        serde_json::json!({ "n_agt_diff": report })
    }
}

pub struct Analyzer {
    cfg: Config,
    obs_ptr_vec: Vec<Box<dyn Obs>>,
}

impl Analyzer {
    pub fn new(cfg: Config) -> Self {
        let mut obs_ptr_vec: Vec<Box<dyn Obs>> = Vec::new();
        obs_ptr_vec.push(Box::new(ProbEnv::new(&cfg)));
        obs_ptr_vec.push(Box::new(AvgProbPhe::new(&cfg)));
        obs_ptr_vec.push(Box::new(NAgtDiff::new()));
        Self { cfg, obs_ptr_vec }
    }

    pub fn add_file<P: AsRef<Path>>(&mut self, file: P) -> Result<()> {
        let file = file.as_ref();
        let file = File::open(file).with_context(|| format!("failed to open {:?}", file))?;
        let mut reader = BufReader::new(file);

        for _ in 0..self.cfg.saves_per_file {
            let state = decode::from_read(&mut reader).context("failed to read state")?;
            for obs in &mut self.obs_ptr_vec {
                obs.update(&state).context("failed to update observable")?;
            }
        }
        Ok(())
    }

    pub fn save_results<P: AsRef<Path>>(&self, file: P) -> Result<()> {
        let file = file.as_ref();
        let file = File::create(file).with_context(|| format!("failed to create {:?}", file))?;
        let writer = BufWriter::new(file);

        let reports: Vec<_> = self.obs_ptr_vec.iter().map(|obs| obs.report()).collect();
        serde_json::to_writer_pretty(writer, &reports)?;
        Ok(())
    }
}
