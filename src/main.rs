mod analysis;
mod config;
mod engine;
mod manager;
mod model;
mod stats;

use crate::config::Config;
use crate::manager::Manager;
use anyhow::{Context, Result};
use clap::Parser;
use std::{path::PathBuf, time::Instant};

#[derive(Debug, Parser)]
#[command(version, about)]
struct Args {
    sim_dir: PathBuf,
    sim_idx: Option<usize>,
    #[arg(short, long)]
    analyze: bool,
}

fn main() -> Result<()> {
    env_logger::Builder::new()
        .format_timestamp_millis()
        .filter_level(log::LevelFilter::Info)
        .parse_default_env()
        .init();

    let args = Args::parse();
    log::info!("{args:#?}");

    let cfg = Config::from_file("config.bin")
        .context("failed to create config")
        .unwrap_or_else(|err| {
            log::error!("{err:?}");
            std::process::exit(1);
        });
    log::info!("{cfg:#?}");

    let mgr = Manager::new(args.sim_dir.clone(), cfg);

    if args.analyze {
        mgr.run_analysis()?;
    } else {
        let start = Instant::now();
        mgr.run_simulation(args.sim_idx)?;
        let duration = start.elapsed();
        log::info!("elapsed time = {duration:?}");
    }

    Ok(())
}
