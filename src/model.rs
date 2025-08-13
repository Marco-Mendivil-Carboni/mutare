use anyhow::{Context, Result};
use ndarray::Array1;
use postcard::{from_bytes, to_allocvec};
use serde::{Deserialize, Serialize};
use std::io::{Read, Write};

#[derive(Debug, Serialize, Deserialize)]
pub struct Agent {
    phe: usize,
    prob_phe: Array1<f64>,
}

impl Agent {
    pub fn new(phe: usize, prob_phe: Array1<f64>) -> Self {
        Self { phe, prob_phe }
    }

    pub fn phe(&self) -> usize {
        self.phe
    }

    pub fn prob_phe(&self) -> &Array1<f64> {
        &self.prob_phe
    }
}

#[derive(Debug, Serialize, Deserialize)]
pub struct State {
    pub env: usize,
    pub agt_vec: Vec<Agent>,
    pub n_agt_diff: i32,
}

impl State {
    pub fn read_frame<R: Read>(reader: &mut R) -> Result<Self> {
        let mut len_bytes = [0u8; size_of::<u32>()];
        reader
            .read_exact(&mut len_bytes)
            .context("failed to read length prefix")?;

        let len = u32::from_le_bytes(len_bytes);

        let mut state_bytes = vec![0u8; len as usize];
        reader
            .read_exact(&mut state_bytes)
            .context("failed to read State value bytes")?;

        from_bytes(&state_bytes).context("failed to deserialize State value from bytes")
    }

    pub fn write_frame<W: Write>(&self, writer: &mut W) -> Result<()> {
        let state_bytes =
            to_allocvec(self).context("failed to serialize State value to bytes")?;

        let len = state_bytes.len() as u32;

        writer
            .write_all(&len.to_le_bytes())
            .context("failed to write length prefix")?;

        writer
            .write_all(&state_bytes)
            .context("failed to write State value bytes")?;

        Ok(())
    }
}
