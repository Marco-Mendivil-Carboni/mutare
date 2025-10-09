//! Simulation analyzer and observables.

use crate::config::Config;
use crate::stats;
use crate::types::Record;
use anyhow::{Context, Result, bail};
use rmp_serde::{decode, encode};
use serde::Serialize;
use std::{
    collections::HashMap,
    fs::File,
    io::{BufReader, BufWriter},
    path::Path,
};

/// Result of a generic tensor observable.
#[derive(Serialize)]
struct ObservableResult {
    /// Shape of the observable result.
    shape: Vec<usize>,
    /// Flattened vector of summary statistics, stored in row-major order.
    summary_stats_vec: Vec<f64>,
}

/// Trait for generic tensor observables computed from simulation records.
trait Observable {
    /// Return the name of the observable.
    fn name(&self) -> &'static str;

    /// Update the observable from the given simulation record.
    fn update(&mut self, record: &Record);

    /// Return the observable result.
    fn result(&self) -> ObservableResult;
}

/// Generic tensor observable that uses time series.
///
/// Each observable carries a custom `update_fn`, which defines
/// how its time series should be updated from simulation records.
struct TimeSeriesObservable {
    /// Name of the observable.
    name: &'static str,
    /// Shape of the observable.
    shape: Vec<usize>,
    /// Flattened vector of time series, stored in row-major order.
    time_series_vec: Vec<Vec<f64>>,
    /// Function used to update the time series from simulation records.
    update_fn: Box<dyn Fn(&mut [Vec<f64>], &Record)>,
}

impl TimeSeriesObservable {
    /// Create a new `TimeSeriesObservable`.
    fn new<F>(name: &'static str, shape: &[usize], update_fn: F) -> Self
    where
        F: Fn(&mut [Vec<f64>], &Record) + 'static,
    {
        Self {
            name,
            shape: shape.to_vec(),
            time_series_vec: vec![Vec::new(); shape.iter().product()],
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

    fn result(&self) -> ObservableResult {
        ObservableResult {
            shape: self.shape.clone(),
            summary_stats_vec: self
                .time_series_vec
                .iter()
                .map(|ts| stats::compute_mean(ts))
                .collect(),
        }
    }
}

/// Simulation analyzer.
///
/// Computes and manages a set of observables.
pub struct Analyzer {
    /// Simulation configuration parameters.
    cfg: Config,
    /// Vector of observables.
    observables: Vec<Box<TimeSeriesObservable>>,
}

impl Analyzer {
    /// Create a new `Analyzer` with the given configuration.
    pub fn new(cfg: Config) -> Self {
        let mut observables = Vec::new();

        // ...
        observables.push(Box::new(TimeSeriesObservable::new(
            "time_step",
            &[],
            |time_series_vec, record| {
                time_series_vec[0].push(record.time_step);
            },
        )));

        // Relative change in the number of agents per step
        observables.push(Box::new(TimeSeriesObservable::new(
            "growth_rate",
            &[],
            |time_series_vec, record| {
                time_series_vec[0].push(record.growth_rate);
            },
        )));

        // Probability of extinction
        observables.push(Box::new(TimeSeriesObservable::new(
            "extinction_rate",
            &[],
            |time_series_vec, record| {
                time_series_vec[0].push(record.extinction_rate);
            },
        )));

        // Probability of each environment
        observables.push(Box::new(TimeSeriesObservable::new(
            "prob_env",
            &[cfg.model.n_env],
            |time_series_vec, record| {
                if let Some(state) = &record.state {
                    for (i_env, time_series) in time_series_vec.iter_mut().enumerate() {
                        time_series.push(if i_env == state.env { 1.0 } else { 0.0 });
                    }
                }
            },
        )));

        // Average probability distribution over phenotypes across agents
        observables.push(Box::new(TimeSeriesObservable::new(
            "avg_strat_phe",
            &[cfg.model.n_phe],
            |time_series_vec, record| {
                if let Some(state) = &record.state {
                    // Compute average probability for each phenotype across all agents.
                    let mut avg_strat_phe = vec![0.0; time_series_vec.len()];
                    for agt in &state.agents {
                        for (sum, &ele) in avg_strat_phe.iter_mut().zip(agt.strat_phe()) {
                            *sum += ele;
                        }
                    }
                    avg_strat_phe
                        .iter_mut()
                        .for_each(|ele| *ele /= state.agents.len() as f64);

                    // Update time series with the averaged probabilities.
                    time_series_vec
                        .iter_mut()
                        .zip(avg_strat_phe.iter())
                        .for_each(|(ts, &val)| ts.push(val));
                }
            },
        )));

        Self { cfg, observables }
    }

    /// Read simulation output file and update all observables.
    pub fn add_output_file<P: AsRef<Path>>(&mut self, file: P) -> Result<()> {
        let file = file.as_ref();
        let file = File::open(file).with_context(|| format!("failed to open {file:?}"))?;
        let mut reader = BufReader::new(file);

        // Process each record in the file.
        for _ in 0..self.cfg.output.steps_per_file {
            let record = decode::from_read(&mut reader).context("failed to deserialize record")?;
            for obs in &mut self.observables {
                obs.update(&record);
            }
        }

        Ok(())
    }

    /// Save the analysis results to a file.
    pub fn save_results<P: AsRef<Path>>(&self, file: P) -> Result<()> {
        let file = file.as_ref();
        let file = File::create(file).with_context(|| format!("failed to create {file:?}"))?;
        let mut writer = BufWriter::new(file);

        // Collect the name and result of all observables into a HashMap.
        let mut results = HashMap::new();
        for obs in &self.observables {
            println!("{}", obs.name());
            if results.insert(obs.name(), obs.result()).is_some() {
                bail!("names of observables must be unique");
            }
        }

        encode::write_named(&mut writer, &results).context("failed to serialize results")?;

        Ok(())
    }
}

// // Average probability distribution over phenotypes across agents
// observables.push(Observable::new(
//     "std_dev_strat_phe",
//     &[],
//     move |result, record| {
//         if let Some(state) = &record.state {
//             // Compute average probability for each phenotype across all agents.
//             let mut avg_strat_phe = vec![0.0; cfg.model.n_phe];
//             for agt in &state.agents {
//                 for (sum, &ele) in avg_strat_phe.iter_mut().zip(agt.strat_phe()) {
//                     *sum += ele;
//                 }
//             }
//             avg_strat_phe
//                 .iter_mut()
//                 .for_each(|ele| *ele /= state.agents.len() as f64);

//             let mut diff_strat_phe = 0.0;
//             for agt in &state.agents {
//                 let mut diff = 0.0;
//                 for (ele, avg_ele) in agt.strat_phe().iter().zip(&avg_strat_phe) {
//                     diff += (ele - avg_ele).powi(2);
//                 }
//                 diff /= cfg.model.n_phe as f64;
//                 diff_strat_phe += diff;
//             }
//             diff_strat_phe /= state.agents.len() as f64;

//             result.values_vec.push([diff_strat_phe].to_vec());
//         }
//     },
// ));
