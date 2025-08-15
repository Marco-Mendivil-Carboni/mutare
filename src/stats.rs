use serde::{Deserialize, Serialize};

pub struct Accumulator {
    n_vals: usize,
    mean: f64,
    diff_2_sum: f64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AccumulatorReport {
    pub mean: f64,
    pub std_dev: f64,
}

impl Accumulator {
    pub fn new() -> Self {
        Self {
            n_vals: 0,
            mean: 0.0,
            diff_2_sum: 0.0,
        }
    }

    pub fn add(&mut self, val: f64) {
        self.n_vals += 1;

        let diff_a = val - self.mean;
        self.mean += diff_a / self.n_vals as f64;

        let diff_b = val - self.mean;
        self.diff_2_sum += diff_a * diff_b;
    }

    pub fn report(&self) -> AccumulatorReport {
        AccumulatorReport {
            mean: self.mean,
            std_dev: if self.n_vals > 1 {
                (self.diff_2_sum / (self.n_vals as f64 - 1.0)).sqrt()
            } else {
                f64::NAN
            },
        }
    }
}

pub struct TimeSeries {
    vals: Vec<f64>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TimeSeriesReport {
    pub mean: f64,
    pub std_dev: f64,
    pub sem: f64,
    pub is_equil: bool,
}

impl TimeSeries {
    pub fn new() -> Self {
        Self { vals: Vec::new() }
    }

    pub fn push(&mut self, val: f64) {
        self.vals.push(val);
    }

    pub fn report(&self) -> TimeSeriesReport {
        let i_equil = compute_opt_i_equil(&self.vals);
        let equil_time_series = &self.vals[i_equil..];
        TimeSeriesReport {
            mean: compute_mean(equil_time_series),
            std_dev: compute_var(equil_time_series).sqrt(),
            sem: compute_sem(equil_time_series),
            is_equil: i_equil != self.vals.len() / 2,
        }
    }
}

fn compute_mean(time_series: &[f64]) -> f64 {
    if time_series.is_empty() {
        return f64::NAN;
    }
    time_series.iter().sum::<f64>() / time_series.len() as f64
}

fn compute_var(time_series: &[f64]) -> f64 {
    let n_vals = time_series.len();
    if n_vals < 2 {
        return f64::NAN;
    }
    let mean = compute_mean(time_series);
    time_series
        .iter()
        .map(|&val| (val - mean).powi(2))
        .sum::<f64>()
        / (n_vals - 1) as f64
}

/// Compute the standard error of the mean (SEM) using the Flyvbjerg-Petersen blocking method
fn compute_sem(time_series: &[f64]) -> f64 {
    let mut blk_time_series = time_series.to_vec();
    let mut n_vals = blk_time_series.len();
    let mut sem2_ests = Vec::new();
    let mut sem2_errs = Vec::new();

    while n_vals >= 2 {
        let sem2_est = compute_var(&blk_time_series) / n_vals as f64;
        let sem2_err = sem2_est * (2.0 / (n_vals as f64 - 1.0)).sqrt();
        sem2_ests.push(sem2_est);
        sem2_errs.push(sem2_err);

        blk_time_series = blk_time_series
            .chunks_exact(2)
            .map(|pair| (pair[0] + pair[1]) / 2.0)
            .collect();
        n_vals = blk_time_series.len();
    }

    for (idx, &sem2_est) in sem2_ests.iter().enumerate() {
        let max_low = sem2_ests[idx..]
            .iter()
            .zip(sem2_errs[idx..].iter())
            .map(|(s, e)| s - e)
            .fold(f64::NEG_INFINITY, f64::max);

        if sem2_est > max_low {
            return sem2_est.sqrt();
        }
    }

    sem2_ests.last().copied().unwrap_or(f64::NAN).sqrt()
}

/// Compute the optimal equilibration index using the marginal standard error rule
fn compute_opt_i_equil(time_series: &[f64]) -> usize {
    let mut min_mse = f64::INFINITY;
    let mut opt_i_equil = time_series.len() / 2;
    let n_vals = time_series.len();
    let n_idxs = n_vals.ilog2() + 1;
    let i_equils: Vec<_> = (0..n_idxs)
        .map(|idx| n_vals / (2 as usize).pow(n_idxs - idx))
        .collect();

    for i_equil in i_equils {
        let aux_time_series = &time_series[i_equil..];
        let n_vals = aux_time_series.len();

        let var = compute_var(aux_time_series);
        let mse = var * (n_vals - 1) as f64 / n_vals.pow(2) as f64;

        if mse < min_mse {
            min_mse = mse;
            opt_i_equil = i_equil;
        }
    }

    opt_i_equil
}
