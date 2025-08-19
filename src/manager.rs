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
            Config::from_file(sim_dir.join("config.bin")).context("failed to create config")?;

        log::info!("{cfg:#?}");

        Ok(Self { sim_dir, cfg })
    }

    pub fn run_simulation(&self, run_idx: Option<usize>) -> Result<()> {
        let (run_idx, file_idx, mut engine) = match run_idx {
            None => {
                let run_idx = self.count_runs().context("...")?;
                fs::create_dir_all(&self.run_dir(run_idx)).context("...")?;
                let engine = Engine::generate_initial_condition(self.cfg.clone())?;
                (run_idx, 0, engine)
            }
            Some(run_idx) => {
                let file_idx = self.count_trajectory_files(run_idx).context("...")?;
                let engine = Engine::load_checkpoint(self.checkpoint_file(run_idx))?;
                if engine.cfg() != &self.cfg {
                    bail!("checkpoint config differs from the current simulation config");
                }
                (run_idx, file_idx, engine)
            }
        };

        log::info!("run_dir = {:?}", self.run_dir(run_idx));

        engine.run_simulation(self.trajectory_file(run_idx, file_idx))?;

        engine.save_checkpoint(self.checkpoint_file(run_idx))?;

        Ok(())
    }

    pub fn run_analysis(&self) -> Result<()> {
        let n_runs = self.count_runs().context("...")?;
        for run_idx in 0..n_runs {
            let n_files = self.count_trajectory_files(run_idx).context("...")?;
            let mut analyzer = Analyzer::new(self.cfg.clone());
            for file_idx in 0..n_files {
                analyzer.add_file(self.trajectory_file(run_idx, file_idx))?;
            }
            analyzer.save_results(self.results_file(run_idx))?;
        }

        Ok(())
    }

    fn count_runs(&self) -> Result<usize> {
        let pattern = self.sim_dir.join("run-*");
        let count = glob(pattern.to_str().context("failed to convert to string")?)
            .context("failed to glob run directories")?
            .filter_map(Result::ok)
            .filter(|p| p.is_dir())
            .count();
        Ok(count)
    }

    fn run_dir(&self, run_idx: usize) -> PathBuf {
        self.sim_dir.join(format!("run-{run_idx:04}"))
    }

    fn count_trajectory_files(&self, run_idx: usize) -> Result<usize> {
        let pattern = self.run_dir(run_idx).join("trajectory-*.bin");
        let count = glob(pattern.to_str().context("failed to convert to string")?)
            .context("failed to glob trajectory files")?
            .filter_map(Result::ok)
            .count();
        Ok(count)
    }

    fn trajectory_file(&self, run_idx: usize, file_idx: usize) -> PathBuf {
        self.run_dir(run_idx)
            .join(format!("trajectory-{file_idx:04}.bin"))
    }

    fn checkpoint_file(&self, run_idx: usize) -> PathBuf {
        self.run_dir(run_idx).join(format!("checkpoint.bin"))
    }

    fn results_file(&self, run_idx: usize) -> PathBuf {
        self.run_dir(run_idx).join(format!("results.bin"))
    }
}
