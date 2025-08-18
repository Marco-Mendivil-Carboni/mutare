use crate::config::Config;
use crate::model::State;
use crate::stats::{Accumulator, TimeSeries};
use anyhow::{Context, Result};
use rmp_serde::{decode, encode};
use serde_value::{Value, to_value};
use std::{
    collections::HashMap,
    default::Default,
    fs::File,
    io::{BufReader, BufWriter},
    path::Path,
};

pub trait Observable {
    fn update(&mut self, state: &State);
    fn result(&self) -> Result<Value>;
}

pub struct ProbEnv {
    acc_vec: Vec<Accumulator>,
}

impl ProbEnv {
    pub fn new(cfg: &Config) -> Self {
        let acc_vec = vec![Accumulator::default(); cfg.n_env];
        Self { acc_vec }
    }
}

impl Observable for ProbEnv {
    fn update(&mut self, state: &State) {
        for (i_env, acc) in self.acc_vec.iter_mut().enumerate() {
            acc.add(if i_env == state.env { 1.0 } else { 0.0 });
        }
    }

    fn result(&self) -> Result<Value> {
        let reports: Vec<_> = self.acc_vec.iter().map(|acc| acc.report()).collect();
        Ok(to_value(HashMap::from([("prob_env", reports)]))?)
    }
}

pub struct AvgProbPhe {
    acc_vec: Vec<Accumulator>,
}

impl AvgProbPhe {
    pub fn new(cfg: &Config) -> Self {
        let acc_vec = vec![Accumulator::default(); cfg.n_phe];
        Self { acc_vec }
    }
}

impl Observable for AvgProbPhe {
    fn update(&mut self, state: &State) {
        let mut avg_prob_phe = vec![0.0; self.acc_vec.len()];
        for agt in &state.agt_vec {
            for (sum, &ele) in avg_prob_phe.iter_mut().zip(agt.prob_phe()) {
                *sum += ele;
            }
        }
        avg_prob_phe
            .iter_mut()
            .for_each(|ele| *ele /= state.agt_vec.len() as f64);
        self.acc_vec
            .iter_mut()
            .zip(avg_prob_phe.iter())
            .for_each(|(acc, &val)| acc.add(val));
    }

    fn result(&self) -> Result<Value> {
        let reports: Vec<_> = self.acc_vec.iter().map(|acc| acc.report()).collect();
        Ok(to_value(HashMap::from([("avg_prob_phe", reports)]))?)
    }
}

#[derive(Default)]
pub struct NAgtDiff {
    time_series: TimeSeries,
}

impl Observable for NAgtDiff {
    fn update(&mut self, state: &State) {
        self.time_series.push(state.n_agt_diff as f64);
    }

    fn result(&self) -> Result<Value> {
        let report = self.time_series.report();
        Ok(to_value(HashMap::from([("n_agt_diff", report)]))?)
    }
}

pub struct Analyzer {
    cfg: Config,
    obs_vec: Vec<Box<dyn Observable>>,
}

impl Analyzer {
    pub fn new(cfg: Config) -> Self {
        let mut obs_vec: Vec<Box<dyn Observable>> = Vec::new();
        obs_vec.push(Box::new(ProbEnv::new(&cfg)));
        obs_vec.push(Box::new(AvgProbPhe::new(&cfg)));
        obs_vec.push(Box::new(NAgtDiff::default()));
        Self { cfg, obs_vec }
    }

    pub fn add_file<P: AsRef<Path>>(&mut self, file: P) -> Result<()> {
        let file = file.as_ref();
        let file = File::open(file).with_context(|| format!("failed to open {file:?}"))?;
        let mut reader = BufReader::new(file);

        for _ in 0..self.cfg.saves_per_file {
            let state = decode::from_read(&mut reader).context("failed to deserialize state")?;
            for obs in &mut self.obs_vec {
                obs.update(&state);
            }
        }
        Ok(())
    }

    pub fn save_results<P: AsRef<Path>>(&self, file: P) -> Result<()> {
        let file = file.as_ref();
        let file = File::create(file).with_context(|| format!("failed to create {file:?}"))?;
        let mut writer = BufWriter::new(file);

        let results: Result<Vec<_>> = self.obs_vec.iter().map(|obs| obs.result()).collect();
        let results = results.context("failed to generate results")?;

        encode::write_named(&mut writer, &results).context("failed to serialize results")?;

        Ok(())
    }
}
