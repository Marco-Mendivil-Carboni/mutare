use crate::config::Config;
use crate::model::State;
use crate::stats::TimeSeries;
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

/// Trait for observables (metrics) computed from the simulation state.
pub trait Observable {
    /// Update the observable with the current simulation state.
    fn update(&mut self, state: &State);

    /// Return the observable's report as a `serde_value::Value`.
    fn report(&self) -> Result<Value>;
}

/// Tracks the probability of each environment over time.
pub struct ProbEnv {
    time_series_vec: Vec<TimeSeries>,
}

impl ProbEnv {
    /// Create a new `ProbEnv` observable from the given configuration.
    pub fn new(cfg: &Config) -> Self {
        let time_series_vec = vec![TimeSeries::default(); cfg.n_env];
        Self { time_series_vec }
    }
}

impl Observable for ProbEnv {
    fn update(&mut self, state: &State) {
        // Add 1.0 for the current environment, 0.0 for others.
        for (i_env, time_series) in self.time_series_vec.iter_mut().enumerate() {
            time_series.push(if i_env == state.env { 1.0 } else { 0.0 });
        }
    }

    fn report(&self) -> Result<Value> {
        let reports: Vec<_> = self.time_series_vec.iter().map(|ts| ts.report()).collect();
        Ok(to_value(HashMap::from([("prob_env", reports)]))?)
    }
}

/// Tracks the average probability distribution over phenotypes across agents.
pub struct AvgProbPhe {
    time_series_vec: Vec<TimeSeries>,
}

impl AvgProbPhe {
    /// Create a new `AvgProbPhe` observable from the given configuration.
    pub fn new(cfg: &Config) -> Self {
        let time_series_vec = vec![TimeSeries::default(); cfg.n_phe];
        Self { time_series_vec }
    }
}

impl Observable for AvgProbPhe {
    fn update(&mut self, state: &State) {
        // Compute average probability for each phenotype across all agents.
        let mut avg_prob_phe = vec![0.0; self.time_series_vec.len()];
        for agt in &state.agt_vec {
            for (sum, &ele) in avg_prob_phe.iter_mut().zip(agt.prob_phe()) {
                *sum += ele;
            }
        }
        avg_prob_phe
            .iter_mut()
            .for_each(|ele| *ele /= state.agt_vec.len() as f64);

        // Update time series with the averaged probabilities.
        self.time_series_vec
            .iter_mut()
            .zip(avg_prob_phe.iter())
            .for_each(|(ts, &val)| ts.push(val));
    }

    fn report(&self) -> Result<Value> {
        let reports: Vec<_> = self.time_series_vec.iter().map(|ts| ts.report()).collect();
        Ok(to_value(HashMap::from([("avg_prob_phe", reports)]))?)
    }
}

/// Tracks the net change in the number of agents per step.
#[derive(Default)]
pub struct NAgtDiff {
    time_series: TimeSeries,
}

impl Observable for NAgtDiff {
    fn update(&mut self, state: &State) {
        // Record the net change in the number of agents for this step.
        self.time_series.push(state.n_agt_diff as f64);
    }

    fn report(&self) -> Result<Value> {
        let report = self.time_series.report();
        Ok(to_value(HashMap::from([("n_agt_diff", report)]))?)
    }
}

/// Simulation analyzer.
///
/// Computes and manages a set of observables (metrics).
pub struct Analyzer {
    cfg: Config,
    obs_vec: Vec<Box<dyn Observable>>,
}

impl Analyzer {
    /// Create a new `Analyzer` with default-initialized observables.
    pub fn new(cfg: Config) -> Self {
        let mut obs_vec: Vec<Box<dyn Observable>> = Vec::new();
        obs_vec.push(Box::new(ProbEnv::new(&cfg)));
        obs_vec.push(Box::new(AvgProbPhe::new(&cfg)));
        obs_vec.push(Box::new(NAgtDiff::default()));
        Self { cfg, obs_vec }
    }

    /// Load simulation states from a file and update all observables.
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

    /// Save reports from all observables to a file.
    pub fn save_reports<P: AsRef<Path>>(&self, file: P) -> Result<()> {
        let file = file.as_ref();
        let file = File::create(file).with_context(|| format!("failed to create {file:?}"))?;
        let mut writer = BufWriter::new(file);

        // Collect reports from all observables.
        let reports: Result<Vec<_>> = self.obs_vec.iter().map(|obs| obs.report()).collect();
        let reports = reports.context("failed to generate reports")?;

        // Serialize reports to file.
        encode::write_named(&mut writer, &reports).context("failed to serialize reports")?;

        Ok(())
    }
}
