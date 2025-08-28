use anyhow::{Context, Result, bail};
use serde::{Deserialize, Serialize};
use std::{fmt::Debug, fs, ops::RangeBounds, path::Path};

/// Simulation configuration parameters.
#[derive(Debug, PartialEq, Clone, Serialize, Deserialize)]
pub struct Config {
    /// Number of environments.
    pub n_env: usize,
    /// Number of phenotypes.
    pub n_phe: usize,

    /// Environment transition probabilities (matrix `n_env x n_env`).
    pub prob_env: Vec<Vec<f64>>,
    /// Replication probabilities (matrix `n_env x n_phe`).
    pub prob_rep: Vec<Vec<f64>>,
    /// Death probabilities (matrix `n_env x n_phe`).
    pub prob_dec: Vec<Vec<f64>>,

    /// Initial number of agents.
    pub n_agt_init: usize,
    /// Initial probability distribution over phenotypes.
    pub prob_phe_init: Vec<f64>,

    /// Standard deviation of mutation noise.
    pub std_dev_mut: f64,

    /// Number of steps between simulation saves.
    pub steps_per_save: usize,
    /// Number of saves written per file.
    pub saves_per_file: usize,
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
        check_num(self.n_env, 1..100).context("invalid number of environments")?;
        check_num(self.n_phe, 1..100).context("invalid number of phenotypes")?;

        check_mat(&self.prob_env, (self.n_env, self.n_env), true)
            .context("invalid environment probabilities")?;
        check_mat(&self.prob_rep, (self.n_env, self.n_phe), false)
            .context("invalid replicating probabilities")?;
        check_mat(&self.prob_dec, (self.n_env, self.n_phe), false)
            .context("invalid deceased probabilities")?;

        check_num(self.n_agt_init, 1..100_000).context("invalid initial number of agents")?;
        check_vec(&self.prob_phe_init, self.n_phe, true)
            .context("invalid initial probability distribution over phenotypes")?;

        check_num(self.std_dev_mut, 0.0..1.0).context("invalid mutation standard deviation")?;

        check_num(self.steps_per_save, 1..10_000).context("invalid number of steps per save")?;
        check_num(self.saves_per_file, 1..10_000).context("invalid number of saves per file")?;

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

fn check_vec(vec: &[f64], exp_len: usize, prob_vec: bool) -> Result<()> {
    // Ensure vector has expected length.
    let len = vec.len();
    if len != exp_len {
        bail!("vector length must be {exp_len}, but is {len}");
    }
    if !prob_vec {
        return Ok(());
    }
    // For probability vectors: non-negative elements and sums to ~1.0.
    if vec.iter().any(|&ele| ele < 0.0) {
        bail!("vector must have only non-negative elements");
    }
    let sum: f64 = vec.iter().sum();
    let tol = 1e-8;
    if (sum - 1.0).abs() > tol {
        bail!("vector must sum to 1.0 (tolerance: {tol}), but sums to {sum}");
    }
    Ok(())
}

fn check_mat(mat: &[Vec<f64>], exp_dim: (usize, usize), trans_mat: bool) -> Result<()> {
    // Ensure matrix has expected dimensions.
    let exp_n_rows = exp_dim.0;
    let exp_n_cols = exp_dim.1;
    let n_rows = mat.len();
    if n_rows != exp_n_rows {
        bail!("matrix must have {exp_n_rows} rows, but has {n_rows}");
    }
    if mat.iter().any(|row| row.len() != exp_n_cols) {
        bail!("matrix must have {exp_n_cols} columns");
    }
    if !trans_mat {
        return Ok(());
    }
    // For transition matrices: must be square and each row a valid probability vector.
    if exp_n_rows != exp_n_cols {
        bail!("matrix must be square");
    }
    for (i_row, row) in mat.iter().enumerate() {
        check_vec(row, exp_n_cols, true).with_context(|| format!("invalid row {i_row}"))?;
    }
    Ok(())
}
