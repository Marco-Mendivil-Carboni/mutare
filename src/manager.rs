use crate::analysis::Analyzer;
use crate::config::Config;
use crate::engine::Engine;
use anyhow::{Context, Result};
use std::{
    fs,
    path::{Path, PathBuf},
};

pub struct Manager {
    sim_dir: PathBuf,
    cfg: Config,
}

const CKPT_PRE: &str = "checkpoint";
const TRAJ_PRE: &str = "trajectory";
const ANA_PRE: &str = "analysis";

impl Manager {
    pub fn new(sim_dir: PathBuf, cfg: Config) -> Self {
        Self { sim_dir, cfg }
    }

    pub fn run_simulation(&self, sim_idx: Option<usize>) -> Result<()> {
        let new_sim = sim_idx.is_none();
        let mut sim_idx = sim_idx.unwrap_or(0);

        let file_idx;
        let mut sim;

        if new_sim {
            sim_idx = count_entries(&self.sim_dir, &format!("^{CKPT_PRE}-.*$"))?;
            file_idx = 0;
            sim = Engine::generate_initial_condition(self.cfg.clone())?;
        } else {
            file_idx = count_entries(&self.sim_dir, &format!("^{TRAJ_PRE}-{sim_idx:03}.*$"))?;
            sim =
                Engine::load_checkpoint(self.sim_dir.join(format!("{CKPT_PRE}-{sim_idx:03}.bin")))?;
        }

        log::info!("{} = {sim_idx:03}", stringify!(sim_idx));
        log::info!("{} = {file_idx:03}", stringify!(file_idx));

        sim.run_simulation(
            self.sim_dir
                .join(format!("{TRAJ_PRE}-{sim_idx:03}-{file_idx:03}.bin")),
        )?;

        sim.save_checkpoint(self.sim_dir.join(format!("{CKPT_PRE}-{sim_idx:03}.bin")))?;

        Ok(())
    }

    pub fn run_analysis(&self) -> Result<()> {
        let n_sim = count_entries(&self.sim_dir, &format!("^{CKPT_PRE}-.*$"))?;

        for sim_idx in 0..n_sim {
            let n_files = count_entries(&self.sim_dir, &format!("^{TRAJ_PRE}-{sim_idx:03}-.*$"))?;

            let mut ana = Analyzer::new(self.cfg.clone());

            for file_idx in 0..n_files {
                ana.add_file(
                    self.sim_dir
                        .join(format!("{TRAJ_PRE}-{sim_idx:03}-{file_idx:03}.bin")),
                )?;
            }

            ana.save_results(self.sim_dir.join(format!("{ANA_PRE}-{sim_idx:03}.bin")))?;
        }

        Ok(())
    }
}

fn count_entries<P: AsRef<Path>>(dir: P, regex: &str) -> Result<usize> {
    let dir = dir.as_ref();
    let regex = regex::Regex::new(regex)?;
    let count = fs::read_dir(dir)
        .with_context(|| format!("failed to read {:?}", dir))?
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
