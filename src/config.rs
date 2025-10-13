//! Simulation configuration parameters.

use anyhow::{Context, Result, bail};
use serde::{Deserialize, Serialize};
use std::{fmt::Debug, fs, ops::RangeBounds, path::Path};

/// Simulation configuration parameters.
#[derive(Debug, PartialEq, Clone, Serialize, Deserialize)]
pub struct Config {
    /// Stochastic agent-based model parameters.
    pub model: ModelParams,
    /// State initialization parameters.
    pub init: InitParams,
    /// Output format parameters.
    pub output: OutputParams,
}

/// Stochastic agent-based model parameters.
#[derive(Debug, PartialEq, Clone, Serialize, Deserialize)]
pub struct ModelParams {
    /// Number of environments.
    pub n_env: usize,
    /// Number of phenotypes.
    pub n_phe: usize,

    /// Environment transition probabilities (matrix `n_env x n_env`).
    pub rates_trans_env: Vec<Vec<f64>>,
    /// Replication rates (matrix `n_env x n_phe`).
    pub rates_rep: Vec<Vec<f64>>,
    /// Deceased rates (matrix `n_env x n_phe`).
    pub rates_dec: Vec<Vec<f64>>,

    /// Mutation probability.
    pub prob_mut: f64,
    /// Mutation standard deviation.
    pub std_dev_mut: f64,
}

/// State initialization parameters.
#[derive(Debug, PartialEq, Clone, Serialize, Deserialize)]
pub struct InitParams {
    /// Number of agents.
    pub n_agt: usize,

    /// Phenotypic strategy.
    pub strat_phe: Vec<f64>,
}

/// Output format parameters.
#[derive(Debug, PartialEq, Clone, Serialize, Deserialize)]
pub struct OutputParams {
    /// Number of steps per output file.
    pub steps_per_file: usize,

    /// Number of steps per saved record.
    pub steps_per_save: usize,
}

impl Config {
    /// Load a `Config` from a TOML file.
    ///
    /// Performs validation on all parameters before returning.
    pub fn from_file<P: AsRef<Path>>(file: P) -> Result<Self> {
        let file = file.as_ref();
        let file = fs::read_to_string(file).with_context(|| format!("failed to read {file:?}"))?;

        let config: Config = toml::from_str(&file).context("failed to deserialize config")?;

        config.validate().context("failed to validate config")?;

        Ok(config)
    }

    fn validate(&self) -> Result<()> {
        let model = &self.model;
        let init = &self.init;
        let output = &self.output;

        check_num(model.n_env, 1..=16).context("invalid number of environments")?;
        check_num(model.n_phe, 1..=16).context("invalid number of phenotypes")?;

        check_mat(&model.rates_trans_env, (model.n_env, model.n_env))
            .context("invalid environment transition rates")?;
        check_mat(&model.rates_rep, (model.n_env, model.n_phe))
            .context("invalid replicating rates")?;
        check_mat(&model.rates_dec, (model.n_env, model.n_phe))
            .context("invalid deceased rates")?;

        check_num(model.prob_mut, 0.0..=1.0).context("invalid mutation probability")?;
        check_num(model.std_dev_mut, 0.0..=1.0).context("invalid mutation standard deviation")?;

        check_num(init.n_agt, 1..=16_384).context("invalid number of agents")?;

        check_vec(&init.strat_phe, model.n_phe).context("invalid phenotypic strategy")?;

        check_num(output.steps_per_file, 0..=1_048_576)
            .context("invalid number of steps per output file")?;

        check_num(output.steps_per_save, 256..)
            .context("invalid number of steps per saved record")?;

        Ok(())
    }
}

fn check_num<T, R>(num: T, range: R) -> Result<()>
where
    T: PartialOrd + Debug,
    R: RangeBounds<T> + Debug,
{
    if !range.contains(&num) {
        bail!("number must be in the range {range:?}, but is {num:?}");
    }
    Ok(())
}

fn check_vec(vec: &[f64], exp_len: usize) -> Result<()> {
    let len = vec.len();
    if len != exp_len {
        bail!("vector length must be {exp_len}, but is {len}");
    }
    Ok(())
}

fn check_mat(mat: &[Vec<f64>], exp_shape: (usize, usize)) -> Result<()> {
    let exp_n_rows = exp_shape.0;
    let exp_n_cols = exp_shape.1;
    let n_rows = mat.len();
    if n_rows != exp_n_rows {
        bail!("matrix must have {exp_n_rows} rows, but has {n_rows}");
    }
    if mat.iter().any(|row| row.len() != exp_n_cols) {
        bail!("matrix must have {exp_n_cols} columns");
    }
    Ok(())
}
