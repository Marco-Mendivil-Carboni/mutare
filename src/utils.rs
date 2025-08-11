use anyhow::{Context, Result, bail};
use ndarray::{ArrayView1, ArrayView2};
use std::{fmt::Debug, ops::RangeBounds};

pub fn check_num<T, R>(num: T, range: R) -> Result<()>
where
    T: PartialOrd + Debug,
    R: RangeBounds<T> + Debug,
{
    if !range.contains(&num) {
        bail!("number must be in the range {:?}, but is {:?}", range, num);
    }

    Ok(())
}

pub fn check_vec(vec: ArrayView1<f64>, exp_len: usize, prob_vec: bool) -> Result<()> {
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
    let tol = 1e-6;
    if (sum - 1.0).abs() > tol {
        bail!("vector must sum to 1.0 (tolerance: {tol}), but sums to {sum}");
    }

    Ok(())
}

pub fn check_mat(mat: ArrayView2<f64>, exp_dim: (usize, usize), trans_mat: bool) -> Result<()> {
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
