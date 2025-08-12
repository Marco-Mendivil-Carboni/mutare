pub use average::Moments4 as OnlineStats;

fn mean(time_series: &[f64]) -> f64 {
    if time_series.is_empty() {
        return f64::NAN;
    }
    time_series.iter().sum::<f64>() / time_series.len() as f64
}

fn sample_variance(time_series: &[f64]) -> f64 {
    if time_series.len() < 2 {
        return f64::NAN;
    }
    let mean = mean(time_series);
    time_series
        .iter()
        .map(|&val| (val - mean).powi(2))
        .sum::<f64>()
        / (time_series.len() - 1) as f64
}

/// Compute the standard error of the mean (SEM) using the Flyvbjerg-Petersen blocking method
fn compute_sem(time_series: &[f64]) -> f64 {
    if time_series.len() < 2 {
        return f64::NAN;
    }

    let mut blk_time_series = time_series.to_vec();
    let mut sem_2;
    let mut uppr_lim = f64::NAN;

    loop {
        let var = sample_variance(&blk_time_series);
        let n_vals = blk_time_series.len();

        sem_2 = var / n_vals as f64;

        if uppr_lim.is_nan() || sem_2 > uppr_lim {
            uppr_lim = sem_2 * (1.0 + (2.0 / (n_vals as f64 - 1.0)).sqrt());
        } else {
            break;
        }

        if n_vals < 4 {
            break;
        }

        // blocking transformation: average pairs of adjacent values
        blk_time_series = blk_time_series
            .chunks_exact(2)
            .map(|pair| (pair[0] + pair[1]) / 2.0)
            .collect();
    }

    sem_2.sqrt()
}

/// Compute the thermalization index using the marginal standard error rule
fn compute_i_therm(time_series: &[f64]) -> usize {
    let mut min_mse = f64::INFINITY;
    let mut i_therm = time_series.len() / 2;

    for div in [2, 4, 8, 16, 32, 64].iter() {
        let i_therm_candidate = time_series.len() / div;

        let aux_time_series = &time_series[i_therm_candidate..];
        let n_vals = aux_time_series.len();

        let var = sample_variance(aux_time_series);
        let mse = var * (n_vals as f64 - 1.0) / ((n_vals * n_vals) as f64);

        if mse < min_mse {
            min_mse = mse;
            i_therm = i_therm_candidate;
        }
    }

    i_therm
}
