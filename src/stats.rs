use serde::Serialize;
use std::default::Default;

#[derive(Serialize)]
pub struct Report {
    mean: f64,
    std_dev: f64,
    #[serde(skip_serializing_if = "Option::is_none")]
    sem: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    is_eq: Option<bool>,
}

impl Default for Report {
    fn default() -> Self {
        Self {
            mean: f64::NAN,
            std_dev: f64::NAN,
            sem: None,
            is_eq: None,
        }
    }
}

#[derive(Clone, Default)]
pub struct Accumulator {
    n_vals: usize,
    mean: f64,
    diff_2_sum: f64,
}

impl Accumulator {
    pub fn add(&mut self, val: f64) {
        self.n_vals += 1;

        let diff_a = val - self.mean;
        self.mean += diff_a / self.n_vals as f64;

        let diff_b = val - self.mean;
        self.diff_2_sum += diff_a * diff_b;
    }

    pub fn report(&self) -> Report {
        Report {
            mean: if self.n_vals > 0 { self.mean } else { f64::NAN },
            std_dev: if self.n_vals > 1 {
                (self.diff_2_sum / (self.n_vals as f64 - 1.0)).sqrt()
            } else {
                f64::NAN
            },
            sem: None,
            is_eq: None,
        }
    }
}

#[derive(Default)]
pub struct TimeSeries {
    vals: Vec<f64>,
}

impl TimeSeries {
    pub fn push(&mut self, val: f64) {
        self.vals.push(val);
    }

    pub fn report(&self) -> Report {
        if self.vals.is_empty() {
            return Report::default();
        }

        let opt_eq_idx = compute_opt_eq_idx(&self.vals);
        let eq_time_series = match opt_eq_idx {
            Some(opt_eq_idx) => &self.vals[opt_eq_idx..],
            None => &self.vals,
        };

        Report {
            mean: compute_mean(eq_time_series),
            std_dev: compute_var(eq_time_series).sqrt(),
            sem: Some(compute_sem(eq_time_series)),
            is_eq: Some(opt_eq_idx.is_some()),
        }
    }
}

/// Compute the optimal equilibration index using the marginal standard error rule
fn compute_opt_eq_idx(time_series: &[f64]) -> Option<usize> {
    if time_series.is_empty() {
        return None;
    }

    let n_vals = time_series.len();
    let n_idxs = n_vals.ilog2() + 1;
    let eq_idxs: Vec<_> = (0..n_idxs).map(|idx| n_vals >> (n_idxs - idx)).collect();
    let opt_eq_idx = eq_idxs
        .iter()
        .filter_map(|&eq_idx| {
            let aux_time_series = &time_series[eq_idx..];
            let n_vals = aux_time_series.len();
            if n_vals < 2 {
                return None;
            }
            let var = compute_var(aux_time_series);
            let mse = var * (n_vals - 1) as f64 / (n_vals * n_vals) as f64;
            Some((eq_idx, mse))
        })
        .min_by(|(_, a), (_, b)| a.total_cmp(b))
        .map(|(eq_idx, _)| eq_idx);

    if opt_eq_idx == eq_idxs.last().copied() {
        return None;
    } else {
        return opt_eq_idx;
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

    while n_vals > 1 {
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
            .max_by(|a, b| a.total_cmp(b))
            .unwrap_or(f64::NAN);

        if sem2_est > max_low {
            return sem2_est.sqrt();
        }
    }

    sem2_ests.last().copied().unwrap_or(f64::NAN).sqrt()
}
