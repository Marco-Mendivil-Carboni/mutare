mod analysis;
mod config;
mod engine;
mod manager;
mod model;
mod stats;

use crate::manager::Manager;
use anyhow::{Context, Result};
use clap::{Parser, Subcommand};
use std::{path::PathBuf, time::Instant};

#[derive(Debug, Parser)]
#[command(version, about)]
struct CLI {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Debug, Subcommand)]
enum Commands {
    Run {
        sim_dir: PathBuf,
        run_idx: Option<usize>,
    },
    Analyze {
        sim_dir: PathBuf,
    },
}

fn main() {
    env_logger::Builder::new()
        .format_timestamp_millis()
        .filter_level(log::LevelFilter::Info)
        .parse_default_env()
        .init();

    if let Err(err) = run() {
        log::error!("{err:?}");
        std::process::exit(1);
    }
}

fn run() -> Result<()> {
    let args = CLI::parse();
    log::info!("{args:?}");

    match args.command {
        Commands::Run { sim_dir, run_idx } => {
            let mgr = Manager::new(sim_dir).context("failed to construct mgr")?;

            let start = Instant::now();
            mgr.run_simulation(run_idx)?;
            let duration = start.elapsed();

            log::info!("elapsed time = {duration:?}");
        }
        Commands::Analyze { sim_dir } => {
            let mgr = Manager::new(sim_dir).context("failed to construct mgr")?;

            mgr.run_analysis()?;
        }
    }

    Ok(())
}
