use crate::utils::{check_mat, check_num};
use anyhow::{Context, Result};
use ndarray::Array2;
use serde::{Deserialize, Serialize};
use std::fmt::Debug;

#[derive(Debug, Serialize, Deserialize)]
pub struct Params {
    pub n_env: usize,
    pub n_phe: usize,

    pub prob_env: Array2<f64>,
    pub prob_rep: Array2<f64>,
    pub prob_dec: Array2<f64>,

    pub n_agt_init: usize,

    pub std_dev_mut: f64,

    pub steps_per_save: usize,
    pub saves_per_file: usize,
}

impl Params {
    pub fn new(par_str: &str) -> Result<Self> {
        let par: Params =
            ron::de::from_str(par_str).context("failed to deserialize Params value from string")?;

        check_num(par.n_env, 1..100).context("invalid number of environments")?;
        check_num(par.n_phe, 1..100).context("invalid number of phenotypes")?;

        check_mat(par.prob_env.view(), (par.n_env, par.n_env), true)
            .context("invalid environment probabilities")?;
        check_mat(par.prob_rep.view(), (par.n_env, par.n_phe), false)
            .context("invalid replicating probabilities")?;
        check_mat(par.prob_dec.view(), (par.n_env, par.n_phe), false)
            .context("invalid deceased probabilities")?;

        check_num(par.n_agt_init, 1..100_000).context("invalid initial number of agents")?;

        check_num(par.std_dev_mut, 0.0..1.0).context("invalid mutation standard deviation")?;

        check_num(par.steps_per_save, 1..10_000).context("invalid number of steps per save")?;
        check_num(par.saves_per_file, 1..10_000).context("invalid number of saves per file")?;

        Ok(par)
    }
}
