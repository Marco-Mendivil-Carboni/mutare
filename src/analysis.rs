//! Simulation analyzer and observables.

use crate::config::Config;
use crate::types::{Event, Record, State};
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
    /// Flattened vector of the average of each tensor element.
    average_vec: Vec<f64>,
}

/// Generic tensor observable.
///
/// Each observable carries a custom `update_fn`, which defines
/// how the observable should be updated from simulation records.
struct Observable {
    /// Name of the observable.
    name: &'static str,
    /// Shape of the observable.
    shape: Vec<usize>,
    /// Flattened vector of the values of each tensor element.
    values_vec: Vec<Vec<f64>>,
    /// Function used to update the observable from simulation records.
    update_fn: Box<dyn Fn(&mut [Vec<f64>], &Record)>,
}

impl Observable {
    /// Create a new `Observable`.
    fn new<F>(name: &'static str, shape: &[usize], update_fn: F) -> Self
    where
        F: Fn(&mut [Vec<f64>], &Record) + 'static,
    {
        Self {
            name,
            shape: shape.to_vec(),
            values_vec: vec![Vec::new(); shape.iter().product()],
            update_fn: Box::new(update_fn),
        }
    }

    /// Return the name of the observable.
    fn name(&self) -> &'static str {
        self.name
    }

    /// Update the observable from the given simulation record.
    fn update(&mut self, record: &Record) {
        (self.update_fn)(&mut self.values_vec, record);
    }

    /// Return the observable result.
    fn result(&self) -> ObservableResult {
        ObservableResult {
            shape: self.shape.clone(),
            average_vec: self
                .values_vec
                .iter()
                .map(|values| average(values))
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
    observables: Vec<Observable>,
}

impl Analyzer {
    /// Create a new `Analyzer` with the given configuration.
    pub fn new(cfg: Config) -> Self {
        let mut observables = Vec::new();

        // Time to the next event
        observables.push(Observable::new("time_step", &[], |values_vec, record| {
            values_vec[0].push(record.time_step);
        }));

        // Relative change in the number of agents
        observables.push(Observable::new(
            "rel_diff_n_agents",
            &[],
            |values_vec, record| {
                let rel_diff_n_agents = match record.event {
                    Event::Replication { .. } => 1.0,
                    Event::Death { .. } => -1.0,
                    _ => 0.0,
                } / (record.prev_n_agents as f64);

                values_vec[0].push(rel_diff_n_agents);
            },
        ));

        // Probability of extinction
        observables.push(Observable::new(
            "prob_extinct",
            &[],
            |values_vec, record| {
                let prob_extinct = match record.event {
                    Event::Death { .. } if record.prev_n_agents == 1 => 1.0,
                    _ => 0.0,
                };

                values_vec[0].push(prob_extinct);
            },
        ));

        // Probability of each environment
        observables.push(Observable::new(
            "prob_env",
            &[cfg.model.n_env],
            |values_vec, record| {
                if let Some(state) = &record.state {
                    for (env, values) in values_vec.iter_mut().enumerate() {
                        values.push(if env == state.env { 1.0 } else { 0.0 });
                    }
                }
            },
        ));

        // Average phenotypic strategy across agents
        observables.push(Observable::new(
            "avg_strat_phe",
            &[cfg.model.n_phe],
            |values_vec, record| {
                if let Some(state) = &record.state {
                    let avg_strat_phe = average_strat_phe(state);
                    values_vec
                        .iter_mut()
                        .zip(avg_strat_phe.iter())
                        .for_each(|(values, &value)| values.push(value));
                }
            },
        ));

        // Standard deviation of the phenotypic strategy across agents
        observables.push(Observable::new(
            "std_dev_strat_phe",
            &[],
            |values_vec, record| {
                if let Some(state) = &record.state {
                    let avg_strat_phe = average_strat_phe(state);

                    let mut std_dev_strat_phe = 0.0;
                    for agt in &state.agents {
                        let mut diff_sq = 0.0;
                        for (ele, avg_ele) in agt.strat_phe().iter().zip(&avg_strat_phe) {
                            diff_sq += (ele - avg_ele).powi(2);
                        }
                        diff_sq /= agt.strat_phe().len() as f64;
                        std_dev_strat_phe += diff_sq;
                    }
                    std_dev_strat_phe /= state.agents.len() as f64;
                    std_dev_strat_phe = std_dev_strat_phe.sqrt();

                    values_vec[0].push(std_dev_strat_phe);
                }
            },
        ));

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

/// Compute the arithmetic average of a slice of values.
fn average(values: &[f64]) -> f64 {
    if values.is_empty() {
        return f64::NAN;
    }
    values.iter().sum::<f64>() / values.len() as f64
}

// Compute the average phenotypic strategy across agents.
fn average_strat_phe(state: &State) -> Vec<f64> {
    let mut avg_strat_phe = vec![0.0; state.agents[0].strat_phe().len()];
    for agt in &state.agents {
        for (sum, &ele) in avg_strat_phe.iter_mut().zip(agt.strat_phe()) {
            *sum += ele;
        }
    }
    avg_strat_phe
        .iter_mut()
        .for_each(|ele| *ele /= state.agents.len() as f64);

    avg_strat_phe
}
