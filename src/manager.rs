use crate::analysis::Analyzer;
use crate::config::Config;
use crate::engine::Engine;
use anyhow::{Context, Result, bail};
use glob::glob;
use std::{
    fs,
    path::{Path, PathBuf},
};

pub struct Manager {
    sim_dir: PathBuf,
    cfg: Config,
}

impl Manager {
    pub fn new<P: AsRef<Path>>(sim_dir: P) -> Result<Self> {
        let sim_dir = sim_dir.as_ref().to_path_buf();

        let cfg =
            Config::from_file(sim_dir.join("config.msgpack")).context("failed to construct cfg")?;
        log::info!("{cfg:#?}");

        Ok(Self { sim_dir, cfg })
    }

    pub fn run_simulation(&self, run_idx: Option<usize>) -> Result<()> {
        let (run_idx, file_idx, mut engine) = match run_idx {
            None => {
                let run_idx = self.count_run_dirs().context("failed to count run dirs")?;

                let run_dir = self.run_dir(run_idx);
                fs::create_dir_all(&run_dir)
                    .with_context(|| format!("failed to create {run_dir:?}"))?;
                log::info!("created {run_dir:?}");

                let engine = Engine::generate_initial_condition(self.cfg.clone())
                    .context("failed to generate initial condition")?;

                (run_idx, 0, engine)
            }
            Some(run_idx) => {
                let file_idx = self
                    .count_trajectory_files(run_idx)
                    .context("failed to count trajectory files")?;

                let checkpoint_file = self.checkpoint_file(run_idx);
                let engine = Engine::load_checkpoint(&checkpoint_file)
                    .with_context(|| format!("failed to load {checkpoint_file:?}"))?;
                if engine.cfg() != &self.cfg {
                    bail!("checkpoint config differs from the current config");
                }
                log::info!("loaded {checkpoint_file:?}");

                (run_idx, file_idx, engine)
            }
        };

        engine
            .run_simulation(self.trajectory_file(run_idx, file_idx))
            .context("failed to run simulation")?;

        engine
            .save_checkpoint(self.checkpoint_file(run_idx))
            .context("failed to save checkpoint")?;

        Ok(())
    }

    pub fn run_analysis(&self) -> Result<()> {
        let n_runs = self.count_run_dirs().context("failed to count run dirs")?;
        for run_idx in 0..n_runs {
            let mut analyzer = Analyzer::new(self.cfg.clone());

            let n_files = self
                .count_trajectory_files(run_idx)
                .context("failed to count trajectory files")?;
            for file_idx in 0..n_files {
                analyzer
                    .add_file(self.trajectory_file(run_idx, file_idx))
                    .context("failed to add file")?;
            }

            analyzer
                .save_results(self.results_file(run_idx))
                .context("failed to save results")?;
        }

        Ok(())
    }

    fn count_run_dirs(&self) -> Result<usize> {
        let pattern = self.sim_dir.join("run-*");
        let pattern = pattern.to_str().context("pattern is not valid UTF-8")?;
        let count = glob(pattern)
            .context("failed to glob run dirs")?
            .filter_map(Result::ok)
            .filter(|p| p.is_dir())
            .count();
        Ok(count)
    }

    fn run_dir(&self, run_idx: usize) -> PathBuf {
        self.sim_dir.join(format!("run-{run_idx:04}"))
    }

    fn count_trajectory_files(&self, run_idx: usize) -> Result<usize> {
        let pattern = self.run_dir(run_idx).join("trajectory-*.msgpack");
        let pattern = pattern.to_str().context("pattern is not valid UTF-8")?;
        let count = glob(pattern)
            .context("failed to glob trajectory files")?
            .filter_map(Result::ok)
            .count();
        Ok(count)
    }

    fn checkpoint_file(&self, run_idx: usize) -> PathBuf {
        self.run_dir(run_idx).join("checkpoint.msgpack")
    }

    fn trajectory_file(&self, run_idx: usize, file_idx: usize) -> PathBuf {
        self.run_dir(run_idx)
            .join(format!("trajectory-{file_idx:04}.msgpack"))
    }

    fn results_file(&self, run_idx: usize) -> PathBuf {
        self.run_dir(run_idx).join("results.msgpack")
    }
}
