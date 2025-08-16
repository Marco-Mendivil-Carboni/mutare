use crate::config::Config;
use crate::model::State;
use crate::stats::{Accumulator, TimeSeries};
use anyhow::{Context, Result};
use ndarray::Array1;
use rmp_serde::{decode, encode};
use std::{
    fs::File,
    io::{BufReader, BufWriter, Write},
    path::Path,
};

pub trait Observable {
    fn update(&mut self, state: &State);
    fn write(&self, writer: &mut dyn Write) -> Result<()>;
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

impl Observable for ProbEnv {
    fn update(&mut self, state: &State) {
        for (i_env, acc) in self.acc_vec.iter_mut().enumerate() {
            acc.add(if i_env == state.env { 1.0 } else { 0.0 });
        }
    }

    fn write(&self, writer: &mut dyn Write) -> Result<()> {
        let reports: Vec<_> = self.acc_vec.iter().map(|acc| acc.report()).collect();
        encode::write_named(writer, &("prob_env", reports))?;
        Ok(())
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

impl Observable for AvgProbPhe {
    fn update(&mut self, state: &State) {
        let mut avg_prob_phe = Array1::zeros(self.acc_vec.len());
        for agt in &state.agt_vec {
            avg_prob_phe += agt.prob_phe();
        }
        avg_prob_phe /= state.agt_vec.len() as f64;

        self.acc_vec
            .iter_mut()
            .zip(avg_prob_phe.iter())
            .for_each(|(acc, &val)| acc.add(val));
    }

    fn write(&self, writer: &mut dyn Write) -> Result<()> {
        let reports: Vec<_> = self.acc_vec.iter().map(|acc| acc.report()).collect();
        encode::write_named(writer, &("avg_prob_phe", reports))?;
        Ok(())
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

impl Observable for NAgtDiff {
    fn update(&mut self, state: &State) {
        self.time_series.push(state.n_agt_diff as f64);
    }

    fn write(&self, writer: &mut dyn Write) -> Result<()> {
        let report = self.time_series.report();
        encode::write_named(writer, &("n_agt_diff", report))?;
        Ok(())
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
        obs_vec.push(Box::new(NAgtDiff::new()));
        Self { cfg, obs_vec }
    }

    pub fn add_file<P: AsRef<Path>>(&mut self, file: P) -> Result<()> {
        let file = file.as_ref();
        let file = File::open(file).with_context(|| format!("failed to open {:?}", file))?;
        let mut reader = BufReader::new(file);

        for _ in 0..self.cfg.saves_per_file {
            let state = decode::from_read(&mut reader).context("failed to read state")?;
            for obs in &mut self.obs_vec {
                obs.update(&state);
            }
        }
        Ok(())
    }

    pub fn save_results<P: AsRef<Path>>(&self, file: P) -> Result<()> {
        let file = file.as_ref();
        let file = File::create(file).with_context(|| format!("failed to create {:?}", file))?;
        let mut writer = BufWriter::new(file);

        for obs in &self.obs_vec {
            obs.write(&mut writer)
                .context("failed to write observable")?;
        }
        Ok(())
    }
}
