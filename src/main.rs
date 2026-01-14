//! A simple tool to simulate and analyze a stochastic agent-based model of adaptation in uncertain environments.

mod analysis;
mod config;
mod engine;
mod manager;
mod types;

use crate::manager::Manager;
use anyhow::{Context, Result};
use clap::{Parser, Subcommand};
use std::path::PathBuf;

/// Command-line interface for managing, producing and analyzing simulations.
#[derive(Debug, Parser)]
#[command(version, about)]
struct CLI {
    /// Path to the simulation directory.
    #[arg(long)]
    sim_dir: PathBuf,

    /// Simulation run index.
    #[arg(long)]
    run_idx: usize,

    /// Simulation command.
    #[command(subcommand)]
    sim_cmd: SimCmd,
}

/// Available simulation commands.
#[derive(Debug, Subcommand)]
enum SimCmd {
    /// Create simulation run.
    Create,

    /// Resume simulation run.
    Resume,

    /// Analyze simulation run.
    Analyze,
}

/// Entry point of the application.
fn main() {
    // Initialize logging with millisecond timestamps and INFO level by default.
    env_logger::Builder::new()
        .format_timestamp_millis()
        .filter_level(log::LevelFilter::Info)
        .parse_default_env()
        .init();

    // Run the CLI and exit with error code 1 if any error occurs.
    if let Err(error) = run_cli() {
        log::error!("{error:#?}");
        std::process::exit(1);
    }
}

/// Parse CLI and execute the requested simulation command.
fn run_cli() -> Result<()> {
    // Parse command-line interface.
    let cli = CLI::parse();
    log::info!("{cli:#?}");

    // Create a manager for the specified simulation directory.
    let mgr = Manager::new(cli.sim_dir).context("failed to create mgr")?;

    // Execute the requested simulation command.
    match cli.sim_cmd {
        SimCmd::Create => mgr.create_run(cli.run_idx)?,
        SimCmd::Resume => mgr.resume_run(cli.run_idx)?,
        SimCmd::Analyze => mgr.analyze_run(cli.run_idx)?,
    }

    Ok(())
}
