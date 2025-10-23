//! Simulation analyzer and observables.

use crate::config::Config;
use crate::types::{Event, Observables, State};
use anyhow::{Context, Result};
use rmp_serde::{decode, encode};
use std::{
    fs::File,
    io::{BufReader, BufWriter},
    path::Path,
};

pub fn calc_observables(
    state: &State,
    event: &Event,
    time_step: f64,
    n_extinct: usize,
) -> Observables {
    let growth_rate = match event {
        Event::Replication { .. } => 1.0,
        Event::Death { .. } => -1.0,
        _ => 0.0,
    } / (state.agents.len() as f64 * time_step);

    let mut avg_strat_phe = vec![0.0; state.agents[0].strat_phe().len()];
    for agt in &state.agents {
        for (sum, &ele) in avg_strat_phe.iter_mut().zip(agt.strat_phe()) {
            *sum += ele;
        }
    }
    avg_strat_phe
        .iter_mut()
        .for_each(|ele| *ele /= state.agents.len() as f64);

    let mut std_dev_strat_phe = 0.0;
    for agt in &state.agents {
        let mut variation = 0.0;
        for (ele, avg_ele) in agt.strat_phe().iter().zip(&avg_strat_phe) {
            variation += (ele - avg_ele).abs();
        }
        variation /= 2.0;
        std_dev_strat_phe += variation * variation;
    }
    std_dev_strat_phe /= state.agents.len() as f64;
    std_dev_strat_phe = std_dev_strat_phe.sqrt();

    Observables {
        time: state.time,
        time_step,
        growth_rate,
        n_extinct,
        avg_strat_phe,
        std_dev_strat_phe,
    }
}

/// Simulation analyzer.
///
/// Computes and manages a set of observables.
pub struct Analyzer {
    cfg: Config,
    /// Vector of observables.
    observables_vec: Vec<Observables>,
}

impl Analyzer {
    /// Create a new `Analyzer` with the given configuration.
    pub fn new(cfg: Config) -> Self {
        Self {
            cfg,
            observables_vec: Vec::new(),
        }
    }

    /// Read simulation output file and update all observables.
    pub fn add_output_file<P: AsRef<Path>>(&mut self, file: P) -> Result<()> {
        let file = file.as_ref();
        let file = File::open(file).with_context(|| format!("failed to open {file:?}"))?;
        let mut reader = BufReader::new(file);

        // ... in the file.
        loop {
            match decode::from_read(&mut reader) {
                Ok(observables) => {
                    self.observables_vec.push(observables);
                }
                Err(decode::Error::InvalidMarkerRead(err))
                    if err.kind() == std::io::ErrorKind::UnexpectedEof =>
                {
                    break;
                }
                Err(err) => return Err(err).context("failed to deserialize record"),
            }
        }

        Ok(())
    }

    /// Make the analysis and save it to a file.
    pub fn analyze<P: AsRef<Path>>(&self, file: P) -> Result<()> {
        let file = file.as_ref();
        let file = File::create(file).with_context(|| format!("failed to create {file:?}"))?;
        let mut writer = BufWriter::new(file);

        // ...
        let last = self.observables_vec.last().context("...")?;
        let time_steps: Vec<_> = self
            .observables_vec
            .iter()
            .map(|obs| obs.time_step)
            .collect();
        let growth_rates: Vec<_> = self
            .observables_vec
            .iter()
            .map(|obs| obs.growth_rate)
            .collect();
        let std_dev_strat_phes: Vec<_> = self
            .observables_vec
            .iter()
            .map(|obs| obs.std_dev_strat_phe)
            .collect();

        let analysis = Observables {
            time: last.time,
            time_step: average(&time_steps),
            growth_rate: weighted_average(&growth_rates, &time_steps),
            n_extinct: last.n_extinct,
            avg_strat_phe: (0..self.cfg.model.n_phe)
                .collect::<Vec<_>>()
                .iter()
                .map(|&phe| {
                    weighted_average(
                        &self
                            .observables_vec
                            .iter()
                            .map(|obs| obs.avg_strat_phe[phe])
                            .collect::<Vec<_>>(),
                        &time_steps,
                    )
                })
                .collect(),
            std_dev_strat_phe: weighted_average(&std_dev_strat_phes, &time_steps),
        };

        encode::write_named(&mut writer, &analysis).context("failed to serialize analysis")?;

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

/// Compute the weighted average of a slice of values.
fn weighted_average(values: &[f64], weights: &[f64]) -> f64 {
    if values.is_empty() || values.len() != weights.len() {
        return f64::NAN;
    }

    let weighted_sum: f64 = values.iter().zip(weights.iter()).map(|(v, w)| v * w).sum();
    let total_weight: f64 = weights.iter().sum();

    weighted_sum / total_weight
}
