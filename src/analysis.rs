use crate::config::Config;
use crate::model::State;
use crate::stats::{Accumulator, TimeSeries};
use anyhow::{Context, Result};
use rmp_serde::decode;
use std::{
    fs::File,
    io::{BufReader, BufWriter, Write},
    path::Path,
};

pub trait Obs {
    fn update(&mut self, state: &State) -> Result<()>;
    fn write(&self, writer: &mut dyn Write) -> Result<()>;
}

pub struct ProbEnvObs {
    stats_vec: Vec<Accumulator>,
}

impl ProbEnvObs {
    pub fn new(cfg: &Config) -> Self {
        let mut stats_vec = Vec::new();
        stats_vec.resize_with(cfg.n_env, Accumulator::new);
        Self { stats_vec }
    }
}

impl Obs for ProbEnvObs {
    fn update(&mut self, state: &State) -> Result<()> {
        let env = state.env;
        for (i_env, stats) in self.stats_vec.iter_mut().enumerate() {
            stats.add(if i_env == env { 1.0 } else { 0.0 });
        }
        Ok(())
    }

    fn write(&self, writer: &mut dyn Write) -> Result<()> {
        writeln!(writer, "#prob_env:")?;
        for stats in &self.stats_vec {
            writeln!(writer, "{}", stats.report())?;
        }
        Ok(())
    }
}

pub struct AvgProbPheObs {
    stats_vec: Vec<Accumulator>,
}

impl AvgProbPheObs {
    pub fn new(cfg: &Config) -> Self {
        let mut stats_vec = Vec::new();
        stats_vec.resize_with(cfg.n_phe, Accumulator::new);
        Self { stats_vec }
    }
}

impl Obs for AvgProbPheObs {
    fn update(&mut self, state: &State) -> Result<()> {
        let n_phe = self.stats_vec.len();
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
            self.stats_vec[i_phe].add(prob_phe_sum[i_phe] / agt_vec.len() as f64);
        }
        Ok(())
    }

    fn write(&self, writer: &mut dyn Write) -> Result<()> {
        writeln!(writer, "#avg_prob_phe:")?;
        for stats in &self.stats_vec {
            writeln!(writer, "{}", stats.report())?;
        }
        Ok(())
    }
}

pub struct NAgtDiffObs {
    stats: TimeSeries,
}

impl NAgtDiffObs {
    pub fn new() -> Self {
        Self {
            stats: TimeSeries::new(),
        }
    }
}

impl Obs for NAgtDiffObs {
    fn update(&mut self, state: &State) -> Result<()> {
        self.stats.add(state.n_agt_diff as f64);
        Ok(())
    }

    fn write(&self, writer: &mut dyn Write) -> Result<()> {
        writeln!(writer, "#n_agt_diff:")?;
        writeln!(writer, "{}", self.stats.report())?;
        Ok(())
    }
}

pub struct Analyzer {
    cfg: Config,
    obs_ptr_vec: Vec<Box<dyn Obs>>,
}

impl Analyzer {
    pub fn new(cfg: Config) -> Self {
        let mut obs_ptr_vec: Vec<Box<dyn Obs>> = Vec::new();
        obs_ptr_vec.push(Box::new(ProbEnvObs::new(&cfg)));
        obs_ptr_vec.push(Box::new(AvgProbPheObs::new(&cfg)));
        obs_ptr_vec.push(Box::new(NAgtDiffObs::new()));
        Self { cfg, obs_ptr_vec }
    }

    pub fn add_file<P: AsRef<Path>>(&mut self, file: P) -> Result<()> {
        let file = file.as_ref();
        let file = File::open(file).with_context(|| format!("failed to open {:?}", file))?;
        let mut reader = BufReader::new(file);

        for _ in 0..self.cfg.saves_per_file {
            let state = decode::from_read(&mut reader).context("failed to read state")?;
            for obs in &mut self.obs_ptr_vec {
                obs.update(&state).context("failed to update observable")?;
            }
        }
        Ok(())
    }

    pub fn write<P: AsRef<Path>>(&self, file: P) -> Result<()> {
        let file = file.as_ref();
        let file = File::create(file).with_context(|| format!("failed to create {:?}", file))?;
        let mut writer = BufWriter::new(file);

        for obs in &self.obs_ptr_vec {
            obs.write(&mut writer)
                .context("failed to write observable")?;
            writeln!(writer)?;
        }
        Ok(())
    }
}
