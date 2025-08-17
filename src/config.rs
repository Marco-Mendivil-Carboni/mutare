use anyhow::{Context, Result, bail};
use rmp_serde::decode;
use serde::{Deserialize, Serialize};
use std::{fmt::Debug, fs::File, io::BufReader, ops::RangeBounds, path::Path};

#[derive(Debug, PartialEq, Clone, Serialize, Deserialize)]
pub struct Config {
    pub n_env: usize,
    pub n_phe: usize,

    pub prob_env: Vec<Vec<f64>>,
    pub prob_rep: Vec<Vec<f64>>,
    pub prob_dec: Vec<Vec<f64>>,

    pub n_agt_init: usize,

    pub std_dev_mut: f64,

    pub steps_per_save: usize,
    pub saves_per_file: usize,
}

impl Config {
    pub fn from_file<P: AsRef<Path>>(file: P) -> Result<Self> {
        let file = file.as_ref();
        let file = File::open(file).with_context(|| format!("failed to open {:?}", file))?;
        let reader = BufReader::new(file);

        let config: Config =
            serde_json::from_reader(reader).context("failed to deserialize config")?;
        // let config: Config = decode::from_read(reader).context("failed to deserialize config")?;

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
    let len = vec.len();
    if len != exp_len {
        bail!("vector length must be {exp_len}, but is {len}");
    }
    if !prob_vec {
        return Ok(());
    }
    if vec.iter().any(|&ele| ele < 0.0) {
        bail!("vector must have only non-negative elements");
    }
    let sum = vec.iter().sum::<f64>();
    let tol = 1e-8;
    if (sum - 1.0).abs() > tol {
        bail!("vector must sum to 1.0 (tolerance: {tol}), but sums to {sum}");
    }
    Ok(())
}

fn check_mat(mat: &[Vec<f64>], exp_dim: (usize, usize), trans_mat: bool) -> Result<()> {
    let exp_n_rows = exp_dim.0;
    let exp_n_cols = exp_dim.1;
    let n_rows = mat.len();
    if n_rows != exp_n_rows {
        bail!("matrix must have {exp_n_rows} rows, but has {n_rows}");
    }
    for (i_row, row) in mat.iter().enumerate() {
        check_vec(row, exp_n_cols, false).with_context(|| format!("invalid row {i_row}"))?;
    }
    if !trans_mat {
        return Ok(());
    }
    if exp_n_rows != exp_n_cols {
        bail!("matrix must be square");
    }
    for (i_row, row) in mat.iter().enumerate() {
        check_vec(row, exp_n_cols, true).with_context(|| format!("invalid row {i_row}"))?;
    }
    Ok(())
}
