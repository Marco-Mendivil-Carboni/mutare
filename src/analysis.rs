use crate::config::Config;
use crate::model::State;
use crate::stats::TimeSeries;
use anyhow::{Context, Result};
use rmp_serde::{decode, encode};
use serde_value::{Value, to_value};
use std::{
    collections::HashMap,
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

pub struct TimeSeriesObservable {
    name: &'static str,
    time_series_vec: Vec<TimeSeries>,
    update_fn: Box<dyn Fn(&mut [TimeSeries], &State)>,
}

impl TimeSeriesObservable {
    pub fn new<F>(name: &'static str, n_ts: usize, update_fn: F) -> Self
    where
        F: Fn(&mut [TimeSeries], &State) + 'static,
    {
        Self {
            name,
            time_series_vec: vec![TimeSeries::default(); n_ts],
            update_fn: Box::new(update_fn),
        }
    }
}

impl Observable for TimeSeriesObservable {
    fn update(&mut self, state: &State) {
        (self.update_fn)(&mut self.time_series_vec, state);
    }

    fn report(&self) -> Result<Value> {
        let reports: Vec<_> = self.time_series_vec.iter().map(|ts| ts.report()).collect();
        Ok(to_value(HashMap::from([(self.name, reports)]))?)
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
    /// Create a new `Analyzer` with the given configuration.
    pub fn new(cfg: Config) -> Self {
        let mut obs_vec: Vec<Box<dyn Observable>> = Vec::new();

        // Probability of each environment over time
        obs_vec.push(Box::new(TimeSeriesObservable::new(
            "prob_env",
            cfg.n_env,
            |time_series_vec, state| {
                // Add 1.0 for the current environment, 0.0 for others.
                for (i_env, time_series) in time_series_vec.iter_mut().enumerate() {
                    time_series.push(if i_env == state.env { 1.0 } else { 0.0 });
                }
            },
        )));

        // Average probability distribution over phenotypes across agents
        obs_vec.push(Box::new(TimeSeriesObservable::new(
            "avg_prob_phe",
            cfg.n_phe,
            |time_series_vec, state| {
                // Compute average probability for each phenotype across all agents.
                let mut avg_prob_phe = vec![0.0; time_series_vec.len()];
                for agt in &state.agt_vec {
                    for (sum, &ele) in avg_prob_phe.iter_mut().zip(agt.prob_phe()) {
                        *sum += ele;
                    }
                }
                avg_prob_phe
                    .iter_mut()
                    .for_each(|ele| *ele /= state.agt_vec.len() as f64);

                // Update time series with the averaged probabilities.
                time_series_vec
                    .iter_mut()
                    .zip(avg_prob_phe.iter())
                    .for_each(|(ts, &val)| ts.push(val));
            },
        )));

        // Net change in the number of agents per step
        obs_vec.push(Box::new(TimeSeriesObservable::new(
            "n_agt_diff",
            1,
            |time_series_vec, state| {
                // Record the net change in the number of agents for this step.
                time_series_vec[0].push(state.n_agt_diff as f64);
            },
        )));

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
