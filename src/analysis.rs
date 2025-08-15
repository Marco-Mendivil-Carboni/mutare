use crate::config::Config;
use crate::model::State;
use crate::stats::{Accumulator, TimeSeries};
use anyhow::{Context, Result};
use rmp_serde::{decode, encode};
use std::{
    fs::File,
    io::{BufReader, BufWriter, Write},
    path::Path,
};

pub trait Observable {
    fn update(&mut self, state: &State) -> Result<()>;
    fn write(&self, writer: &mut dyn Write) -> Result<()>;
}

pub struct ProbEnv {
    acc_vec: Vec<Accumulator>,
}

impl ProbEnv {
    pub fn new(cfg: &Config) -> Self {
        let mut acc_vec = Vec::new();
        acc_vec.resize_with(cfg.n_env, Accumulator::new);
        Self { acc_vec }
    }
}

impl Observable for ProbEnv {
    fn update(&mut self, state: &State) -> Result<()> {
        let env = state.env;
        for (i_env, acc) in self.acc_vec.iter_mut().enumerate() {
            acc.add(if i_env == env { 1.0 } else { 0.0 });
        }
        Ok(())
    }

    fn write(&self, writer: &mut dyn Write) -> Result<()> {
        let reports: Vec<_> = self.acc_vec.iter().map(|acc| acc.report()).collect();
        encode::write_named(writer, &("prob_env", reports))?;
        Ok(())
    }
}

pub struct AvgProbPhe {
    acc_vec: Vec<Accumulator>,
}

impl AvgProbPhe {
    pub fn new(cfg: &Config) -> Self {
        let mut acc_vec = Vec::new();
        acc_vec.resize_with(cfg.n_phe, Accumulator::new);
        Self { acc_vec }
    }
}

impl Observable for AvgProbPhe {
    fn update(&mut self, state: &State) -> Result<()> {
        let n_phe = self.acc_vec.len();
        let agt_vec = &state.agt_vec;
        if agt_vec.is_empty() {
            return Ok(());
        }

        let mut prob_phe_sum = vec![0.0; n_phe];
        for agt in agt_vec {
            let prob_phe = agt.prob_phe();
            for (i_phe, &val) in prob_phe.iter().enumerate() {
                prob_phe_sum[i_phe] += val;
            }
        }

        for i_phe in 0..n_phe {
            self.acc_vec[i_phe].add(prob_phe_sum[i_phe] / agt_vec.len() as f64);
        }
        Ok(())
    }

    fn write(&self, writer: &mut dyn Write) -> Result<()> {
        let reports: Vec<_> = self.acc_vec.iter().map(|acc| acc.report()).collect();
        encode::write_named(writer, &("avg_prob_phe", reports))?;
        Ok(())
    }
}

pub struct NAgtDiff {
    time_series: TimeSeries,
}

impl NAgtDiff {
    pub fn new() -> Self {
        Self {
            time_series: TimeSeries::new(),
        }
    }
}

impl Observable for NAgtDiff {
    fn update(&mut self, state: &State) -> Result<()> {
        self.time_series.push(state.n_agt_diff as f64);
        Ok(())
    }

    fn write(&self, writer: &mut dyn Write) -> Result<()> {
        let report = self.time_series.report();
        encode::write_named(writer, &("n_agt_diff", report))?;
        Ok(())
    }
}

pub struct Analyzer {
    cfg: Config,
    obs_vec: Vec<Box<dyn Observable>>,
}

impl Analyzer {
    pub fn new(cfg: Config) -> Self {
        let mut obs_vec: Vec<Box<dyn Observable>> = Vec::new();
        obs_vec.push(Box::new(ProbEnv::new(&cfg)));
        obs_vec.push(Box::new(AvgProbPhe::new(&cfg)));
        obs_vec.push(Box::new(NAgtDiff::new()));
        Self { cfg, obs_vec }
    }

    pub fn add_file<P: AsRef<Path>>(&mut self, file: P) -> Result<()> {
        let file = file.as_ref();
        let file = File::open(file).with_context(|| format!("failed to open {:?}", file))?;
        let mut reader = BufReader::new(file);

        for _ in 0..self.cfg.saves_per_file {
            let state = decode::from_read(&mut reader).context("failed to read state")?;
            for obs in &mut self.obs_vec {
                obs.update(&state).context("failed to update observable")?;
            }
        }
        Ok(())
    }

    pub fn save_results<P: AsRef<Path>>(&self, file: P) -> Result<()> {
        let file = file.as_ref();
        let file = File::create(file).with_context(|| format!("failed to create {:?}", file))?;
        let mut writer = BufWriter::new(file);

        for obs in &self.obs_vec {
            obs.write(&mut writer)
                .context("failed to write observable")?;
        }
        Ok(())
    }
}
