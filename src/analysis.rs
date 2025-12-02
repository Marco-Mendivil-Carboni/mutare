//! Simulation analysis.

use crate::config::Config;
use crate::types::{Event, Observables, State};
use anyhow::{Context, Result};
use rmp_serde::{decode, encode};
use serde::Serialize;
use std::{
    fs::File,
    io::{BufReader, BufWriter},
    path::Path,
};

/// Calculate simulation observables.
pub fn calc_observables(
    cfg: &Config,
    state: &State,
    event: &Event,
    time_step: f64,
    n_extinct: usize,
) -> Observables {
    let n_phe = cfg.model.n_phe;
    let n_agents = state.agents.len() as f64;

    let growth_rate = match event {
        Event::Replication { .. } => 1.0,
        Event::Death { .. } => -1.0,
        _ => 0.0,
    } / (n_agents * time_step);

    let mut avg_strat_phe = vec![0.0; n_phe];
    for agent in &state.agents {
        for (sum, &ele) in avg_strat_phe.iter_mut().zip(agent.strat_phe()) {
            *sum += ele;
        }
    }
    avg_strat_phe.iter_mut().for_each(|ele| *ele /= n_agents);

    let mut std_dev_strat_phe = 0.0;
    for agent in &state.agents {
        let mut variation = 0.0;
        for (ele, avg_ele) in agent.strat_phe().iter().zip(&avg_strat_phe) {
            variation += (ele - avg_ele).abs();
        }
        variation /= 2.0;
        std_dev_strat_phe += variation * variation;
    }
    std_dev_strat_phe /= n_agents;
    std_dev_strat_phe = std_dev_strat_phe.sqrt();

    let hist_bins = cfg.output.hist_bins;

    let mut dist_strat_phe = vec![vec![0.0; hist_bins]; n_phe];
    for agent in &state.agents {
        for (phe, ele) in agent.strat_phe().iter().enumerate() {
            let bin = ((ele * hist_bins as f64) as usize).min(hist_bins - 1);
            dist_strat_phe[phe][bin] += 1.0;
        }
    }
    dist_strat_phe.iter_mut().for_each(|row| {
        row.iter_mut().for_each(|ele| *ele /= n_agents);
    });

    Observables {
        time: state.time,
        time_step,
        n_agents,
        growth_rate,
        n_extinct,
        avg_strat_phe,
        std_dev_strat_phe,
        dist_strat_phe,
    }
}

/// Simulation analysis results.
#[derive(Serialize)]
pub struct Analysis {
    /// Distribution of the number of agents.
    pub dist_n_agents: Vec<f64>,

    /// Mean population growth rate.
    pub growth_rate: f64,

    /// Total extinction rate.
    pub extinct_rate: f64,

    /// Mean average phenotypic strategy.
    pub avg_strat_phe: Vec<f64>,

    /// Mean standard deviation of the phenotypic strategy.
    pub std_dev_strat_phe: f64,

    /// Mean distribution of phenotypic strategies.
    pub dist_strat_phe: Vec<Vec<f64>>,
}

/// Simulation analyzer.
///
/// Provides methods to read the simulation output files and analyze them.
pub struct Analyzer {
    /// Simulation configuration parameters.
    cfg: Config,
    /// Vector of all the simulation observables.
    all_observables: Vec<Observables>,
}

impl Analyzer {
    /// Create a new `Analyzer` with the given configuration.
    pub fn new(cfg: Config) -> Self {
        Self {
            cfg,
            all_observables: Vec::new(),
        }
    }

    /// Read simulation output file and add it to the analysis.
    pub fn add_output_file<P: AsRef<Path>>(&mut self, file: P) -> Result<()> {
        let file = file.as_ref();
        let file = File::open(file).with_context(|| format!("failed to open {file:?}"))?;
        let mut reader = BufReader::new(file);

        // Read and collect all the observables in the file.
        use decode::Error::InvalidMarkerRead;
        use std::io::ErrorKind::UnexpectedEof;
        loop {
            match decode::from_read(&mut reader) {
                Ok(observables) => self.all_observables.push(observables),
                Err(InvalidMarkerRead(error)) if error.kind() == UnexpectedEof => break,
                Err(error) => return Err(error).context("failed to deserialize observables"),
            }
        }

        Ok(())
    }

    /// Make the analysis and save it to a file.
    pub fn analyze<P: AsRef<Path>>(&self, file: P) -> Result<()> {
        let file = file.as_ref();
        let file = File::create(file).with_context(|| format!("failed to create {file:?}"))?;
        let mut writer = BufWriter::new(file);

        let last_observables = self
            .all_observables
            .last()
            .context("failed to get last observables")?;

        let time_steps = self
            .all_observables
            .iter()
            .map(|obs| obs.time_step)
            .collect::<Vec<_>>();

        let obs_weighted_average = |f: &dyn Fn(&Observables) -> f64| {
            weighted_average(
                &self.all_observables.iter().map(f).collect::<Vec<_>>(),
                &time_steps,
            )
        };

        let analysis = Analysis {
            growth_rate: obs_weighted_average(&|obs| obs.growth_rate),
            dist_n_agents: (0..self.cfg.output.hist_bins)
                .map(|bin| {
                    obs_weighted_average(&|obs| {
                        let obs_bin = ((obs.n_agents / self.cfg.init.n_agents as f64
                            * self.cfg.output.hist_bins as f64)
                            as usize)
                            .min(self.cfg.output.hist_bins - 1);
                        if obs_bin == bin { 1.0 } else { 0.0 }
                    })
                })
                .collect(),
            extinct_rate: last_observables.n_extinct as f64 / last_observables.time,
            avg_strat_phe: (0..self.cfg.model.n_phe)
                .map(|phe| obs_weighted_average(&|obs| obs.avg_strat_phe[phe]))
                .collect(),
            std_dev_strat_phe: obs_weighted_average(&|obs| obs.std_dev_strat_phe),
            dist_strat_phe: (0..self.cfg.model.n_phe)
                .map(|phe| {
                    (0..self.cfg.output.hist_bins)
                        .map(|bin| obs_weighted_average(&|obs| obs.dist_strat_phe[phe][bin]))
                        .collect()
                })
                .collect(),
        };

        encode::write_named(&mut writer, &analysis).context("failed to serialize analysis")?;

        Ok(())
    }
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
