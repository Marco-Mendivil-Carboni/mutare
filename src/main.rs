mod analysis;
mod config;
mod engine;
mod manager;
mod model;
mod stats;

use crate::manager::Manager;
use anyhow::{Context, Result};
use clap::{Parser, Subcommand};
use std::path::PathBuf;

#[derive(Debug, Parser)]
#[command(version, about)]
struct CLI {
    #[arg(long)]
    sim_dir: PathBuf,

    #[command(subcommand)]
    command: Command,
}

#[derive(Debug, Subcommand)]
enum Command {
    Create,

    Resume {
        #[arg(long)]
        run_idx: usize,
    },

    Analyze,

    Clean,
}

fn main() {
    env_logger::Builder::new()
        .format_timestamp_millis()
        .filter_level(log::LevelFilter::Info)
        .parse_default_env()
        .init();

    if let Err(error) = run_cli() {
        log::error!("{error:#?}");
        std::process::exit(1);
    }
}

fn run_cli() -> Result<()> {
    let args = CLI::parse();
    log::info!("{args:#?}");

    let mgr = Manager::new(args.sim_dir).context("failed to construct mgr")?;

    match args.command {
        Command::Create => mgr.create_run()?,
        Command::Resume { run_idx } => mgr.resume_run(run_idx)?,
        Command::Analyze => mgr.analyze_sim()?,
        Command::Clean => mgr.clean_sim()?,
    }

    Ok(())
}
