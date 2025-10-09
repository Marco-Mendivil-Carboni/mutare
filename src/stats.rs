//! Statistical analysis utilities.

/// Compute the arithmetic mean of a slice of values.
pub fn compute_mean(time_series: &[f64]) -> f64 {
    if time_series.is_empty() {
        return f64::NAN;
    }
    time_series.iter().sum::<f64>() / time_series.len() as f64
}
