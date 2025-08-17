use crate::analysis::Analyzer;
use crate::config::Config;
use crate::engine::Engine;
use anyhow::{Context, Result};
use std::{fs, path::PathBuf};

pub struct Manager {
    sim_dir: PathBuf,
    cfg: Config,
}

impl Manager {
    pub fn new(sim_dir: PathBuf, cfg: Config) -> Self {
        Self { sim_dir, cfg }
    }

    pub fn run_simulation(&self, sim_idx: Option<usize>) -> Result<()> {
        let (sim_idx, file_idx, mut engine) = match sim_idx {
            None => {
                let sim_idx = self.count_entries(&format!("^checkpoint-.*$"))?;
                let engine = Engine::generate_initial_condition(self.cfg.clone())?;
                (sim_idx, 0, engine)
            }
            Some(sim_idx) => {
                let file_idx = self.count_entries(&format!("^trajectory-{sim_idx:04}.*$"))?;
                let engine =
                    Engine::load_checkpoint(self.checkpoint_file(sim_idx), self.cfg.clone())?;
                (sim_idx, file_idx, engine)
            }
        };

        log::info!("{} = {sim_idx:03}", stringify!(sim_idx));
        log::info!("{} = {file_idx:03}", stringify!(file_idx));

        engine.run_simulation(self.trajectory_file(sim_idx, file_idx))?;

        engine.save_checkpoint(self.checkpoint_file(sim_idx))?;

        Ok(())
    }

    pub fn run_analysis(&self) -> Result<()> {
        let n_sim = self.count_entries(&format!("^checkpoint-.*$"))?;
        for sim_idx in 0..n_sim {
            let n_files = self.count_entries(&format!("^trajectory-{sim_idx:04}-.*$"))?;
            let mut analyzer = Analyzer::new(self.cfg.clone());
            for file_idx in 0..n_files {
                analyzer.add_file(self.trajectory_file(sim_idx, file_idx))?;
            }
            analyzer.save_results(self.results_file(sim_idx))?;
        }

        Ok(())
    }

    fn trajectory_file(&self, sim_idx: usize, file_idx: usize) -> PathBuf {
        self.sim_dir
            .join(format!("trajectory-{sim_idx:04}-{file_idx:04}.bin"))
    }

    fn checkpoint_file(&self, sim_idx: usize) -> PathBuf {
        self.sim_dir.join(format!("checkpoint-{sim_idx:04}.bin"))
    }

    fn results_file(&self, sim_idx: usize) -> PathBuf {
        self.sim_dir.join(format!("results-{sim_idx:04}.bin"))
    }

    fn count_entries(&self, regex: &str) -> Result<usize> {
        let regex = regex::Regex::new(regex)?;
        let count = fs::read_dir(&self.sim_dir)
            .with_context(|| format!("failed to read {:?}", self.sim_dir))?
            .filter_map(Result::ok)
            .filter(|entry| {
                entry
                    .file_name()
                    .to_str()
                    .is_some_and(|name| regex.is_match(name))
            })
            .count();
        Ok(count)
    }
}
