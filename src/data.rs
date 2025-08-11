use crate::utils::{check_num, check_vec};
use anyhow::{Context, Result};
use ndarray::Array1;
use postcard::{from_bytes, to_allocvec};
use serde::{Deserialize, Serialize};
use std::io::{Read, Write};

#[derive(Debug, Serialize, Deserialize)]
pub struct AgtData {
    phe: usize,
    prob_phe: Array1<f64>,
}

impl AgtData {
    pub fn new(phe: usize, prob_phe: Array1<f64>, n_phe: usize) -> Result<Self> {
        check_num(phe, 0..n_phe).context("invalid phenotype")?;
        check_vec(prob_phe.view(), n_phe, true).context("invalid phenotype probabilities")?;
        Ok(Self { phe, prob_phe })
    }

    pub fn phe(&self) -> usize {
        self.phe
    }

    pub fn prob_phe(&self) -> &Array1<f64> {
        &self.prob_phe
    }
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SimData {
    pub env: usize,
    pub agt_vec: Vec<AgtData>,
    pub n_agt_diff: i32,
}

impl SimData {
    pub fn new(env: usize, n_agt_init: usize) -> Self {
        Self {
            env,
            agt_vec: Vec::with_capacity(n_agt_init),
            n_agt_diff: 0,
        }
    }

    pub fn read_frame<R: Read>(reader: &mut R) -> Result<Self> {
        let mut len_bytes = [0u8; size_of::<u32>()];
        reader
            .read_exact(&mut len_bytes)
            .context("failed to read length prefix")?;

        let len = u32::from_le_bytes(len_bytes);

        let mut sim_data_bytes = vec![0u8; len as usize];
        reader
            .read_exact(&mut sim_data_bytes)
            .context("failed to read SimData bytes")?;

        from_bytes(&sim_data_bytes).context("failed to deserialize SimData value from bytes")
    }

    pub fn write_frame<W: Write>(&self, writer: &mut W) -> Result<()> {
        let sim_data_bytes =
            to_allocvec(self).context("failed to serialize SimData value to bytes")?;

        let len = sim_data_bytes.len() as u32;

        writer
            .write_all(&len.to_le_bytes())
            .context("failed to write length prefix")?;

        writer
            .write_all(&sim_data_bytes)
            .context("failed to write SimData bytes")?;

        Ok(())
    }
}
