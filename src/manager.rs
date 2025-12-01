//! Simulation manager.

use crate::analysis::Analyzer;
use crate::config::Config;
use crate::engine::Engine;
use anyhow::{Context, Result};
use std::{
    fs,
    path::{Path, PathBuf},
    time::Instant,
};

/// Simulation manager.
///
/// Manages the production and analysis of simulation runs.
pub struct Manager {
    /// Path to the simulation directory.
    sim_dir: PathBuf,
    /// Simulation configuration parameters.
    cfg: Config,
}

impl Manager {
    /// Create a new simulation manager for a given simulation directory.
    ///
    /// Expects a `config.toml` file inside this directory.
    pub fn new<P: AsRef<Path>>(sim_dir: P) -> Result<Self> {
        let sim_dir = sim_dir.as_ref().to_path_buf();

        let cfg = Config::from_file(sim_dir.join("config.toml")).context("failed to load cfg")?;
        log::info!("{cfg:#?}");

        Ok(Self { sim_dir, cfg })
    }

    /// Create a new simulation run directory and initialize the engine.
    pub fn create_run(&self) -> Result<()> {
        let run_idx = self.count_run_dirs().context("failed to count run dirs")?;

        let run_dir = self.run_dir(run_idx);
        fs::create_dir_all(&run_dir).with_context(|| format!("failed to create {run_dir:?}"))?;
        log::info!("created {run_dir:?}");

        let engine = Engine::new(self.cfg.clone()).context("failed to create engine")?;

        engine
            .save_checkpoint(self.checkpoint_file(run_idx))
            .context("failed to save checkpoint")?;

        Ok(())
    }

    /// Resume a simulation run from its checkpoint and generate a new output file.
    pub fn resume_run(&self, run_idx: usize) -> Result<()> {
        let file_idx = self
            .count_output_files(run_idx)
            .context("failed to count output files")?;

        let checkpoint_file = self.checkpoint_file(run_idx);
        let mut engine = Engine::load_checkpoint(&checkpoint_file)
            .with_context(|| format!("failed to load {checkpoint_file:?}"))?;
        log::info!("loaded {checkpoint_file:?}");

        let start = Instant::now();
        engine
            .perform_simulation(self.output_file(run_idx, file_idx))
            .context("failed to perform simulation")?;
        let duration = start.elapsed();
        log::info!("finished simulation in {duration:?}");

        engine
            .save_checkpoint(self.checkpoint_file(run_idx))
            .context("failed to save checkpoint")?;

        Ok(())
    }

    /// Analyze all output files from all simulation runs and save the analysis.
    pub fn analyze_sim(&self) -> Result<()> {
        let n_runs = self.count_run_dirs().context("failed to count run dirs")?;
        for run_idx in 0..n_runs {
            let mut analyzer = Analyzer::new(self.cfg.clone());

            let n_files = self
                .count_output_files(run_idx)
                .context("failed to count output files")?;
            for file_idx in 0..n_files {
                analyzer
                    .add_output_file(self.output_file(run_idx, file_idx))
                    .context("failed to add output file")?;
            }

            analyzer
                .analyze(self.analysis_file(run_idx))
                .context("failed to save analysis")?;

            let run_dir = self.run_dir(run_idx);
            log::info!("analyzed {run_dir:?}");
        }

        Ok(())
    }

    fn count_run_dirs(&self) -> Result<usize> {
        let pattern = self.sim_dir.join("run-*");
        let pattern = pattern.to_str().context("pattern is not valid UTF-8")?;
        let count = glob::glob(pattern)
            .context("failed to glob run dirs")?
            .filter_map(Result::ok)
            .filter(|p| p.is_dir())
            .count();
        Ok(count)
    }

    fn run_dir(&self, run_idx: usize) -> PathBuf {
        self.sim_dir.join(format!("run-{run_idx:04}"))
    }

    fn count_output_files(&self, run_idx: usize) -> Result<usize> {
        let pattern = self.run_dir(run_idx).join("output-*");
        let pattern = pattern.to_str().context("pattern is not valid UTF-8")?;
        let count = glob::glob(pattern)
            .context("failed to glob output files")?
            .filter_map(Result::ok)
            .count();
        Ok(count)
    }

    fn checkpoint_file(&self, run_idx: usize) -> PathBuf {
        self.run_dir(run_idx).join("checkpoint.msgpack")
    }

    fn output_file(&self, run_idx: usize, file_idx: usize) -> PathBuf {
        self.run_dir(run_idx)
            .join(format!("output-{file_idx:04}.msgpack"))
    }

    fn analysis_file(&self, run_idx: usize) -> PathBuf {
        self.run_dir(run_idx).join("analysis.msgpack")
    }
}
