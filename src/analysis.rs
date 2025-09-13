//! Simulation analyzer and observables.

use crate::config::Config;
use crate::types::Record;
use crate::stats::{SummaryStats, TimeSeries};
use anyhow::{Context, Result, bail};
use rmp_serde::{decode, encode};
use std::{
    collections::HashMap,
    fs::File,
    io::{BufReader, BufWriter},
    path::Path,
};

/// Trait for observables (metrics) computed from the simulation record.
trait Observable {
    /// Return the name of the observable.
    fn name(&self) -> &'static str;

    /// Update the observable with the current simulation record.
    fn update(&mut self, record: &Record);

    /// Return the observable statistics.
    fn stats(&self) -> Vec<SummaryStats>;
}

/// Generic observable that holds a vector of time series.
///
/// Each observable carries a custom `update_fn`, which defines
/// how its time series should be updated from the simulation record.
struct TimeSeriesObservable {
    name: &'static str,
    time_series_vec: Vec<TimeSeries>,
    update_fn: Box<dyn Fn(&mut [TimeSeries], &Record)>,
}

impl TimeSeriesObservable {
    /// Create a new `TimeSeriesObservable`.
    fn new<F>(name: &'static str, n_ts: usize, update_fn: F) -> Self
    where
        F: Fn(&mut [TimeSeries], &Record) + 'static,
    {
        Self {
            name,
            time_series_vec: vec![TimeSeries::default(); n_ts],
            update_fn: Box::new(update_fn),
        }
    }
}

impl Observable for TimeSeriesObservable {
    fn name(&self) -> &'static str {
        self.name
    }

    fn update(&mut self, record: &Record) {
        (self.update_fn)(&mut self.time_series_vec, record);
    }

    fn stats(&self) -> Vec<SummaryStats> {
        self.time_series_vec.iter().map(|ts| ts.stats()).collect()
    }
}

/// Simulation analyzer.
///
/// Computes and manages a set of observables (metrics).
pub struct Analyzer {
    /// Simulation configuration parameters.
    cfg: Config,
    /// Vector of observables.
    obs_vec: Vec<Box<dyn Observable>>,
}

impl Analyzer {
    /// Create a new `Analyzer` with the given configuration.
    pub fn new(cfg: Config) -> Self {
        let mut obs_vec: Vec<Box<dyn Observable>> = Vec::new();

        // Relative change in the number of agents per step
        obs_vec.push(Box::new(TimeSeriesObservable::new(
            "growth_rate",
            1,
            |time_series_vec, record| {
                time_series_vec[0].push(record.growth_rate);
            },
        )));

        // Probability of extinction
        obs_vec.push(Box::new(TimeSeriesObservable::new(
            "prob_extinct",
            1,
            |time_series_vec, record| {
                time_series_vec[0].push(if record.extinction { 1.0 } else { 0.0 });
            },
        )));

        // Probability of each environment
        obs_vec.push(Box::new(TimeSeriesObservable::new(
            "prob_env",
            cfg.model.n_env,
            |time_series_vec, record| {
                if let Some(state) = &record.state {
                    for (i_env, time_series) in time_series_vec.iter_mut().enumerate() {
                        time_series.push(if i_env == state.env { 1.0 } else { 0.0 });
                    }
                }
            },
        )));

        // Average probability distribution over phenotypes across agents
        obs_vec.push(Box::new(TimeSeriesObservable::new(
            "avg_prob_phe",
            cfg.model.n_phe,
            |time_series_vec, record| {
                if let Some(state) = &record.state {
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
                }
            },
        )));

        Self { cfg, obs_vec }
    }

    /// Read simulation output file and update all observables.
    pub fn add_output_file<P: AsRef<Path>>(&mut self, file: P) -> Result<()> {
        let file = file.as_ref();
        let file = File::open(file).with_context(|| format!("failed to open {file:?}"))?;
        let mut reader = BufReader::new(file);

        // Process each record in the file.
        for _ in 0..self.cfg.output.steps_per_file {
            let state = decode::from_read(&mut reader).context("failed to deserialize record")?;
            for obs in &mut self.obs_vec {
                obs.update(&state);
            }
        }

        Ok(())
    }

    /// Save the analysis results to a file.
    pub fn save_results<P: AsRef<Path>>(&self, file: P) -> Result<()> {
        let file = file.as_ref();
        let file = File::create(file).with_context(|| format!("failed to create {file:?}"))?;
        let mut writer = BufWriter::new(file);

        // Collect the name and statistics of all observables into a HashMap.
        let mut results = HashMap::new();
        for obs in &self.obs_vec {
            if results.insert(obs.name(), obs.stats()).is_some() {
                bail!("names of observables must be unique");
            }
        }

        encode::write_named(&mut writer, &results).context("failed to serialize results")?;

        Ok(())
    }
}
