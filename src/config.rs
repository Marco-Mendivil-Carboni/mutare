use anyhow::{Context, Result, bail};
use ndarray::{Array2, ArrayView1, ArrayView2};
// use rmp_serde::decode;
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

        check_mat(self.prob_env_arr().view(), (self.n_env, self.n_env), true)
            .context("invalid environment probabilities")?;
        check_mat(self.prob_rep_arr().view(), (self.n_env, self.n_phe), false)
            .context("invalid replicating probabilities")?;
        check_mat(self.prob_dec_arr().view(), (self.n_env, self.n_phe), false)
            .context("invalid deceased probabilities")?;

        check_num(self.n_agt_init, 1..100_000).context("invalid initial number of agents")?;
        check_num(self.std_dev_mut, 0.0..1.0).context("invalid mutation standard deviation")?;
        check_num(self.steps_per_save, 1..10_000).context("invalid number of steps per save")?;
        check_num(self.saves_per_file, 1..10_000).context("invalid number of saves per file")?;

        Ok(())
    }

    fn vecvec_to_array2(vec: &Vec<Vec<f64>>) -> Array2<f64> {
        let nrows = vec.len();
        let ncols = vec[0].len();
        let flat: Vec<f64> = vec.iter().flat_map(|row| row.iter().cloned()).collect();
        Array2::from_shape_vec((nrows, ncols), flat).expect("All rows must have same length") // TEMPORARY
    }

    pub fn prob_env_arr(&self) -> Array2<f64> {
        Self::vecvec_to_array2(&self.prob_env) // TEMPORARY
    }

    pub fn prob_rep_arr(&self) -> Array2<f64> {
        Self::vecvec_to_array2(&self.prob_rep) // TEMPORARY
    }

    pub fn prob_dec_arr(&self) -> Array2<f64> {
        Self::vecvec_to_array2(&self.prob_dec) // TEMPORARY
    }
}

fn check_num<T, R>(num: T, range: R) -> Result<()>
where
    T: PartialOrd + Debug,
    R: RangeBounds<T> + Debug,
{
    if !range.contains(&num) {
        bail!("number must be in the range {:?}, but is {:?}", range, num);
    }

    Ok(())
}

fn check_vec(vec: ArrayView1<f64>, exp_len: usize, prob_vec: bool) -> Result<()> {
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
    let sum = vec.sum();
    let tol = 1e-8;
    if (sum - 1.0).abs() > tol {
        bail!("vector must sum to 1.0 (tolerance: {tol}), but sums to {sum}");
    }

    Ok(())
}

fn check_mat(mat: ArrayView2<f64>, exp_dim: (usize, usize), trans_mat: bool) -> Result<()> {
    let dim = mat.dim();
    if dim != exp_dim {
        bail!("matrix shape must be {:?}, but is {:?}", exp_dim, dim);
    }

    if !trans_mat {
        return Ok(());
    }
    if dim.0 != dim.1 {
        bail!("matrix is not square");
    }
    for (i_row, row) in mat.outer_iter().enumerate() {
        check_vec(row, dim.1, true).with_context(|| format!("invalid row {i_row}"))?;
    }

    Ok(())
}
