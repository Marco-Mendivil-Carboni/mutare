use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize)]
pub struct Agent {
    phe: usize,

    prob_phe: Vec<f64>,
}

impl Agent {
    pub fn new(phe: usize, prob_phe: Vec<f64>) -> Self {
        Self { phe, prob_phe }
    }

    pub fn phe(&self) -> usize {
        self.phe
    }

    pub fn prob_phe(&self) -> &Vec<f64> {
        &self.prob_phe
    }
}

#[derive(Serialize, Deserialize)]
pub struct State {
    pub env: usize,

    pub agt_vec: Vec<Agent>,

    pub n_agt_diff: i32,
}
